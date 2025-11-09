# app/schemas/group.py
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class GroupBase(BaseModel):
    group_id: str = Field(..., description="WhatsApp Group ID")
    name: str = Field(..., description="Group name")
    description: Optional[str] = None
    participants: List[str] = Field(default_factory=list, description="List of participant phone numbers")
    admins: List[str] = Field(default_factory=list, description="List of admin phone numbers")

class GroupCreate(GroupBase):
    """Create new group"""
    pass

class GroupUpdate(BaseModel):
    """Update existing group"""
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    participants: Optional[List[str]] = None
    admins: Optional[List[str]] = None

class GroupResponse(GroupBase):
    """Group response"""
    id: int
    tenant_id: str
    created_by: Optional[str] = None
    group_invite_link: Optional[str] = None
    is_active: bool = True
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True