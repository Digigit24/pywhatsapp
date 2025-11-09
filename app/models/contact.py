# app/models/contact.py
"""Contact model with assigned_to field"""
from sqlalchemy import Column, String, Text, Boolean, JSON, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class Contact(BaseModel):
    __tablename__ = "contacts"
    __table_args__ = (
        UniqueConstraint('tenant_id', 'phone', name='uq_tenant_phone'),
    )
    
    phone = Column(String(50), index=True, nullable=False, unique=True)
    name = Column(String(255), nullable=True)
    profile_pic_url = Column(String(500), nullable=True)
    status = Column(String(500), nullable=True)
    is_business = Column(Boolean, default=False)
    business_description = Column(Text, nullable=True)
    labels = Column(JSON, nullable=True, default=list)
    groups = Column(JSON, nullable=True, default=list)
    notes = Column(Text, nullable=True)
    last_seen = Column(String, nullable=True)
    
    # NEW: Assign contact to a user
    assigned_to = Column(Integer, ForeignKey('admin_users.id'), nullable=True)
    
    def __repr__(self):
        return f"<Contact {self.name or self.phone}>"