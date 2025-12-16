# app/schemas/campaign.py
from pydantic import BaseModel, Field, model_validator
from typing import List, Optional, Dict, Any
from datetime import datetime

class CampaignCreate(BaseModel):
    campaign_name: str
    message_text: str = Field(..., min_length=1, max_length=4096)

    # Support multiple recipient types
    recipients: Optional[List[str]] = Field(None, description="Direct phone numbers")
    contact_ids: Optional[List[int]] = Field(None, description="Contact IDs from database")
    group_ids: Optional[List[int]] = Field(None, description="Group IDs from database")

    @model_validator(mode='after')
    def validate_at_least_one_recipient_type(self):
        """Ensure at least one recipient type is provided"""
        if not any([
            self.recipients,
            self.contact_ids,
            self.group_ids
        ]):
            raise ValueError('At least one of recipients, contact_ids, or group_ids must be provided')
        return self

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