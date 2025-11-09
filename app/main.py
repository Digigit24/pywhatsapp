# app/main.py
"""
FastAPI application with new architecture.
Supports both session-based (HTML UI) and JWT (API) authentication.
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
    MAX_BUFFER, VALIDATE_UPDATES
)
from app.db.session import init_db, test_db_connection
from app.core.security import authenticate_user
from app.api.deps import require_auth_session, optional_auth_session, require_auth_flexible, get_current_user_flexible, get_tenant_id_flexible
from app.api.v1.router import api_router
from app.services import set_whatsapp_client

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
    Development middleware to add default tenant ID header.
    This helps with testing when no JWT token is provided.
    """
    # Only add default tenant for API routes if no auth header present
    if request.url.path.startswith("/api/") and not request.headers.get("authorization"):
        # Create a mutable copy of headers
        mutable_headers = dict(request.headers)
        # Add default tenant ID for development
        if "x-tenant-id" not in mutable_headers:
            mutable_headers["x-tenant-id"] = "bc531d42-ac91-41df-817e-26c339af6b3a"
        
        # Create new request with updated headers
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
    return jinja_templates.TemplateResponse("login.html", {"request": request, "error": None})

@app.post("/login", include_in_schema=False)
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    """Login"""
    user = authenticate_user(username, password)
    if not user:
        return RedirectResponse(url="/login?error=Invalid", status_code=303)
    
    request.session["username"] = user["username"]
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
    return jinja_templates.TemplateResponse("chat.html", {"request": request, "username": username})

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)