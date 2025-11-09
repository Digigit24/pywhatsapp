# app/models/campaign.py
from sqlalchemy import Column, String, Text, Integer, JSON
from app.models.base import BaseModel

class Campaign(BaseModel):
    __tablename__ = "campaigns"
    
    campaign_id = Column(String(100), unique=True, index=True, nullable=False)
    campaign_name = Column(String(255), nullable=True)
    message_text = Column(Text, nullable=False)
    total_recipients = Column(Integer, default=0)
    sent_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    results = Column(JSON, nullable=True)