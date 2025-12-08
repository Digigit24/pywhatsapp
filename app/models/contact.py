# app/models/contact.py
"""Contact model with assigned_to field"""
from sqlalchemy import Column, String, Text, Boolean, JSON, UniqueConstraint, DateTime
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
    # Allow UUID/string identifiers for assignment (no FK enforced)
    assigned_to = Column(String(100), nullable=True)

    # 24-hour conversation window tracking
    last_message_from_user = Column(DateTime, nullable=True)  # Last incoming message timestamp
    conversation_window_expires_at = Column(DateTime, nullable=True)  # Expiry time (last_msg + 24h)

    def __repr__(self):
        return f"<Contact {self.name or self.phone}>"
