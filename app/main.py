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
from app.api.deps import require_auth_session, optional_auth_session, require_auth_flexible
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

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session middleware
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET_KEY,
    max_age=SESSION_MAX_AGE,
    same_site="lax",
    https_only=False
)

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

# Include API routes
app.include_router(
    api_router,
    prefix="/api/v1",
    dependencies=[Depends(require_auth_flexible)]
)

# Mount static files
try:
    app.mount("/static", StaticFiles(directory=str(BASE_DIR / "templates")), name="static")
except:
    log.warning("⚠️  Static files not mounted")

# Public routes
@app.get("/healthz")
def health():
    """Health check"""
    return {
        "status": "ok",
        "database": test_db_connection(),
        "whatsapp": bool(wa),
        "jwt_enabled": bool(JWT_SECRET_KEY)
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)