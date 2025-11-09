# app/models/template.py
"""
WhatsApp Template models for storing template definitions and tracking.
Supports PyWa template structure.
"""
from sqlalchemy import Column, String, Text, JSON, Integer, Boolean, Enum as SQLEnum
from app.models.base import BaseModel
import enum


class TemplateStatus(str, enum.Enum):
    """Template status from WhatsApp"""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PAUSED = "PAUSED"
    DISABLED = "DISABLED"


class TemplateCategory(str, enum.Enum):
    """Template categories"""
    MARKETING = "MARKETING"
    UTILITY = "UTILITY"
    AUTHENTICATION = "AUTHENTICATION"


class WhatsAppTemplate(BaseModel):
    """Store WhatsApp template definitions"""
    __tablename__ = "whatsapp_templates"
    
    # Template identification
    template_id = Column(String(255), index=True, nullable=True)  # WhatsApp template ID
    name = Column(String(255), index=True, nullable=False)  # Template name
    language = Column(String(10), nullable=False)  # e.g., "en_US", "en", "hi"
    
    # Template details
    category = Column(SQLEnum(TemplateCategory), nullable=False)
    status = Column(SQLEnum(TemplateStatus), default=TemplateStatus.PENDING)
    
    # Template structure (stored as JSON)
    components = Column(JSON, nullable=False)  # PyWa template components
    
    # Additional metadata
    quality_score = Column(String(20), nullable=True)  # HIGH, MEDIUM, LOW
    rejection_reason = Column(Text, nullable=True)
    
    # Usage tracking
    usage_count = Column(Integer, default=0)
    last_used_at = Column(String, nullable=True)
    
    # Library template info (if created from library)
    library_template_name = Column(String(255), nullable=True)
    
    def __repr__(self):
        return f"<WhatsAppTemplate {self.name} ({self.language}) - {self.status}>"


class TemplateSendLog(BaseModel):
    """Log template message sends for analytics"""
    __tablename__ = "template_send_logs"
    
    template_id = Column(Integer, index=True, nullable=False)  # FK to whatsapp_templates
    template_name = Column(String(255), index=True, nullable=False)
    
    recipient_phone = Column(String(50), index=True, nullable=False)
    message_id = Column(String(255), nullable=True)  # WhatsApp message ID
    
    # Parameters used
    parameters = Column(JSON, nullable=True)
    
    # Status tracking
    send_status = Column(String(50), default="sent")  # sent, failed, delivered, read
    error_message = Column(Text, nullable=True)
    
    def __repr__(self):
        return f"<TemplateSendLog {self.template_name} to {self.recipient_phone}>"