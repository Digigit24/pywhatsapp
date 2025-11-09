# app/api/v1/messages.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.session import get_db
from app.api.deps import get_current_user_flexible, get_tenant_id_flexible
from app.services import get_message_service
from app.services.message_service import MessageService
from app.schemas.message import (
    MessageCreate, MediaMessageCreate, LocationMessageCreate,
    MessageResponse, MessageSendResponse, ConversationPreview,
    TemplateSendRequest, TemplateCreate, TemplateResponse,
    ConversationDetail
)

from datetime import datetime
from app.ws.manager import notify_clients_sync

router = APIRouter()

@router.post("/send", response_model=MessageSendResponse)
@router.post("/send/text", response_model=MessageSendResponse)
def send_text(
    data: MessageCreate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id_flexible),
    service: MessageService = Depends(get_message_service)
):
    """Send text message"""
    msg_id, saved = service.send_text_message(db, tenant_id, data)

    # Broadcast to tenant websocket clients
    try:
        notify_clients_sync(tenant_id, {
            "event": "message_outgoing",
            "data": {
                "phone": data.to,
                "name": None,
                "message": {
                    "id": msg_id,
                    "type": "text",
                    "text": data.text,
                    "timestamp": datetime.utcnow().isoformat(),
                    "direction": "outgoing"
                }
            }
        })
    except Exception:
        # Don't fail the request if WS broadcast fails
        pass

    return MessageSendResponse(message_id=msg_id, phone=data.to, text=data.text)

@router.post("/send/media")
def send_media(
    data: MediaMessageCreate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id_flexible),
    service: MessageService = Depends(get_message_service)
):
    """Send media message"""
    msg_id, saved = service.send_media_message(db, tenant_id, data)
    return {"ok": True, "message_id": msg_id}

@router.post("/send/location")
def send_location(
    data: LocationMessageCreate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id_flexible),
    service: MessageService = Depends(get_message_service)
):
    """Send location"""
    msg_id, saved = service.send_location(db, tenant_id, data)
    return {"ok": True, "message_id": msg_id}

@router.get("/messages", response_model=List[MessageResponse])
def list_messages(
    phone: Optional[str] = None,
    direction: Optional[str] = None,
    skip: int = 0,
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id_flexible),
    service: MessageService = Depends(get_message_service)
):
    """List messages with filters"""
    messages, total = service.get_messages(db, tenant_id, phone, direction, skip, limit)
    return messages

@router.get("/conversations")
def list_conversations(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id_flexible),
    service: MessageService = Depends(get_message_service)
):
    """List all conversations"""
    return service.get_conversations(db, tenant_id)

@router.get("/conversations/{phone}", response_model=ConversationDetail)
def get_conversation(
    phone: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id_flexible),
    service: MessageService = Depends(get_message_service)
):
    """Get conversation with specific number"""
    messages = service.get_conversation(db, tenant_id, phone)
    return {"phone": phone, "messages": messages}

@router.delete("/conversations/{phone}")
def delete_conversation(
    phone: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id_flexible),
    service: MessageService = Depends(get_message_service)
):
    """Delete conversation"""
    deleted = service.delete_conversation(db, tenant_id, phone)
    return {"ok": True, "deleted": deleted}

# Templates
@router.post("/templates", response_model=TemplateResponse)
def create_template(
    data: TemplateCreate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id_flexible),
    service: MessageService = Depends(get_message_service)
):
    """Create message template"""
    return service.create_template(db, tenant_id, data)

@router.get("/templates", response_model=List[TemplateResponse])
def list_templates(
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id_flexible),
    service: MessageService = Depends(get_message_service)
):
    """List templates"""
    return service.get_templates(db, tenant_id, category)

@router.post("/templates/send")
def send_template(
    data: TemplateSendRequest,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id_flexible),
    service: MessageService = Depends(get_message_service)
):
    """Send using template"""
    msg_id, saved = service.send_template_message(db, tenant_id, data)
    return {"ok": True, "message_id": msg_id}

# ────────────────────────────────────────────
# Statistics Endpoint
# ────────────────────────────────────────────

@router.get("/stats")
def get_stats(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id_flexible),
    service: MessageService = Depends(get_message_service)
):
    """Get message statistics"""
    from sqlalchemy import func
    from app.models.message import Message
    
    # Total messages
    total_messages = db.query(Message).filter(Message.tenant_id == tenant_id).count()
    
    # Messages by direction
    direction_stats = db.query(
        Message.direction,
        func.count(Message.id).label('count')
    ).filter(
        Message.tenant_id == tenant_id
    ).group_by(Message.direction).all()
    
    # Messages by type
    type_stats = db.query(
        Message.message_type,
        func.count(Message.id).label('count')
    ).filter(
        Message.tenant_id == tenant_id
    ).group_by(Message.message_type).all()
    
    # Recent activity (last 7 days)
    from datetime import datetime, timedelta
    week_ago = datetime.utcnow() - timedelta(days=7)
    recent_messages = db.query(Message).filter(
        Message.tenant_id == tenant_id,
        Message.created_at >= week_ago
    ).count()
    
    # Unique contacts
    unique_contacts = db.query(Message.phone).filter(
        Message.tenant_id == tenant_id
    ).distinct().count()
    
    return {
        "total_messages": total_messages,
        "unique_contacts": unique_contacts,
        "recent_messages": recent_messages,
        "by_direction": {stat.direction: stat.count for stat in direction_stats},
        "by_type": {stat.message_type: stat.count for stat in type_stats}
    }