# app/api/v1/campaigns.py
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
import uuid
import asyncio

from app.db.session import get_db
from app.api.deps import get_tenant_id_flexible
from app.services import get_message_service
from app.models.campaign import Campaign
from app.schemas.campaign import CampaignCreate, CampaignResponse
from app.schemas.message import MessageCreate

router = APIRouter()

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
    """Create broadcast campaign"""
    campaign_id = str(uuid.uuid4())
    
    campaign = Campaign(
        tenant_id=tenant_id,
        campaign_id=campaign_id,
        campaign_name=data.campaign_name,
        message_text=data.message_text,
        total_recipients=len(data.recipients)
    )
    
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    
    # Start background task
    background_tasks.add_task(
        send_broadcast,
        campaign_id,
        tenant_id,
        data.message_text,
        data.recipients
    )
    
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