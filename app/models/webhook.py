# app/models/webhook.py
"""
Webhook activity logging models.
"""
from sqlalchemy import Column, String, Text, JSON
from app.models.base import BaseModel


class WebhookLog(BaseModel):
    """Log all webhook activity from Meta"""
    __tablename__ = "webhook_logs"
    
    log_type = Column(String(50), index=True)  # 'message', 'status', 'error'
    phone = Column(String(50), nullable=True)
    message_id = Column(String(255), nullable=True)
    status = Column(String(50), nullable=True)
    error_message = Column(Text, nullable=True)
    context = Column(String(255), nullable=True)
    raw_data = Column(JSON, nullable=True)
    
    def __repr__(self):
        return f"<WebhookLog {self.log_type} - {self.phone}>"


class MessageReaction(BaseModel):
    """Store message reactions"""
    __tablename__ = "message_reactions"
    
    message_id = Column(String(255), index=True, nullable=False)
    phone = Column(String(50), nullable=False)
    emoji = Column(String(10), nullable=False)
    
    def __repr__(self):
        return f"<MessageReaction {self.emoji} on {self.message_id}>"