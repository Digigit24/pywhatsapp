# app/api/v1/campaigns.py
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from typing import List
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

async def send_broadcast(campaign_id: str, tenant_id: str, message_text: str, recipients: List[str]):
    """Background task to send messages"""
    from app.db.session import get_db_session
    from app.services import get_message_service
    
    service = get_message_service()
    results = []
    sent = 0
    failed = 0
    
    with get_db_session() as db:
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

@router.post("/broadcast", response_model=CampaignResponse)
async def create_broadcast(
    data: CampaignCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id_flexible)
):
    """
    Create broadcast campaign

    Accepts recipients via:
    - recipients: Direct phone numbers array (e.g., ["919876543210", "919876543211"])
    - contact_ids: Contact integer IDs from database (e.g., [36, 35])
    - group_ids: Group integer IDs from database (sends to all participants)

    At least one recipient type must be provided.
    """
    import logging
    log = logging.getLogger("whatspy.campaigns")

    campaign_id = str(uuid.uuid4())

    log.info(f"📢 Creating broadcast campaign: {data.campaign_name}")
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

    log.info(f"✅ Resolved {len(phone_numbers)} phone numbers: {phone_numbers}")

    # Validate we have recipients
    if not phone_numbers:
        log.error("❌ No valid recipients found after resolving contact/group IDs")
        raise HTTPException(
            status_code=400,
            detail="No valid recipients found. Please check contact IDs, group IDs, or phone numbers."
        )

    campaign = Campaign(
        tenant_id=tenant_id,
        campaign_id=campaign_id,
        campaign_name=data.campaign_name,
        message_text=data.message_text,
        total_recipients=len(phone_numbers)
    )

    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    log.info(f"📋 Campaign created: {campaign_id} with {len(phone_numbers)} recipients")

    # Start background task with resolved phone numbers
    background_tasks.add_task(
        send_broadcast,
        campaign_id,
        tenant_id,
        data.message_text,
        phone_numbers
    )

    log.info(f"🚀 Background broadcast task started for campaign {campaign_id}")

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