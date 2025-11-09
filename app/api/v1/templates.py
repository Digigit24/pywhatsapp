# app/api/v1/templates.py
"""
WhatsApp Template API endpoints.
Handles template creation, management, and sending.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.session import get_db
from app.api.deps import get_tenant_id_flexible
from app.services.template_service import TemplateService
from app.services import get_whatsapp_client
from app.schemas.template import (
    TemplateCreate, TemplateUpdate, TemplateResponse,
    TemplateSendRequest, TemplateSendResponse,
    TemplateBulkSendRequest, TemplateBulkSendResponse,
    TemplateListResponse, LibraryTemplateCreate
)

router = APIRouter()


def get_template_service():
    """Get template service with WhatsApp client"""
    wa_client = get_whatsapp_client()
    return TemplateService(wa_client)


# ────────────────────────────────────────────
# Template Management
# ────────────────────────────────────────────

@router.post("/", response_model=TemplateResponse, status_code=201)
def create_template(
    data: TemplateCreate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id_flexible),
    service: TemplateService = Depends(get_template_service)
):
    """
    Create a new WhatsApp template.
    
    The template will be submitted to WhatsApp for approval.
    Status will be PENDING until WhatsApp reviews it.
    
    **Template naming rules:**
    - Only lowercase letters, numbers, and underscores
    - No spaces or special characters
    - Example: `order_confirmation`, `delivery_update_2`
    
    **Components:**
    - HEADER: Text, image, video, or document
    - BODY: Main message text with variables {{1}}, {{2}}, etc.
    - FOOTER: Optional footer text
    - BUTTONS: Quick reply, URL, or phone buttons
    """
    try:
        template = service.create_template(db, tenant_id, data)
        return template
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Failed to create template: {str(e)}")


@router.post("/library", response_model=TemplateResponse, status_code=201)
def create_from_library(
    data: LibraryTemplateCreate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id_flexible),
    service: TemplateService = Depends(get_template_service)
):
    """
    Create template from WhatsApp template library.
    
    Template library provides pre-approved templates for common use cases
    like payment reminders, delivery updates, and authentication codes.
    """
    try:
        template = service.create_from_library(
            db, tenant_id,
            name=data.name,
            library_template_name=data.library_template_name,
            language=data.language.value,
            category=data.category.value,
            button_inputs=data.button_inputs
        )
        return template
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/", response_model=TemplateListResponse)
def list_templates(
    status: Optional[str] = Query(None, description="Filter by status: PENDING, APPROVED, REJECTED"),
    category: Optional[str] = Query(None, description="Filter by category: MARKETING, UTILITY, AUTHENTICATION"),
    language: Optional[str] = Query(None, description="Filter by language: en_US, hi, etc."),
    skip: int = 0,
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id_flexible),
    service: TemplateService = Depends(get_template_service)
):
    """
    List all templates with optional filters.
    
    **Filter by status:**
    - `PENDING`: Awaiting WhatsApp approval
    - `APPROVED`: Ready to use
    - `REJECTED`: Not approved by WhatsApp
    - `PAUSED`: Temporarily disabled
    """
    templates, total = service.get_templates(
        db, tenant_id, status, category, language, skip, limit
    )
    
    return TemplateListResponse(
        total=total,
        items=templates,
        page=skip // limit + 1,
        page_size=limit
    )


@router.get("/{template_id}", response_model=TemplateResponse)
def get_template(
    template_id: int,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id_flexible),
    service: TemplateService = Depends(get_template_service)
):
    """Get specific template by ID"""
    template = service.get_template(db, tenant_id, template_id)
    
    if not template:
        raise HTTPException(404, "Template not found")
    
    return template


@router.get("/name/{template_name}", response_model=TemplateResponse)
def get_template_by_name(
    template_name: str,
    language: str = Query(..., description="Template language"),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id_flexible),
    service: TemplateService = Depends(get_template_service)
):
    """Get template by name and language"""
    template = service.get_template_by_name(db, tenant_id, template_name, language)
    
    if not template:
        raise HTTPException(404, f"Template '{template_name}' not found for language {language}")
    
    return template


@router.patch("/{template_id}", response_model=TemplateResponse)
def update_template(
    template_id: int,
    data: TemplateUpdate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id_flexible),
    service: TemplateService = Depends(get_template_service)
):
    """
    Update template.
    
    Note: Most template properties cannot be changed after creation.
    You can only update status and internal metadata.
    """
    try:
        template = service.update_template(db, tenant_id, template_id, data)
        return template
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.delete("/{template_id}")
def delete_template(
    template_id: int,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id_flexible),
    service: TemplateService = Depends(get_template_service)
):
    """
    Delete template.
    
    This removes the template from your account.
    Note: Deletion from WhatsApp may not be immediate.
    """
    success = service.delete_template(db, tenant_id, template_id)
    
    if not success:
        raise HTTPException(404, "Template not found")
    
    return {"ok": True, "message": "Template deleted"}


# ────────────────────────────────────────────
# Send Template Messages
# ────────────────────────────────────────────

@router.post("/send", response_model=TemplateSendResponse)
def send_template(
    data: TemplateSendRequest,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id_flexible),
    service: TemplateService = Depends(get_template_service)
):
    """
    Send template message to a recipient.
    
    **Requirements:**
    - Template must be APPROVED
    - Recipient must have opted in to receive messages
    - All required parameters must be provided
    
    **Parameter format:**
    ```json
    {
        "to": "919876543210",
        "template_name": "order_confirmation",
        "language": "en_US",
        "components": [
            {
                "type": "body",
                "parameters": [
                    {"type": "text", "text": "John Doe"},
                    {"type": "text", "text": "12345"}
                ]
            }
        ]
    }
    ```
    
    **Or use simple parameters:**
    ```json
    {
        "to": "919876543210",
        "template_name": "order_confirmation",
        "language": "en_US",
        "parameters": {
            "name": "John Doe",
            "order_id": "12345"
        }
    }
    ```
    """
    try:
        message_id, log = service.send_template(db, tenant_id, data)
        
        return TemplateSendResponse(
            message_id=message_id,
            phone=data.to,
            template_name=data.template_name,
            status="sent" if message_id else "failed"
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Failed to send template: {str(e)}")


@router.post("/send/bulk", response_model=TemplateBulkSendResponse)
async def send_template_bulk(
    data: TemplateBulkSendRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id_flexible),
    service: TemplateService = Depends(get_template_service)
):
    """
    Send template message to multiple recipients.
    
    **Bulk sending:**
    - Max 1000 recipients per request
    - Respects WhatsApp rate limits
    - Returns detailed results per recipient
    
    **Example with different parameters per recipient:**
    ```json
    {
        "template_name": "order_update",
        "language": "en_US",
        "recipients": ["919876543210", "919876543211"],
        "parameters_per_recipient": [
            {"name": "John", "order_id": "123"},
            {"name": "Jane", "order_id": "456"}
        ]
    }
    ```
    
    **Example with same parameters for all:**
    ```json
    {
        "template_name": "promotion",
        "language": "en_US",
        "recipients": ["919876543210", "919876543211"],
        "default_parameters": {
            "discount": "20%",
            "code": "SAVE20"
        }
    }
    ```
    """
    try:
        # Run in background for large batches
        if len(data.recipients) > 10:
            background_tasks.add_task(
                service.send_template_bulk,
                db, tenant_id, data
            )
            return TemplateBulkSendResponse(
                total=len(data.recipients),
                sent=0,
                failed=0,
                results=[{"status": "queued", "message": "Processing in background"}]
            )
        
        # Send immediately for small batches
        result = service.send_template_bulk(db, tenant_id, data)
        return TemplateBulkSendResponse(**result)
        
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, str(e))


# ────────────────────────────────────────────
# Template Analytics
# ────────────────────────────────────────────

@router.get("/{template_id}/analytics")
def get_template_analytics(
    template_id: int,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id_flexible),
    service: TemplateService = Depends(get_template_service)
):
    """
    Get analytics for a specific template.
    
    Returns:
    - Total sends
    - Success rate
    - Recent sends
    - Delivery statistics
    """
    from app.models.template import TemplateSendLog
    
    template = service.get_template(db, tenant_id, template_id)
    if not template:
        raise HTTPException(404, "Template not found")
    
    # Get send logs
    logs = db.query(TemplateSendLog).filter(
        TemplateSendLog.tenant_id == tenant_id,
        TemplateSendLog.template_id == template_id
    ).all()
    
    total_sends = len(logs)
    successful_sends = sum(1 for log in logs if log.send_status == "sent")
    failed_sends = sum(1 for log in logs if log.send_status == "failed")
    
    return {
        "template_id": template_id,
        "template_name": template.name,
        "status": template.status.value,
        "usage_count": template.usage_count,
        "total_sends": total_sends,
        "successful_sends": successful_sends,
        "failed_sends": failed_sends,
        "success_rate": (successful_sends / total_sends * 100) if total_sends > 0 else 0,
        "last_used_at": template.last_used_at
    }


# ────────────────────────────────────────────
# Template Status Webhooks
# ────────────────────────────────────────────

@router.post("/webhook/status")
async def template_status_webhook(
    data: dict,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id_flexible),
    service: TemplateService = Depends(get_template_service)
):
    """
    Handle template status update webhooks from WhatsApp.
    
    This endpoint receives notifications when:
    - Template is approved
    - Template is rejected
    - Template quality score changes
    """
    try:
        template_id = data.get("template_id")
        status = data.get("status")
        quality_score = data.get("quality_score")
        rejection_reason = data.get("rejection_reason")
        
        service.update_template_status(
            db, tenant_id, template_id, status,
            quality_score, rejection_reason
        )
        
        return {"ok": True}
    except Exception as e:
        raise HTTPException(500, str(e))