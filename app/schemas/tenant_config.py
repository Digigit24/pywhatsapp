# app/schemas/tenant_config.py
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional
from datetime import datetime


class TenantConfigBase(BaseModel):
    """Base schema for tenant configuration"""
    user_id: Optional[str] = None
    waba_id: Optional[str] = Field(None, description="WhatsApp Business Account ID")
    phone_number_id: Optional[str] = Field(None, description="Phone Number ID")
    fb_app_id: Optional[str] = Field(None, description="Facebook App ID")
    callback_url: Optional[str] = Field(None, description="Webhook callback URL")
    redirect_url: Optional[str] = Field(None, description="OAuth redirect URL")
    verify_token: Optional[str] = Field(None, description="Webhook verify token")


class TenantConfigCreate(TenantConfigBase):
    """Schema for creating tenant configuration"""
    pass


class TenantConfigUpdate(BaseModel):
    """Schema for updating tenant configuration (all fields optional)"""
    user_id: Optional[str] = None
    waba_id: Optional[str] = None
    phone_number_id: Optional[str] = None
    access_token: Optional[str] = None
    fb_app_id: Optional[str] = None
    fb_app_secret: Optional[str] = None
    callback_url: Optional[str] = None
    redirect_url: Optional[str] = None
    verify_token: Optional[str] = None
    is_active: Optional[bool] = None


class TenantConfigResponse(TenantConfigBase):
    """Schema for tenant configuration response (sensitive data masked)"""
    id: int
    tenant_id: str
    access_token: Optional[str] = Field(None, description="Masked access token")
    fb_app_secret: Optional[str] = Field(None, description="Masked app secret")
    token_expires_at: Optional[datetime] = None
    is_active: bool
    onboarding_completed: bool
    onboarded_at: Optional[datetime] = None
    last_verified_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TenantConfigFullResponse(TenantConfigResponse):
    """Schema with full data including sensitive fields (admin only)"""
    access_token: Optional[str] = Field(None, description="Full access token")
    fb_app_secret: Optional[str] = Field(None, description="Full app secret")
    refresh_token: Optional[str] = None

    class Config:
        from_attributes = True


class WhatsAppOnboardingRequest(BaseModel):
    """Schema for WhatsApp OAuth onboarding"""
    code: str = Field(..., description="OAuth authorization code from Meta")
    waba_id: str = Field(..., description="WhatsApp Business Account ID")
    phone_number_id: str = Field(..., description="Phone Number ID")
    redirect_uri: str = Field(..., description="Redirect URI used in OAuth flow")


class WhatsAppOnboardingResponse(BaseModel):
    """Response after successful onboarding"""
    success: bool
    message: str
    tenant_id: str
    config_id: int
    waba_id: str
    phone_number_id: str
