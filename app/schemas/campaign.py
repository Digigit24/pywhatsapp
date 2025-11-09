# app/schemas/campaign.py
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class CampaignCreate(BaseModel):
    campaign_name: str
    message_text: str = Field(..., min_length=1, max_length=4096)
    recipients: List[str] = Field(..., min_items=1)  # Phone numbers

class CampaignResponse(BaseModel):
    id: int
    tenant_id: str
    campaign_id: str
    campaign_name: Optional[str]
    total_recipients: int
    sent_count: int
    failed_count: int
    results: Optional[List[Dict[str, Any]]] = None
    created_at: datetime
    
    class Config:
        from_attributes = True