# scripts/create_admin.py
"""
Create admin user for HTML UI access.
Run this script once to create the initial admin account.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import get_db_session, test_db_connection, init_db
from app.core.security import create_admin_user, hash_password
from app.core.config import ADMIN_USERNAME, ADMIN_PASSWORD
from app.models.user import AdminUser

print("=" * 60)
print("🔐 Creating Admin User")
print("=" * 60)

# Test database connection
print("\n1️⃣  Testing database connection...")
if not test_db_connection():
    print("❌ Database connection failed!")
    print("   Please check:")
    print("   - PostgreSQL is running")
    print("   - Database exists")
    print("   - .env configuration is correct")
    sys.exit(1)
print("✅ Database connected")

# Initialize database tables
print("\n2️⃣  Initializing database tables...")
try:
    init_db()
    print("✅ Tables initialized")
except Exception as e:
    print(f"❌ Failed to initialize tables: {e}")
    sys.exit(1)

# Create admin user
print(f"\n3️⃣  Creating admin user '{ADMIN_USERNAME}'...")
try:
    with get_db_session() as db:
        # Check if user exists
        existing = db.query(AdminUser).filter(AdminUser.username == ADMIN_USERNAME).first()
        
        if existing:
            print(f"⚠️  User '{ADMIN_USERNAME}' already exists. Updating password...")
            existing.password_hash = hash_password(ADMIN_PASSWORD)
            db.commit()
            print(f"✅ Password updated for '{ADMIN_USERNAME}'")
        else:
            user = create_admin_user(ADMIN_USERNAME, ADMIN_PASSWORD, db)
            if user:
                print(f"✅ Admin user '{ADMIN_USERNAME}' created successfully")
            else:
                print(f"❌ Failed to create user")
                sys.exit(1)
        
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)

# Success!
print("\n" + "=" * 60)
print("✅ ADMIN USER READY!")
print("=" * 60)
print(f"\n📌 Login Credentials:")
print(f"   Username: {ADMIN_USERNAME}")
print(f"   Password: {ADMIN_PASSWORD}")
print(f"   Tenant ID: default")
print(f"\n🔒 IMPORTANT: Change password after first login!")
print("\n🚀 Start the application with:")
print("   python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8002")
print()