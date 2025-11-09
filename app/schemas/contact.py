# app/schemas/contact.py
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime

class ContactBase(BaseModel):
    phone: str = Field(..., min_length=10, max_length=15)
    name: Optional[str] = None
    notes: Optional[str] = None
    labels: List[str] = Field(default_factory=list)
    groups: List[str] = Field(default_factory=list)
    assigned_to: Optional[int] = None  # User ID
    
    @validator('phone')
    def validate_phone(cls, v):
        clean = v.replace('+', '').replace(' ', '').replace('-', '')
        if not clean.isdigit():
            raise ValueError('Phone must contain only digits')
        return clean

class ContactCreate(ContactBase):
    pass

class ContactUpdate(BaseModel):
    name: Optional[str] = None
    notes: Optional[str] = None
    labels: Optional[List[str]] = None
    groups: Optional[List[str]] = None
    is_business: Optional[bool] = None
    assigned_to: Optional[int] = None

class ContactResponse(ContactBase):
    id: int
    tenant_id: str
    profile_pic_url: Optional[str] = None
    status: Optional[str] = None
    is_business: bool = False
    business_description: Optional[str] = None
    last_seen: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True