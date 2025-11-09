#!/usr/bin/env python3
# scripts/setup_database.py
"""
Complete database setup script
- Creates all tables via Alembic migration
- Creates admin user
- Verifies database connection
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import test_db_connection, get_db_session
from app.core.security import create_admin_user, hash_password
from app.core.config import ADMIN_USERNAME, ADMIN_PASSWORD, DATABASE_URL
from app.models.user import AdminUser

def setup():
    print("=" * 70)
    print("🚀 WHATSPY DATABASE SETUP")
    print("=" * 70)
    
    # Step 1: Test connection
    print("\n1️⃣  Testing database connection...")
    print(f"   Database: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'hidden'}")
    
    if not test_db_connection():
        print("   ❌ Database connection failed!")
        print("   Please check:")
        print("   - PostgreSQL is running")
        print("   - Database exists")
        print("   - .env configuration is correct")
        return 1
    print("   ✅ Database connected successfully")
    
    # Step 2: Run migrations
    print("\n2️⃣  Running database migrations...")
    print("   Execute: alembic upgrade head")
    import os
    result = os.system("alembic upgrade head")
    if result != 0:
        print("   ❌ Migration failed!")
        print("   Try manually: alembic upgrade head")
        return 1
    print("   ✅ All migrations applied")
    
    # Step 3: Create admin user
    print(f"\n3️⃣  Creating admin user '{ADMIN_USERNAME}'...")
    try:
        with get_db_session() as db:
            existing = db.query(AdminUser).filter(
                AdminUser.username == ADMIN_USERNAME
            ).first()
            
            if existing:
                print(f"   ⚠️  User '{ADMIN_USERNAME}' exists. Updating password...")
                existing.password_hash = hash_password(ADMIN_PASSWORD)
                existing.is_active = True
                db.commit()
                print(f"   ✅ Password updated")
            else:
                user = create_admin_user(ADMIN_USERNAME, ADMIN_PASSWORD, db)
                if user:
                    print(f"   ✅ Admin user created")
                else:
                    print(f"   ❌ Failed to create user")
                    return 1
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return 1
    
    # Step 4: Verify tables
    print("\n4️⃣  Verifying database tables...")
    try:
        from sqlalchemy import inspect
        from app.db.session import engine
        
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        expected_tables = [
            'admin_users',
            'messages',
            'message_templates',
            'contacts',
            'groups',
            'campaigns',
            'webhook_logs',
            'message_reactions',
            'alembic_version'
        ]
        
        missing = [t for t in expected_tables if t not in tables]
        
        if missing:
            print(f"   ⚠️  Missing tables: {', '.join(missing)}")
        else:
            print(f"   ✅ All {len(expected_tables)} tables created")
            for table in expected_tables:
                print(f"      ✓ {table}")
    except Exception as e:
        print(f"   ⚠️  Could not verify tables: {e}")
    
    # Success!
    print("\n" + "=" * 70)
    print("✅ DATABASE SETUP COMPLETE!")
    print("=" * 70)
    print(f"\n📌 Admin Credentials:")
    print(f"   Username: {ADMIN_USERNAME}")
    print(f"   Password: {ADMIN_PASSWORD}")
    print(f"   🔒 CHANGE PASSWORD AFTER FIRST LOGIN!")
    
    print("\n🚀 Start Application:")
    print("   python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8002")
    print("   Visit: http://localhost:8002/docs")
    print("\n" + "=" * 70)
    
    return 0

if __name__ == "__main__":
    sys.exit(setup())