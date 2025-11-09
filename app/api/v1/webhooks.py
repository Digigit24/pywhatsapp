# app/api/v1/webhooks.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta

from app.db.session import get_db
from app.api.deps import get_tenant_id_flexible
from app.models.webhook import WebhookLog
from pydantic import BaseModel

router = APIRouter()

class WebhookLogResponse(BaseModel):
    id: int
    tenant_id: str
    log_type: str
    phone: Optional[str]
    message_id: Optional[str]
    status: Optional[str]
    error_message: Optional[str]
    context: Optional[str]
    raw_data: Optional[dict]
    created_at: datetime
    
    class Config:
        from_attributes = True

@router.get("/logs", response_model=List[WebhookLogResponse])
def get_webhook_logs(
    limit: int = Query(50, le=200),
    skip: int = 0,
    log_type: Optional[str] = None,
    phone: Optional[str] = None,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id_flexible)
):
    """Get webhook logs"""
    query = db.query(WebhookLog).filter(WebhookLog.tenant_id == tenant_id)
    
    if log_type:
        query = query.filter(WebhookLog.log_type == log_type)
    
    if phone:
        query = query.filter(WebhookLog.phone.ilike(f"%{phone}%"))
    
    # Get recent logs first
    logs = query.order_by(WebhookLog.created_at.desc()).offset(skip).limit(limit).all()
    
    return logs

@router.delete("/logs/cleanup")
def cleanup_old_logs(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id_flexible)
):
    """Clean up webhook logs older than specified days"""
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    deleted_count = db.query(WebhookLog).filter(
        WebhookLog.tenant_id == tenant_id,
        WebhookLog.created_at < cutoff_date
    ).delete()
    
    db.commit()
    
    return {"deleted": deleted_count, "cutoff_date": cutoff_date}