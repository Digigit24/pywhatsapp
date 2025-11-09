# app/models/group.py
"""WhatsApp Group model"""
from sqlalchemy import Column, String, Text, Boolean, JSON
from app.models.base import BaseModel


class Group(BaseModel):
    """Store WhatsApp group information"""
    __tablename__ = "groups"
    
    group_id = Column(String(100), index=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    participants = Column(JSON, nullable=True, default=list)  # List of phone numbers
    admins = Column(JSON, nullable=True, default=list)  # List of admin phone numbers
    created_by = Column(String(50), nullable=True)
    group_invite_link = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)
    
    def __repr__(self):
        return f"<Group {self.name}>"