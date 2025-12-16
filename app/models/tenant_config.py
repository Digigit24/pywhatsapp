# app/models/tenant_config.py
"""
Tenant Configuration model for storing WhatsApp Business API credentials
and settings per tenant.
"""
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Boolean, Index
from app.models.base import BaseModel


class TenantConfig(BaseModel):
    """
    Store tenant-specific WhatsApp Business API configuration.
    Overrides global .env settings when available.
    """
    __tablename__ = "tenant_configs"

    # User who owns/created this config
    user_id = Column(String(255), nullable=True, index=True)

    # WhatsApp Business Account Configuration
    waba_id = Column(String(255), nullable=True)  # WhatsApp Business Account ID
    phone_number_id = Column(String(255), nullable=True)  # Phone Number ID
    access_token = Column(Text, nullable=True)  # Long-lived access token

    # Facebook App Configuration
    fb_app_id = Column(String(255), nullable=True)
    fb_app_secret = Column(String(255), nullable=True)

    # Webhook Configuration
    callback_url = Column(String(500), nullable=True)  # Webhook callback URL
    redirect_url = Column(String(500), nullable=True)  # OAuth redirect URL
    verify_token = Column(String(255), nullable=True)  # Webhook verify token

    # Token Management
    token_expires_at = Column(DateTime, nullable=True)  # Access token expiration
    refresh_token = Column(Text, nullable=True)  # Refresh token (if available)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    onboarding_completed = Column(Boolean, default=False, nullable=False)

    # Metadata
    onboarded_at = Column(DateTime, nullable=True)  # When onboarding was completed
    last_verified_at = Column(DateTime, nullable=True)  # Last token verification

    def __repr__(self):
        return f"<TenantConfig tenant_id={self.tenant_id} waba_id={self.waba_id}>"

    def to_dict(self):
        """Convert to dictionary, excluding sensitive fields by default"""
        data = super().to_dict()
        # Mask sensitive data
        if data.get('access_token'):
            data['access_token'] = '***' + data['access_token'][-4:] if len(data['access_token']) > 4 else '***'
        if data.get('fb_app_secret'):
            data['fb_app_secret'] = '***' + data['fb_app_secret'][-4:] if len(data['fb_app_secret']) > 4 else '***'
        if data.get('refresh_token'):
            data['refresh_token'] = '***' + data['refresh_token'][-4:] if len(data['refresh_token']) > 4 else '***'
        return data

    def to_dict_full(self):
        """Convert to dictionary with all fields (admin use only)"""
        return super().to_dict()


# Create composite index for faster lookups
Index('idx_tenant_user', TenantConfig.tenant_id, TenantConfig.user_id)
