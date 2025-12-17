# app/api/v1/campaigns.py
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import uuid
import asyncio

from app.db.session import get_db
from app.api.deps import get_tenant_id_flexible
from app.services import get_message_service
from app.models.campaign import Campaign
from app.models.contact import Contact
from app.models.group import Group
from app.schemas.campaign import CampaignCreate, CampaignResponse
from app.schemas.message import MessageCreate

router = APIRouter()

def resolve_recipients(
    db: Session,
    tenant_id: str,
    recipients: List[str] = None,
    contact_ids: List[int] = None,
    group_ids: List[int] = None
) -> List[str]:
    """
    Resolve all recipient types into a list of phone numbers

    Args:
        db: Database session
        tenant_id: Tenant ID for filtering
        recipients: Direct phone numbers
        contact_ids: Contact integer IDs to look up
        group_ids: Group integer IDs to look up

    Returns:
        List of unique phone numbers
    """
    phone_numbers = set()

    # Add direct phone numbers
    if recipients:
        phone_numbers.update(recipients)

    # Resolve contact IDs to phone numbers
    if contact_ids:
        contacts = db.query(Contact).filter(
            Contact.tenant_id == tenant_id,
            Contact.id.in_(contact_ids)
        ).all()

        for contact in contacts:
            if contact.phone:
                phone_numbers.add(contact.phone)

    # Resolve group IDs to participant phone numbers
    if group_ids:
        groups = db.query(Group).filter(
            Group.tenant_id == tenant_id,
            Group.id.in_(group_ids),
            Group.is_active == True
        ).all()

        for group in groups:
            if group.participants:
                # participants is a JSON array of phone numbers
                phone_numbers.update(group.participants)

    return list(phone_numbers)

async def send_broadcast(
    campaign_id: str,
    tenant_id: str,
    recipients: List[str],
    message_text: Optional[str] = None,
    template_name: Optional[str] = None,
    template_language: str = "en_US",
    parameters: Optional[Dict[str, Any]] = None,
    parameters_per_recipient: Optional[List[Dict[str, Any]]] = None
):
    """
    Background task to send messages.

    Supports both:
    - Regular text messages (requires 24-hour conversation window)
    - Template messages (can send to any contact anytime)
    """
    from app.db.session import get_db_session
    from app.services import get_message_service, get_whatsapp_client
    from app.services.template_service import TemplateService
    from app.schemas.template import TemplateSendRequest, TemplateLanguage
    import logging

    log = logging.getLogger("whatspy.campaigns")
    results = []
    sent = 0
    failed = 0

    # Determine if we're sending templates or text messages
    is_template_broadcast = bool(template_name)

    with get_db_session() as db:
        if is_template_broadcast:
            # ===== TEMPLATE MESSAGE BROADCAST (works with new contacts) =====
            log.info(f"📧 Sending TEMPLATE broadcast: {template_name} to {len(recipients)} recipients")

            wa_client = get_whatsapp_client()
            template_service = TemplateService(wa_client)

            # Convert language string to enum
            try:
                lang_enum = TemplateLanguage(template_language)
            except ValueError:
                lang_enum = TemplateLanguage.ENGLISH_US
                log.warning(f"Invalid language {template_language}, defaulting to en_US")

            for idx, phone in enumerate(recipients):
                try:
                    # Determine parameters for this recipient
                    params = None
                    if parameters_per_recipient and idx < len(parameters_per_recipient):
                        params = parameters_per_recipient[idx]
                    elif parameters:
                        params = parameters

                    # Send template message
                    send_request = TemplateSendRequest(
                        to=phone,
                        template_name=template_name,
                        language=lang_enum,
                        parameters=params
                    )

                    msg_id, send_log = template_service.send_template(db, tenant_id, send_request)

                    if msg_id:
                        results.append({"phone": phone, "status": "sent", "message_id": msg_id})
                        sent += 1
                        log.debug(f"✅ Template sent to {phone}: {msg_id}")
                    else:
                        error_msg = send_log.error_message if send_log else "Unknown error"
                        results.append({"phone": phone, "status": "failed", "error": error_msg})
                        failed += 1
                        log.warning(f"❌ Template failed for {phone}: {error_msg}")

                    await asyncio.sleep(0.5)  # Rate limiting

                except Exception as e:
                    results.append({"phone": phone, "status": "failed", "error": str(e)})
                    failed += 1
                    log.error(f"❌ Template failed for {phone}: {e}")

        else:
            # ===== TEXT MESSAGE BROADCAST (requires 24-hour window) =====
            log.info(f"💬 Sending TEXT broadcast to {len(recipients)} recipients")
            log.warning("⚠️ Text messages can only be sent to contacts within 24-hour conversation window")

            service = get_message_service()

            for phone in recipients:
                try:
                    msg_data = MessageCreate(to=phone, text=message_text)
                    msg_id, _ = service.send_text_message(db, tenant_id, msg_data)
                    results.append({"phone": phone, "status": "sent", "message_id": msg_id})
                    sent += 1
                    await asyncio.sleep(0.5)  # Rate limiting
                except Exception as e:
                    results.append({"phone": phone, "status": "failed", "error": str(e)})
                    failed += 1

        # Update campaign
        campaign = db.query(Campaign).filter(Campaign.campaign_id == campaign_id).first()
        if campaign:
            campaign.sent_count = sent
            campaign.failed_count = failed
            campaign.results = results
            db.commit()

        log.info(f"📊 Campaign {campaign_id} completed: {sent} sent, {failed} failed")

@router.post("/broadcast", response_model=CampaignResponse)
async def create_broadcast(
    data: CampaignCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id_flexible)
):
    """
    Create broadcast campaign

    **Supports two modes:**

    1. **Template Broadcast** (recommended for new contacts):
       - Provide `template_name` instead of `message_text`
       - Can send to contacts OUTSIDE 24-hour conversation window
       - Perfect for marketing messages to cold contacts
       - Example:
         ```json
         {
           "campaign_name": "Welcome Campaign",
           "template_name": "hello_world",
           "template_language": "en_US",
           "contact_ids": [36, 35]
         }
         ```

    2. **Text Message Broadcast** (for recent conversations):
       - Provide `message_text` instead of `template_name`
       - Can ONLY send to contacts WITHIN 24-hour conversation window
       - Example:
         ```json
         {
           "campaign_name": "Quick Update",
           "message_text": "Hi! Just checking in.",
           "contact_ids": [36, 35]
         }
         ```

    **Recipients:**
    - recipients: Direct phone numbers array (e.g., ["919876543210"])
    - contact_ids: Contact IDs from database (e.g., [36, 35])
    - group_ids: Group IDs (sends to all group participants)

    At least one recipient type must be provided.
    """
    import logging
    log = logging.getLogger("whatspy.campaigns")

    campaign_id = str(uuid.uuid4())

    # Determine broadcast type
    is_template = bool(data.template_name)
    broadcast_type = "TEMPLATE" if is_template else "TEXT"

    log.info(f"📢 Creating {broadcast_type} broadcast campaign: {data.campaign_name}")
    if is_template:
        log.info(f"   Template: {data.template_name} ({data.template_language})")
    else:
        log.info(f"   Message: {data.message_text[:50]}...")
    log.info(f"   Recipients: {data.recipients}")
    log.info(f"   Contact IDs: {data.contact_ids}")
    log.info(f"   Group IDs: {data.group_ids}")

    # Resolve all recipient types to phone numbers
    phone_numbers = resolve_recipients(
        db=db,
        tenant_id=tenant_id,
        recipients=data.recipients,
        contact_ids=data.contact_ids,
        group_ids=data.group_ids
    )

    log.info(f"✅ Resolved {len(phone_numbers)} phone numbers")

    # Validate we have recipients
    if not phone_numbers:
        log.error("❌ No valid recipients found after resolving contact/group IDs")
        raise HTTPException(
            status_code=400,
            detail="No valid recipients found. Please check contact IDs, group IDs, or phone numbers."
        )

    # Create campaign record
    campaign_message = f"Template: {data.template_name}" if is_template else data.message_text
    campaign = Campaign(
        tenant_id=tenant_id,
        campaign_id=campaign_id,
        campaign_name=data.campaign_name,
        message_text=campaign_message,
        total_recipients=len(phone_numbers)
    )

    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    log.info(f"📋 Campaign created: {campaign_id} with {len(phone_numbers)} recipients")

    # Start background task with all parameters
    background_tasks.add_task(
        send_broadcast,
        campaign_id,
        tenant_id,
        phone_numbers,
        data.message_text,
        data.template_name,
        data.template_language,
        data.parameters,
        data.parameters_per_recipient
    )

    log.info(f"🚀 Background {broadcast_type} broadcast task started for campaign {campaign_id}")

    return campaign

@router.get("/", response_model=List[CampaignResponse])
def list_campaigns(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id_flexible)
):
    """List campaigns"""
    campaigns = db.query(Campaign).filter(
        Campaign.tenant_id == tenant_id
    ).order_by(Campaign.created_at.desc()).offset(skip).limit(limit).all()
    
    return campaigns

@router.get("/{campaign_id}", response_model=CampaignResponse)
def get_campaign(
    campaign_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id_flexible)
):
    """Get campaign details"""
    campaign = db.query(Campaign).filter(
        Campaign.tenant_id == tenant_id,
        Campaign.campaign_id == campaign_id
    ).first()

    if not campaign:
        from fastapi import HTTPException
        raise HTTPException(404, "Campaign not found")

    return campaign


class TemplateBroadcastCreate(BaseModel):
    campaign_name: str
    template_name: str
    template_language: str = "en_US"
    recipients: Optional[List[str]] = None
    contact_ids: Optional[List[int]] = None
    group_ids: Optional[List[int]] = None
    # Template parameters - for templates with variables like {{1}}, {{2}}
    parameters: Optional[Dict[str, Any]] = None
    # Or provide different parameters for each recipient
    parameters_per_recipient: Optional[List[Dict[str, Any]]] = None


@router.post("/broadcast/template", response_model=CampaignResponse)
async def create_template_broadcast(
    data: TemplateBroadcastCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id_flexible)
):
    """
    Create template broadcast campaign.

    Template messages can be sent ANYTIME, even outside the 24-hour window.
    Use this for marketing broadcasts to users who haven't messaged recently.

    **Required:**
    - campaign_name: Name of the campaign
    - template_name: Approved template name from Meta
    - template_language: Template language (default: en_US)

    **Recipients (at least one):**
    - recipients: Direct phone numbers
    - contact_ids: Contact IDs from database
    - group_ids: Group IDs from database

    **Template Parameters (for templates with variables):**
    - parameters: Default parameters for all recipients (e.g., {"1": "John", "2": "12345"})
    - parameters_per_recipient: Different parameters per recipient (list of dicts)

    **Example 1 - Template without variables:**
    ```json
    {
        "campaign_name": "Welcome Campaign",
        "template_name": "hello_world",
        "template_language": "en_US",
        "contact_ids": [36, 35]
    }
    ```

    **Example 2 - Template with same parameters for all:**
    ```json
    {
        "campaign_name": "Promo Campaign",
        "template_name": "discount_offer",
        "template_language": "en_US",
        "contact_ids": [36, 35],
        "parameters": {"1": "20%", "2": "SAVE20"}
    }
    ```

    **Example 3 - Template with different parameters per recipient:**
    ```json
    {
        "campaign_name": "Order Updates",
        "template_name": "order_status",
        "template_language": "en_US",
        "recipients": ["919876543210", "919876543211"],
        "parameters_per_recipient": [
            {"1": "John", "2": "12345"},
            {"1": "Jane", "2": "67890"}
        ]
    }
    ```
    """
    import logging
    log = logging.getLogger("whatspy.campaigns")

    campaign_id = str(uuid.uuid4())

    # Validate at least one recipient type provided
    if not any([data.recipients, data.contact_ids, data.group_ids]):
        raise HTTPException(
            status_code=400,
            detail="At least one of recipients, contact_ids, or group_ids must be provided"
        )

    log.info(f"📢 Creating TEMPLATE broadcast campaign: {data.campaign_name}")
    log.info(f"   Template: {data.template_name} ({data.template_language})")

    # Resolve recipients
    phone_numbers = resolve_recipients(
        db=db,
        tenant_id=tenant_id,
        recipients=data.recipients,
        contact_ids=data.contact_ids,
        group_ids=data.group_ids
    )

    if not phone_numbers:
        raise HTTPException(400, "No valid recipients found. Check contact IDs, group IDs, or phone numbers.")

    log.info(f"✅ Resolved {len(phone_numbers)} phone numbers for template broadcast")

    # Create campaign
    campaign = Campaign(
        tenant_id=tenant_id,
        campaign_id=campaign_id,
        campaign_name=data.campaign_name,
        message_text=f"Template: {data.template_name}",
        total_recipients=len(phone_numbers)
    )

    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    # Start background task with template
    background_tasks.add_task(
        send_template_broadcast,
        campaign_id,
        tenant_id,
        data.template_name,
        data.template_language,
        phone_numbers,
        data.parameters,
        data.parameters_per_recipient
    )

    log.info(f"🚀 Template broadcast task started for campaign {campaign_id}")

    return campaign


async def send_template_broadcast(
    campaign_id: str,
    tenant_id: str,
    template_name: str,
    template_language: str,
    recipients: List[str],
    default_parameters: Optional[Dict[str, Any]] = None,
    parameters_per_recipient: Optional[List[Dict[str, Any]]] = None
):
    """Background task to send template messages"""
    from app.db.session import get_db_session
    from app.services.template_service import TemplateService
    from app.services import get_whatsapp_client
    from app.schemas.template import TemplateSendRequest, TemplateLanguage
    import logging

    log = logging.getLogger("whatspy.campaigns")
    wa_client = get_whatsapp_client()
    template_service = TemplateService(wa_client)

    results = []
    sent = 0
    failed = 0

    # Convert language string to enum
    try:
        lang_enum = TemplateLanguage(template_language)
    except ValueError:
        lang_enum = TemplateLanguage.ENGLISH_US
        log.warning(f"Invalid language {template_language}, defaulting to en_US")

    with get_db_session() as db:
        for idx, phone in enumerate(recipients):
            try:
                # Determine parameters for this recipient
                params = None
                if parameters_per_recipient and idx < len(parameters_per_recipient):
                    # Use specific parameters for this recipient
                    params = parameters_per_recipient[idx]
                    log.debug(f"Using specific parameters for {phone}: {params}")
                elif default_parameters:
                    # Use default parameters for all
                    params = default_parameters
                    log.debug(f"Using default parameters for {phone}: {params}")
                else:
                    # No parameters (template has no variables)
                    log.debug(f"No parameters for {phone}")

                # Send template message
                send_request = TemplateSendRequest(
                    to=phone,
                    template_name=template_name,
                    language=lang_enum,
                    parameters=params
                )

                msg_id, send_log = template_service.send_template(db, tenant_id, send_request)

                if msg_id:
                    results.append({"phone": phone, "status": "sent", "message_id": msg_id})
                    sent += 1
                    log.info(f"✅ Template sent to {phone}: {msg_id}")
                else:
                    results.append({"phone": phone, "status": "failed", "error": send_log.error_message})
                    failed += 1
                    log.error(f"❌ Template failed for {phone}: {send_log.error_message}")

                await asyncio.sleep(0.5)  # Rate limiting

            except Exception as e:
                results.append({"phone": phone, "status": "failed", "error": str(e)})
                failed += 1
                log.error(f"❌ Template failed for {phone}: {e}")

        # Update campaign
        campaign = db.query(Campaign).filter(Campaign.campaign_id == campaign_id).first()
        if campaign:
            campaign.sent_count = sent
            campaign.failed_count = failed
            campaign.results = results
            db.commit()
            log.info(f"📊 Campaign {campaign_id} completed: {sent} sent, {failed} failed")