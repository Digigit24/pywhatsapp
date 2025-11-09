# app/api/deps.py
"""
API dependencies for authentication and database access.
Supports both session-based (HTML UI) and JWT (API) authentication.
"""
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.jwt_auth import JWTAuth

# Security scheme (optional to allow both auth methods)
security = HTTPBearer(auto_error=False)


# ────────────────────────────────────────────
# Session-based Authentication (HTML UI)
# ────────────────────────────────────────────

def get_current_user_session(request: Request) -> Optional[str]:
    """Get current authenticated user from session"""
    return request.session.get("username")


def require_auth_session(request: Request):
    """
    Dependency to require session-based authentication.
    Used for HTML UI routes.
    """
    username = get_current_user_session(request)
    if not username:
        # For API endpoints, return 401
        if request.url.path.startswith("/api/"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated"
            )
        # For page routes, redirect to login
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            detail="Not authenticated",
            headers={"Location": "/login"}
        )
    return username


def optional_auth_session(request: Request) -> Optional[str]:
    """Optional session authentication - returns username if logged in"""
    return get_current_user_session(request)


# ────────────────────────────────────────────
# Flexible Authentication (Session + JWT)
# ────────────────────────────────────────────

async def get_current_user_flexible(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Dict[str, Any]:
    """
    Flexible authentication - accepts JWT, session, or development header.
    
    Priority:
    1. JWT Bearer token (for API/React)
    2. Session cookie (for HTML UI)
    3. X-Tenant-Id header (for development)
    
    Returns user info dict with auth_type, user_id, tenant_id
    """
    # Try JWT authentication first (for API clients)
    if credentials and credentials.credentials:
        try:
            payload = JWTAuth.decode_token(credentials.credentials)
            
            return {
                "auth_type": "jwt",
                "user_id": JWTAuth.get_user_id(payload),
                "tenant_id": JWTAuth.get_tenant_id(payload) or "default",
                "username": payload.get("email") or payload.get("username"),
                "payload": payload
            }
        except HTTPException:
            # JWT validation failed, fall through to session auth
            pass
    
    # Try session authentication (for HTML UI)
    username = request.session.get("username")
    if username:
        return {
            "auth_type": "session",
            "username": username,
            "tenant_id": "default",  # Default tenant for session users
            "user_id": username
        }
    
    # For development: Allow requests with X-Tenant-Id header
    tenant_id = request.headers.get("x-tenant-id")
    if tenant_id:
        return {
            "auth_type": "development",
            "username": "dev-user",
            "tenant_id": tenant_id,
            "user_id": "dev-user"
        }
    
    # No authentication found
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Provide JWT token, login via session, or X-Tenant-Id header for development."
    )


async def get_tenant_id_flexible(
    request: Request,
    user: Dict[str, Any] = Depends(get_current_user_flexible)
) -> str:
    """
    Get tenant_id from JWT, session, or header.
    
    Priority:
    1. JWT token payload
    2. X-Tenant-Id header (for development)
    3. Session users: Use default tenant
    """
    # First try to get from user (JWT)
    tenant_id = user.get("tenant_id")
    
    # If not found, try header (for development)
    if not tenant_id:
        tenant_id = request.headers.get("x-tenant-id")
    
    # Fallback to default
    if not tenant_id:
        tenant_id = "default"
    
    return tenant_id


# ────────────────────────────────────────────
# Aliases for backward compatibility
# ────────────────────────────────────────────

# For routes that need flexible auth (both session and JWT)
require_auth_flexible = get_current_user_flexible

# For routes that only need session auth (HTML UI)
require_auth = require_auth_session
optional_auth = optional_auth_session