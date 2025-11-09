# app/models/user.py
"""
Admin User model for session-based authentication.
System-wide users (no tenant isolation).
"""
from sqlalchemy import Column, String, Boolean, DateTime
from app.models.base import TimestampMixin


class AdminUser(TimestampMixin):
    """
    Admin user for HTML UI access.
    Legacy session-based authentication.
    """
    __tablename__ = "admin_users"
    
    username = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    last_login = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<AdminUser {self.username}>"