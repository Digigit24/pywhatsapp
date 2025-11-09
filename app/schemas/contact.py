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
        if not v or not v.strip():
            raise ValueError('Phone number is required')
        
        # Preserve the original format but validate structure
        original = v.strip()
        
        # Clean for validation by removing formatting characters
        clean = v.replace('+', '').replace(' ', '').replace('-', '').replace('(', '').replace(')', '').strip()
        
        # Check if the cleaned phone contains only digits
        if not clean.isdigit():
            raise ValueError('Phone number must contain only digits (with optional +, spaces, hyphens, parentheses)')
        
        # Check length (should be between 10-15 digits for international numbers)
        if len(clean) < 10 or len(clean) > 15:
            raise ValueError('Phone number must be between 10-15 digits')
        
        # Return original format to preserve country codes like +91
        return original

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