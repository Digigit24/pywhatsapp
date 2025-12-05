# app/models/media.py
"""
Media model for storing uploaded files.
"""
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime
from app.models.base import Base

class Media(Base):
    """Store uploaded media files metadata"""
    __tablename__ = "media"
    
    # Explicitly define all fields to avoid ID conflict with BaseModel
    id = Column(String(36), primary_key=True, index=True)
    tenant_id = Column(String(100), index=True, nullable=False, default="default")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    filename = Column(String(255), nullable=False)
    mime_type = Column(String(100), nullable=False)
    file_size = Column(Integer, nullable=True)
    whatsapp_media_id = Column(String(255), nullable=True, index=True)
    storage_path = Column(String(512), nullable=True)  # Path on disk
    
    def __repr__(self):
        return f"<Media {self.id} ({self.filename})>"
