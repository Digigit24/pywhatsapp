# app/schemas/campaign.py
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any
from datetime import datetime

class CampaignCreate(BaseModel):
    campaign_name: str
    message_text: str = Field(..., min_length=1, max_length=4096)

    # Support multiple recipient types
    recipients: Optional[List[str]] = Field(None, description="Direct phone numbers")
    contact_ids: Optional[List[str]] = Field(None, description="Contact UUIDs from database")
    group_ids: Optional[List[str]] = Field(None, description="Group UUIDs from database")

    @field_validator('recipients', 'contact_ids', 'group_ids', mode='after')
    @classmethod
    def validate_at_least_one_recipient_type(cls, v, info):
        """Ensure at least one recipient type is provided"""
        data = info.data
        if not any([
            data.get('recipients'),
            data.get('contact_ids'),
            data.get('group_ids')
        ]):
            raise ValueError('At least one of recipients, contact_ids, or group_ids must be provided')
        return v

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