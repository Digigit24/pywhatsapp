# scripts/create_admin.py
"""
Create admin user for HTML UI access.
Run this script once to create the initial admin account.
"""
import sys
from pathlib import Path

# Ensure UTF-8 capable stdout/stderr on Windows terminals
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import get_db_session, test_db_connection, init_db
from app.core.security import create_admin_user, hash_password
from app.core.config import ADMIN_USERNAME, ADMIN_PASSWORD
from app.models.user import AdminUser

print("=" * 60)
print("Creating Admin User")
print("=" * 60)

# Test database connection
print("\n1) Testing database connection...")
if not test_db_connection():
    print("[ERROR] Database connection failed!")
    print("   Please check:")
    print("   - PostgreSQL is running")
    print("   - Database exists")
    print("   - .env configuration is correct")
    sys.exit(1)
print("[OK] Database connected")

# Initialize database tables
print("\n2) Initializing database tables...")
try:
    init_db()
    print("[OK] Tables initialized")
except Exception as e:
    print(f"[ERROR] Failed to initialize tables: {e}")
    sys.exit(1)

# Create admin user
print(f"\n3) Creating admin user '{ADMIN_USERNAME}'...")
try:
    with get_db_session() as db:
        # Check if user exists
        existing = db.query(AdminUser).filter(AdminUser.username == ADMIN_USERNAME).first()

        if existing:
            print(f"[WARN] User '{ADMIN_USERNAME}' already exists. Updating password...")
            existing.password_hash = hash_password(ADMIN_PASSWORD)
            db.commit()
            print(f"[OK] Password updated for '{ADMIN_USERNAME}'")
        else:
            user = create_admin_user(ADMIN_USERNAME, ADMIN_PASSWORD, db)
            if user:
                print(f"[OK] Admin user '{ADMIN_USERNAME}' created successfully")
            else:
                print("[ERROR] Failed to create user")
                sys.exit(1)

except Exception as e:
    print(f"[ERROR] Error: {e}")
    sys.exit(1)

# Success!
print("\n" + "=" * 60)
print("ADMIN USER READY!")
print("=" * 60)
print("\nLogin Credentials:")
print(f"   Username: {ADMIN_USERNAME}")
print(f"   Password: {ADMIN_PASSWORD}")
print("   Tenant ID: default")
print("\nIMPORTANT: Change password after first login!")
print("\nStart the application with:")
print("   python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8002")
print()