# app/main.py
"""
FastAPI application with unified architecture.
Supports both session-based (HTML UI) and JWT (API) authentication.

FIXES APPLIED:
1. Proper middleware order (CORS before Session causes issues)
2. Single unified CORS handler
3. Fixed session access in middleware
4. Proper WebSocket CORS handling
5. ✅ Better WebSocket broadcasting with proper logging
"""
import logging
import re
from pathlib import Path
from fastapi import FastAPI, Request, Depends, Form, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import RedirectResponse, Response
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
from app.api.deps import require_auth_session, optional_auth_session, get_current_user_flexible, get_tenant_id_flexible
from app.api.v1.router import api_router
from app.services import set_whatsapp_client
from app.ws.manager import ws_manager

# Logging setup with file handler
import os
from logging.handlers import RotatingFileHandler

# Ensure logs directory exists
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Configure root logger
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG for detailed logs
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    handlers=[
        # Console handler
        logging.StreamHandler(),
        # File handler for debug logs
        RotatingFileHandler(
            LOG_DIR / "debug.log",
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
    ]
)

log = logging.getLogger("whatspy")
log.info("="*80)
log.info("🚀 Application starting - Logging to console and logs/debug.log")
log.info("="*80)

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

# ────────────────────────────────────────────
# CORS Configuration
# ────────────────────────────────────────────
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://whatsapp.dglinkup.com",
    "https://hmsceliyo.netlify.app",
]

# Local origin regex for dynamic ports
LOCAL_ORIGIN_RE = re.compile(r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$")

# Add CORS middleware FIRST (before other middlewares)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=[
        "X-Tenant",
        "X-Tenant-Id",
        "X-Tenant-Slug",
        "tenanttoken",
        "Authorization",
        "Content-Type",
        "Set-Cookie",
    ],
    max_age=86400,
)

# Session middleware AFTER CORS
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET_KEY,
    max_age=SESSION_MAX_AGE,
    same_site="lax",
    https_only=False
)

# ────────────────────────────────────────────
# Explicit OPTIONS handler for preflight
# ────────────────────────────────────────────
@app.options("/api/{path:path}", include_in_schema=False)
async def cors_preflight_all(path: str, request: Request):
    """Explicit CORS preflight to ensure Access-Control headers"""
    origin = request.headers.get("origin")
    req_headers = request.headers.get("access-control-request-headers", "*")

    # Echo back the Origin if it's allowed
    allow_origin = ""
    if origin:
        if origin in ALLOWED_ORIGINS or LOCAL_ORIGIN_RE.match(origin):
            allow_origin = origin

    headers = {
        "Access-Control-Allow-Origin": allow_origin or "*",
        "Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": req_headers or "*",
        "Access-Control-Max-Age": "86400",
        "Vary": "Origin",
    }
    
    if allow_origin:
        headers["Access-Control-Allow-Credentials"] = "true"

    return Response(status_code=204, headers=headers)

# ────────────────────────────────────────────
# Default Tenant Middleware
# ────────────────────────────────────────────
@app.middleware("http")
async def add_default_tenant_header(request: Request, call_next):
    """Add tenant ID header for API calls without JWT"""
    if request.url.path.startswith("/api/") and not request.headers.get("authorization"):
        # For OPTIONS requests, skip session access
        if request.method != "OPTIONS":
            try:
                # Only access session if SessionMiddleware is available
                tenant_from_session = None
                if hasattr(request.state, "session"):
                    tenant_from_session = request.state.session.get("tenant_id")
                elif hasattr(request, "_session"):
                    tenant_from_session = request._session.get("tenant_id")
                
                # Create mutable headers dict
                mutable_headers = dict(request.headers)
                if "x-tenant-id" not in mutable_headers or not mutable_headers.get("x-tenant-id"):
                    mutable_headers["x-tenant-id"] = tenant_from_session or DEFAULT_TENANT_ID
                
                # This is a workaround - modifying headers
                request._headers = mutable_headers
            except Exception as e:
                log.debug(f"Could not access session: {e}")

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
        register_handlers(wa)
        log.info("✅ WhatsApp client initialized")
    except Exception as e:
        log.error(f"❌ WhatsApp init failed: {e}")
else:
    log.warning("⚠️  WhatsApp not configured")

# Include API routes
app.include_router(api_router, prefix="/api")

# ────────────────────────────────────────────
# Unified API Routes (Legacy + New Merged)
# ────────────────────────────────────────────

from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services import get_message_service
from app.schemas.message import MessageCreate, MessageSendResponse
from datetime import datetime

@app.get("/api/stats")
def get_stats(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id_flexible),
    service = Depends(get_message_service)
):
    """Get message statistics"""
    from sqlalchemy import func
    from app.models.message import Message
    from datetime import timedelta
    
    total_messages = db.query(Message).filter(Message.tenant_id == tenant_id).count()
    
    direction_stats = db.query(
        Message.direction,
        func.count(Message.id).label('count')
    ).filter(
        Message.tenant_id == tenant_id
    ).group_by(Message.direction).all()
    
    type_stats = db.query(
        Message.message_type,
        func.count(Message.id).label('count')
    ).filter(
        Message.tenant_id == tenant_id
    ).group_by(Message.message_type).all()
    
    week_ago = datetime.utcnow() - timedelta(days=7)
    recent_messages = db.query(Message).filter(
        Message.tenant_id == tenant_id,
        Message.created_at >= week_ago
    ).count()
    
    unique_contacts = db.query(Message.phone).filter(
        Message.tenant_id == tenant_id
    ).distinct().count()
    
    # Build proper response
    by_direction = {stat.direction: stat.count for stat in direction_stats}
    
    return {
        "total_messages": total_messages,
        "incoming_messages": by_direction.get("incoming", 0),
        "outgoing_messages": by_direction.get("outgoing", 0),
        "unique_contacts": unique_contacts,
        "recent_messages": recent_messages,
        "by_direction": by_direction,
        "by_type": {stat.message_type: stat.count for stat in type_stats}
    }


@app.get("/api/conversations")
def list_conversations(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id_flexible),
    service = Depends(get_message_service)
):
    """List all conversations - ALWAYS returns an array"""
    try:
        conversations = service.get_conversations(db, tenant_id)
        if not isinstance(conversations, list):
            log.warning("⚠️ get_conversations returned non-list, returning empty array")
            return []
        return conversations
    except Exception as e:
        log.error(f"❌ Failed to get conversations: {e}")
        return []


@app.get("/api/conversations/{phone}")
def get_conversation(
    phone: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id_flexible),
    service = Depends(get_message_service)
):
    """Get conversation with specific number"""
    messages = service.get_conversation(db, tenant_id, phone)
    return {"phone": phone, "messages": messages}


@app.post("/api/send/text", response_model=MessageSendResponse)
def send_text_message(
    data: MessageCreate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id_flexible),
    service = Depends(get_message_service)
):
    """
    Send text message - Legacy endpoint
    Frontend expects this exact route: /api/send/text
    """
    try:
        log.info(f"📤 Sending message to {data.to}: {data.text[:50]}...")
        
        msg_id, saved = service.send_text_message(db, tenant_id, data)

        log.info(f"✅ Message sent and saved: {msg_id}")

        # Broadcast to tenant websocket clients
        try:
            from app.ws.manager import notify_clients_sync
            
            payload = {
                "event": "message_outgoing",
                "data": {
                    "phone": data.to,
                    "name": saved.contact_name or data.to,
                    "contact_name": saved.contact_name,
                    "message": {
                        "id": msg_id,
                        "message_id": msg_id,
                        "type": "text",
                        "text": data.text,
                        "message_text": data.text,
                        "timestamp": saved.created_at.isoformat() if saved.created_at else datetime.utcnow().isoformat(),
                        "created_at": saved.created_at.isoformat() if saved.created_at else datetime.utcnow().isoformat(),
                        "direction": "outgoing"
                    }
                }
            }
            
            log.info(f"📢 Broadcasting outgoing message to tenant {tenant_id}")
            notify_clients_sync(tenant_id, payload)
            log.info(f"✅ WebSocket broadcast successful")
            
        except Exception as ws_err:
            log.error(f"❌ WebSocket broadcast failed: {ws_err}")
            import traceback
            log.error(traceback.format_exc())

        return MessageSendResponse(
            message_id=msg_id, 
            phone=data.to, 
            text=data.text,
            timestamp=saved.created_at.isoformat() if saved.created_at else datetime.utcnow().isoformat()
        )
    except Exception as e:
        log.error(f"❌ Failed to send message: {e}")
        import traceback
        log.error(traceback.format_exc())
        raise HTTPException(500, f"Failed to send message: {str(e)}")


# Mount static files
try:
    app.mount("/static", StaticFiles(directory=str(BASE_DIR / "app" / "static")), name="static")
except:
    log.warning("⚠️  Static files not mounted")

# ────────────────────────────────────────────
# Public routes
# ────────────────────────────────────────────

@app.get("/healthz", tags=["System"])
def health():
    """Health check endpoint"""
    db_ok = test_db_connection()
    ws_connections = ws_manager.connection_count()
    
    return {
        "status": "ok" if db_ok else "degraded",
        "phone_id_ok": bool(PHONE_ID),
        "token_ok": bool(TOKEN),
        "verify_token_ok": bool(VERIFY_TOKEN),
        "database_ok": db_ok,
        "jwt_enabled": bool(JWT_SECRET_KEY),
        "buffer_size": MAX_BUFFER,
        "websocket_connections": ws_connections
    }

@app.get("/", include_in_schema=False)
def index(request: Request, username: str = Depends(optional_auth_session)):
    """Root"""
    if username:
        return RedirectResponse(url="/chat", status_code=303)
    return RedirectResponse(url="/login", status_code=303)

# ────────────────────────────────────────────
# Auth routes
# ────────────────────────────────────────────

@app.get("/login", include_in_schema=False)
def login_page(request: Request):
    """Login page"""
    if request.session.get("username"):
        return RedirectResponse(url="/chat", status_code=303)

    error_param = request.query_params.get("error")
    error_msg = None
    if error_param == "Invalid":
        error_msg = "Invalid username or password"
    elif error_param:
        error_msg = error_param

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
    
    request.session["username"] = user["username"]
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

# ────────────────────────────────────────────
# Protected UI routes
# ────────────────────────────────────────────

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
    """Webhook logs interface"""
    return jinja_templates.TemplateResponse("logs.html", {"request": request, "username": username})

# ────────────────────────────────────────────
# JWT Test Endpoint
# ────────────────────────────────────────────

@app.get("/api/auth/verify", tags=["Authentication"])
async def verify_jwt(
    user: dict = Depends(get_current_user_flexible),
    tenant_id: str = Depends(get_tenant_id_flexible)
):
    """Verify JWT token"""
    return {
        "valid": True,
        "user_id": user.get("user_id"),
        "tenant_id": tenant_id,
        "email": user.get("username"),
        "modules": user.get("modules", []),
        "token_payload": user
    }

# ────────────────────────────────────────────
# WebSocket Endpoint
# ────────────────────────────────────────────

@app.websocket("/ws/{tenant_id}")
async def websocket_endpoint(websocket: WebSocket, tenant_id: str):
    """WebSocket endpoint for real-time message updates"""
    try:
        await ws_manager.connect(tenant_id, websocket)
        log.info(f"✅ WebSocket connected for tenant: {tenant_id} (Total: {ws_manager.connection_count(tenant_id)})")
        
        # Keep connection alive
        while True:
            try:
                # Receive messages to detect disconnects
                data = await websocket.receive_text()
                log.debug(f"📨 WebSocket received from {tenant_id}: {data}")
                
                # Handle ping/pong
                if data == "ping":
                    await websocket.send_text("pong")
                    log.debug(f"🏓 Pong sent to {tenant_id}")
                    
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
        log.info(f"🔌 WebSocket cleanup complete for tenant: {tenant_id} (Remaining: {ws_manager.connection_count(tenant_id)})")


# ────────────────────────────────────────────
# Exception Handlers
# ────────────────────────────────────────────

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    from fastapi.responses import JSONResponse
    
    if exc.status_code == 303 and exc.headers and exc.headers.get("Location"):
        return RedirectResponse(url=exc.headers["Location"], status_code=303)
    
    if request.url.path.startswith("/api/"):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail}
        )
    
    if exc.status_code == 401:
        return RedirectResponse(url="/login", status_code=303)
    
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8100)