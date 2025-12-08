# app/models/message.py
"""
Message models for WhatsApp messages and templates.
"""
from sqlalchemy import Column, String, Text, JSON, Integer
from app.models.base import BaseModel


class Message(BaseModel):
    """Store all WhatsApp messages (incoming and outgoing)"""
    __tablename__ = "messages"

    message_id = Column(String(255), unique=True, index=True, nullable=True)
    phone = Column(String(50), index=True, nullable=False)
    contact_name = Column(String(255), nullable=True)
    text = Column(Text, nullable=True)
    message_type = Column(String(50), nullable=True)
    direction = Column(String(20), nullable=False)  # 'incoming' or 'outgoing'
    status = Column(String(20), nullable=True, default='sent')  # 'sent', 'delivered', 'read', 'failed'
    meta_data = Column(JSON, nullable=True)

    def __repr__(self):
        return f"<Message {self.message_id} from {self.phone}>"


class MessageTemplate(BaseModel):
    """Store reusable message templates"""
    __tablename__ = "message_templates"
    
    name = Column(String(255), index=True, nullable=False)
    content = Column(Text, nullable=False)
    variables = Column(JSON, nullable=True)  # List of variable names like ["name", "code"]
    category = Column(String(100), default="general")
    usage_count = Column(Integer, default=0)
    
    def __repr__(self):
        return f"<MessageTemplate {self.name}>"