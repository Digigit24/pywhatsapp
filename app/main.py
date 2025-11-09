# app/main.py
"""
FastAPI application with new architecture.
Supports both session-based (HTML UI) and JWT (API) authentication.

FIXES APPLIED:
1. Added /api/stats endpoint (was only at /api/messages/stats)
2. Added /api/conversations endpoint (was only at /api/messages/conversations)  
3. Fixed conversations response to always return an array
4. Added WebSocket error handling
"""
import logging
from pathlib import Path
from fastapi import FastAPI, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import (
    PHONE_ID, TOKEN, VERIFY_TOKEN, CALLBACK_URL,
    SESSION_SECRET_KEY, SESSION_MAX_AGE, JWT_SECRET_KEY,
    MAX_BUFFER, VALIDATE_UPDATES, DEFAULT_TENANT_ID
)
from app.db.session import init_db, test_db_connection
from app.core.security import authenticate_user
from app.api.deps import require_auth_session, optional_auth_session, require_auth_flexible, get_current_user_flexible, get_tenant_id_flexible
from app.api.v1.router import api_router
from app.services import set_whatsapp_client
from fastapi import WebSocket, WebSocketDisconnect
from app.ws.manager import ws_manager

# Logging
logging.basicConfig(level="INFO", format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
log = logging.getLogger("whatspy")

# Initialize database
try:
    init_db()
    if test_db_connection():
        log.info("✅ Database initialized")
except Exception as e:
    log.error(f"❌ Database error: {e}")

# Templates
BASE_DIR = Path(__file__).parent.parent
jinja_templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# FastAPI app
app = FastAPI(
    title="Whatspy - WhatsApp API",
    description="Multi-tenant WhatsApp Business API",
    version="3.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS - Enhanced configuration matching old version
app.add_middleware(
    CORSMiddleware,
    # Explicitly allow common localhost dev origins
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",  # Vite default port
        "http://127.0.0.1:5173",
        "https://whatsapp.dglinkup.com",  # Add your production domain
    ],
    # Also accept any localhost/127.0.0.1 with any port (dev convenience)
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    # Required to support cookies/authorization headers across origins
    allow_credentials=True,
    # Explicit methods to ensure preflight passes everywhere
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    # Allow any request headers (covers X-Tenant-Id, X-Tenant-Slug, tenanttoken, etc.)
    allow_headers=["*"],
    # Headers the browser is allowed to read from responses
    expose_headers=[
        "X-Tenant",
        "X-Tenant-Id",
        "X-Tenant-Slug",
        "tenanttoken",
        "Authorization",
        "Content-Type",
        "Set-Cookie",
    ],
    # Cache preflight for a day to reduce OPTIONS noise
    max_age=86400,
)

# Session middleware
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET_KEY,
    max_age=SESSION_MAX_AGE,
    same_site="lax",
    https_only=False
)

# ────────────────────────────────────────────
# Development Middleware - Default Tenant ID
# ────────────────────────────────────────────

@app.middleware("http")
async def add_default_tenant_header(request: Request, call_next):
    """
    Development middleware to add tenant ID header for API calls without JWT.
    Uses session tenant if available, otherwise falls back to default.
    """
    # Only add tenant header for API routes if no auth header present
    if request.url.path.startswith("/api/") and not request.headers.get("authorization"):
        # Create a mutable copy of headers
        mutable_headers = dict(request.headers)
        # Prefer existing header if provided; else use session tenant; else default
        if "x-tenant-id" not in mutable_headers or not mutable_headers.get("x-tenant-id"):
            tenant_from_session = request.session.get("tenant_id") if hasattr(request, "session") else None
            mutable_headers["x-tenant-id"] = tenant_from_session or DEFAULT_TENANT_ID
        # Apply updated headers to the request
        request._headers = mutable_headers

    response = await call_next(request)
    return response

# WhatsApp client
wa = None
if PHONE_ID and TOKEN and VERIFY_TOKEN:
    try:
        from pywa import WhatsApp
        from app.services.whatsapp_handlers import register_handlers
        
        wa = WhatsApp(
            phone_id=PHONE_ID,
            token=TOKEN,
            server=app,
            verify_token=VERIFY_TOKEN,
            validate_updates=VALIDATE_UPDATES
        )
        set_whatsapp_client(wa)
        register_handlers(wa)  # Register message handlers
        log.info("✅ WhatsApp client initialized")
    except Exception as e:
        log.error(f"❌ WhatsApp init failed: {e}")
else:
    log.warning("⚠️  WhatsApp not configured")

# Include API routes with correct prefix
app.include_router(
    api_router,
    prefix="/api"  # Changed from /api/v1 to /api to match frontend expectations
    # Removed global dependencies - each endpoint handles its own auth
)

# ────────────────────────────────────────────
# Backward Compatibility Routes (CRITICAL FIX)
# These allow frontend to call /api/stats and /api/conversations directly
# ────────────────────────────────────────────

from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services import get_message_service

@app.get("/api/stats")
def get_stats_compat(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id_flexible),
    service = Depends(get_message_service)
):
    """Get message statistics - backward compatible endpoint"""
    from sqlalchemy import func
    from app.models.message import Message
    from datetime import datetime, timedelta
    
    # Total messages
    total_messages = db.query(Message).filter(Message.tenant_id == tenant_id).count()
    
    # Messages by direction
    direction_stats = db.query(
        Message.direction,
        func.count(Message.id).label('count')
    ).filter(
        Message.tenant_id == tenant_id
    ).group_by(Message.direction).all()
    
    # Messages by type
    type_stats = db.query(
        Message.message_type,
        func.count(Message.id).label('count')
    ).filter(
        Message.tenant_id == tenant_id
    ).group_by(Message.message_type).all()
    
    # Recent activity (last 7 days)
    week_ago = datetime.utcnow() - timedelta(days=7)
    recent_messages = db.query(Message).filter(
        Message.tenant_id == tenant_id,
        Message.created_at >= week_ago
    ).count()
    
    # Unique contacts
    unique_contacts = db.query(Message.phone).filter(
        Message.tenant_id == tenant_id
    ).distinct().count()
    
    return {
        "total_messages": total_messages,
        "unique_contacts": unique_contacts,
        "recent_messages": recent_messages,
        "by_direction": {stat.direction: stat.count for stat in direction_stats},
        "by_type": {stat.message_type: stat.count for stat in type_stats}
    }


@app.get("/api/conversations")
def list_conversations_compat(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id_flexible),
    service = Depends(get_message_service)
):
    """
    List all conversations - backward compatible endpoint
    
    CRITICAL: Returns an array to prevent "conversations.filter is not a function" error
    """
    try:
        conversations = service.get_conversations(db, tenant_id)
        
        # CRITICAL FIX: Ensure we return an array, not an object
        # The frontend expects an array to call .filter()
        if not isinstance(conversations, list):
            log.warning("⚠️ get_conversations returned non-list, returning empty array")
            return []
        
        return conversations
    except Exception as e:
        log.error(f"❌ Failed to get conversations: {e}")
        # Return empty array instead of error to prevent frontend crash
        return []


@app.get("/api/conversations/{phone}")
def get_conversation_compat(
    phone: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id_flexible),
    service = Depends(get_message_service)
):
    """Get conversation with specific number - backward compatible endpoint"""
    messages = service.get_conversation(db, tenant_id, phone)
    return {"phone": phone, "messages": messages}

# Mount static files
try:
    app.mount("/static", StaticFiles(directory=str(BASE_DIR / "templates")), name="static")
except:
    log.warning("⚠️  Static files not mounted")

# Public routes
# CORS preflight handler for any /api/* path (defensive fallback)
@app.options("/api/{path:path}", include_in_schema=False)
async def cors_preflight(path: str, request: Request):
    """Return 204 No Content; CORSMiddleware will attach proper CORS headers"""
    from fastapi import Response
    return Response(status_code=204)

@app.get(
    "/healthz",
    summary="Health Check",
    tags=["System"],
    response_description="System health status"
)
def health():
    """
    Public health check endpoint.
    
    Returns system status including:
    - Database connectivity
    - WhatsApp API configuration status
    - JWT authentication status
    """
    db_ok = test_db_connection()
    return {
        "status": "ok" if db_ok else "degraded",
        "phone_id_ok": bool(PHONE_ID),
        "token_ok": bool(TOKEN),
        "verify_token_ok": bool(VERIFY_TOKEN),
        "database_ok": db_ok,
        "jwt_enabled": bool(JWT_SECRET_KEY),
        "buffer_size": MAX_BUFFER,
    }

@app.get("/", include_in_schema=False)
def index(request: Request, username: str = Depends(optional_auth_session)):
    """Root"""
    if username:
        return RedirectResponse(url="/chat", status_code=303)
    return RedirectResponse(url="/login", status_code=303)

# Auth routes
@app.get("/login", include_in_schema=False)
def login_page(request: Request):
    """Login page"""
    # If already logged in, go to chat
    if request.session.get("username"):
        return RedirectResponse(url="/chat", status_code=303)

    # Extract error from query string and map to friendly message
    error_param = request.query_params.get("error")
    error_msg = None
    if error_param == "Invalid":
        error_msg = "Invalid username or password"
    elif error_param:
        error_msg = error_param

    # Prefill tenant from session (if any) to help the user
    tenant_id = request.session.get("tenant_id", DEFAULT_TENANT_ID)

    return jinja_templates.TemplateResponse("login.html", {
        "request": request,
        "error": error_msg,
        "tenant_id": tenant_id
    })

@app.post("/login", include_in_schema=False)
async def login(request: Request, username: str = Form(...), password: str = Form(...), tenant_id: str = Form(None)):
    """Login"""
    user = authenticate_user(username, password)
    if not user:
        return RedirectResponse(url="/login?error=Invalid", status_code=303)
    
    # Persist username in session
    request.session["username"] = user["username"]
    # Persist tenant id from form if provided; else keep existing or set default
    if tenant_id and tenant_id.strip():
        request.session["tenant_id"] = tenant_id.strip()
    else:
        request.session.setdefault("tenant_id", DEFAULT_TENANT_ID)

    return RedirectResponse(url="/chat", status_code=303)

@app.get("/logout", include_in_schema=False)
def logout(request: Request):
    """Logout"""
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)

# Protected UI routes
@app.get("/chat", include_in_schema=False)
def chat_ui(request: Request, username: str = Depends(require_auth_session)):
    """Chat interface"""
    tenant_id = request.session.get("tenant_id", DEFAULT_TENANT_ID)
    return jinja_templates.TemplateResponse("chat.html", {
        "request": request,
        "username": username,
        "tenant_id": tenant_id
    })

@app.get("/dashboard", include_in_schema=False)
def dashboard(request: Request, username: str = Depends(require_auth_session)):
    """Dashboard"""
    return jinja_templates.TemplateResponse("dashboard.html", {
        "request": request,
        "username": username,
        "phone_id": PHONE_ID,
        "webhook": CALLBACK_URL,
        "verify_token": VERIFY_TOKEN,
        "buffer_size": MAX_BUFFER
    })

@app.get("/logs", include_in_schema=False)
def logs_ui(request: Request, username: str = Depends(require_auth_session)):
    """Webhook logs interface - requires authentication"""
    return jinja_templates.TemplateResponse("logs.html", {"request": request, "username": username})

# ────────────────────────────────────────────
# JWT Test Endpoint (for development)
# ────────────────────────────────────────────

@app.get(
    "/api/auth/verify",
    summary="Verify JWT Token",
    tags=["Authentication"],
    response_description="Token verification result"
)
async def verify_jwt(
    user: dict = Depends(get_current_user_flexible),
    tenant_id: str = Depends(get_tenant_id_flexible)
):
    """
    Verify JWT token and return decoded payload.
    
    Use this endpoint to test your JWT token authentication.
    """
    return {
        "valid": True,
        "user_id": user.get("user_id"),
        "tenant_id": tenant_id,
        "email": user.get("username"),
        "modules": user.get("modules", []),
        "token_payload": user
    }

# ────────────────────────────────────────────
# Exception Handlers
# ────────────────────────────────────────────

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    from fastapi.responses import JSONResponse
    
    if exc.status_code == 303 and exc.headers and exc.headers.get("Location"):
        return RedirectResponse(url=exc.headers["Location"], status_code=303)
    
    # For API calls, return JSON
    if request.url.path.startswith("/api/"):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail}
        )
    
    # For page requests, show error or redirect
    if exc.status_code == 401:
        return RedirectResponse(url="/login", status_code=303)
    
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


# ────────────────────────────────────────────
# WebSocket Endpoint (multi-tenant)
# ────────────────────────────────────────────
@app.websocket("/ws/{tenant_id}")
async def websocket_endpoint(websocket: WebSocket, tenant_id: str):
    """
    WebSocket endpoint for real-time message updates
    
    FIXES:
    - Added proper error handling
    - Added connection logging
    - Improved disconnect handling
    """
    try:
        await ws_manager.connect(tenant_id, websocket)
        log.info(f"✅ WebSocket connected for tenant: {tenant_id}")
        
        # Keep the connection alive and detect disconnects
        while True:
            try:
                # Receive text to keep connection alive
                data = await websocket.receive_text()
                log.debug(f"📨 WebSocket received data from {tenant_id}: {data}")
            except WebSocketDisconnect:
                log.info(f"🔌 WebSocket disconnected for tenant: {tenant_id}")
                break
            except Exception as e:
                log.error(f"❌ WebSocket error for tenant {tenant_id}: {e}")
                break
                
    except Exception as e:
        log.error(f"❌ WebSocket connection error for tenant {tenant_id}: {e}")
    finally:
        ws_manager.disconnect(tenant_id, websocket)
        log.info(f"🔌 WebSocket cleanup complete for tenant: {tenant_id}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)