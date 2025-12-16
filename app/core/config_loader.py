# app/core/config_loader.py
"""
Dynamic configuration loader that prioritizes database over .env files.
Supports tenant-specific WhatsApp Business API configurations.
"""
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.tenant_config import TenantConfig
from app.core import config


class ConfigLoader:
    """
    Configuration loader with database-first fallback to .env.

    Priority:
    1. Active tenant configuration from database
    2. Environment variables from .env file

    Usage:
        loader = ConfigLoader(db, tenant_id="your-tenant-id")
        phone_id = loader.get_phone_id()
        token = loader.get_access_token()
    """

    def __init__(self, db: Session, tenant_id: str):
        """
        Initialize config loader for a specific tenant.

        Args:
            db: Database session
            tenant_id: Tenant identifier
        """
        self.db = db
        self.tenant_id = tenant_id
        self._config_cache: Optional[TenantConfig] = None
        self._load_tenant_config()

    def _load_tenant_config(self):
        """Load tenant configuration from database if available"""
        if self.db:
            self._config_cache = self.db.query(TenantConfig).filter(
                TenantConfig.tenant_id == self.tenant_id,
                TenantConfig.is_active == True
            ).first()

    def get_phone_id(self) -> str:
        """Get phone_number_id (database first, then .env)"""
        if self._config_cache and self._config_cache.phone_number_id:
            return self._config_cache.phone_number_id
        return config.PHONE_ID

    def get_access_token(self) -> str:
        """Get access_token (database first, then .env)"""
        if self._config_cache and self._config_cache.access_token:
            return self._config_cache.access_token
        return config.TOKEN

    def get_verify_token(self) -> str:
        """Get verify_token (database first, then .env)"""
        if self._config_cache and self._config_cache.verify_token:
            return self._config_cache.verify_token
        return config.VERIFY_TOKEN

    def get_callback_url(self) -> str:
        """Get callback_url (database first, then .env)"""
        if self._config_cache and self._config_cache.callback_url:
            return self._config_cache.callback_url
        return config.CALLBACK_URL

    def get_fb_app_id(self) -> Optional[str]:
        """Get Facebook App ID (database first, then .env)"""
        if self._config_cache and self._config_cache.fb_app_id:
            return self._config_cache.fb_app_id
        return config.APP_ID

    def get_fb_app_secret(self) -> Optional[str]:
        """Get Facebook App Secret (database first, then .env)"""
        if self._config_cache and self._config_cache.fb_app_secret:
            return self._config_cache.fb_app_secret
        return config.APP_SECRET

    def get_waba_id(self) -> Optional[str]:
        """Get WhatsApp Business Account ID (database only)"""
        if self._config_cache:
            return self._config_cache.waba_id
        return None

    def get_redirect_url(self) -> Optional[str]:
        """Get OAuth redirect URL (database only)"""
        if self._config_cache:
            return self._config_cache.redirect_url
        return None

    def has_tenant_config(self) -> bool:
        """Check if tenant has active configuration in database"""
        return self._config_cache is not None

    def is_onboarding_completed(self) -> bool:
        """Check if tenant has completed onboarding"""
        return self._config_cache is not None and self._config_cache.onboarding_completed

    def get_all_config(self) -> Dict[str, Any]:
        """
        Get all configuration as a dictionary.
        Useful for initializing WhatsApp client.

        Returns:
            Dictionary with all config values (database-first fallback)
        """
        return {
            "phone_id": self.get_phone_id(),
            "access_token": self.get_access_token(),
            "verify_token": self.get_verify_token(),
            "callback_url": self.get_callback_url(),
            "fb_app_id": self.get_fb_app_id(),
            "fb_app_secret": self.get_fb_app_secret(),
            "waba_id": self.get_waba_id(),
            "redirect_url": self.get_redirect_url(),
            "has_tenant_config": self.has_tenant_config(),
            "onboarding_completed": self.is_onboarding_completed(),
        }


# ────────────────────────────────────────────────────────────────────
# Helper Functions (Convenience Methods)
# ────────────────────────────────────────────────────────────────────

def get_whatsapp_config(db: Session, tenant_id: str) -> Dict[str, Any]:
    """
    Convenience function to get WhatsApp configuration for a tenant.

    Args:
        db: Database session
        tenant_id: Tenant identifier

    Returns:
        Dictionary with WhatsApp configuration

    Example:
        from app.core.config_loader import get_whatsapp_config

        config = get_whatsapp_config(db, tenant_id)
        phone_id = config["phone_id"]
        access_token = config["access_token"]
    """
    loader = ConfigLoader(db, tenant_id)
    return loader.get_all_config()


def get_phone_id_for_tenant(db: Session, tenant_id: str) -> str:
    """Get phone_id for tenant (database-first)"""
    loader = ConfigLoader(db, tenant_id)
    return loader.get_phone_id()


def get_access_token_for_tenant(db: Session, tenant_id: str) -> str:
    """Get access_token for tenant (database-first)"""
    loader = ConfigLoader(db, tenant_id)
    return loader.get_access_token()


def is_tenant_onboarded(db: Session, tenant_id: str) -> bool:
    """Check if tenant has completed WhatsApp onboarding"""
    loader = ConfigLoader(db, tenant_id)
    return loader.is_onboarding_completed()
