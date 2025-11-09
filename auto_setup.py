# auto_setup.py
"""
Complete Whatspy Setup Script for Windows
- Drops and recreates all tables (FRESH START)
- Creates admin user
- Tests connections
Run once on fresh installation
"""
import os
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

print("=" * 70)
print("🚀 WHATSPY COMPLETE AUTO-SETUP (Windows)")
print("=" * 70)
print()

# Import after printing header
try:
    from app.db.session import get_db_session, test_db_connection, engine
    from app.db.base import Base
    from app.core.security import create_admin_user, hash_password
    from app.core.config import ADMIN_USERNAME, ADMIN_PASSWORD, DATABASE_URL
    from app.models.user import AdminUser
except Exception as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're in the correct directory and .env is configured")
    sys.exit(1)

# Show configuration
print(f"📋 Configuration:")
print(f"   Database: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'hidden'}")
print(f"   Admin User: {ADMIN_USERNAME}")
print()

# Step 1: Test database connection
print("1️⃣  Testing database connection...")
if not test_db_connection():
    print("   ❌ Database connection failed!")
    print("   Please check:")
    print("   - PostgreSQL is running")
    print("   - Database exists (CREATE DATABASE whatspy_db;)")
    print("   - DATABASE_URL in .env is correct")
    sys.exit(1)
print("   ✅ Database connected successfully")

# Step 2: Drop and recreate all tables (FRESH START)
print("\n2️⃣  Recreating all database tables (FRESH START)...")
print("   ⚠️  This will DROP all existing tables!")

try:
    # Drop all tables
    print("   Dropping existing tables...")
    Base.metadata.drop_all(bind=engine)
    print("   ✓ Old tables dropped")
    
    # Create all tables fresh
    print("   Creating fresh tables...")
    Base.metadata.create_all(bind=engine)
    print("   ✓ New tables created")
    
    # Verify tables
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    print(f"\n   ✅ Created {len(tables)} tables:")
    expected_tables = [
        'admin_users',
        'messages', 
        'message_templates',
        'contacts',
        'groups',
        'campaigns',
        'webhook_logs',
        'message_reactions'
    ]
    
    for table in expected_tables:
        if table in tables:
            print(f"      ✓ {table}")
        else:
            print(f"      ✗ {table} (MISSING!)")
    
    # Check for unexpected tables
    extra = [t for t in tables if t not in expected_tables]
    if extra:
        print(f"\n   Additional tables: {', '.join(extra)}")
        
except Exception as e:
    print(f"   ❌ Table creation failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Step 3: Create admin user
print(f"\n3️⃣  Creating admin user '{ADMIN_USERNAME}'...")
try:
    with get_db_session() as db:
        # Check if user already exists
        existing = db.query(AdminUser).filter(
            AdminUser.username == ADMIN_USERNAME
        ).first()
        
        if existing:
            print(f"   ⚠️  User '{ADMIN_USERNAME}' already exists. Updating password...")
            existing.password_hash = hash_password(ADMIN_PASSWORD)
            existing.is_active = True
            db.commit()
            print(f"   ✅ Password updated for '{ADMIN_USERNAME}'")
        else:
            user = create_admin_user(ADMIN_USERNAME, ADMIN_PASSWORD, db)
            if user:
                print(f"   ✅ Admin user '{ADMIN_USERNAME}' created successfully")
            else:
                print(f"   ❌ Failed to create admin user")
                sys.exit(1)
                
except Exception as e:
    print(f"   ❌ Admin user creation failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Step 4: Verify everything works
print("\n4️⃣  Verifying setup...")
try:
    with get_db_session() as db:
        # Count admin users
        admin_count = db.query(AdminUser).count()
        print(f"   ✓ Admin users in database: {admin_count}")
        
        # Test each table
        from app.models.message import Message, MessageTemplate
        from app.models.webhook import WebhookLog, MessageReaction
        from app.models.contact import Contact
        from app.models.group import Group
        from app.models.campaign import Campaign
        
        tables_to_test = [
            (AdminUser, 'admin_users'),
            (Message, 'messages'),
            (MessageTemplate, 'message_templates'),
            (Contact, 'contacts'),
            (Group, 'groups'),
            (Campaign, 'campaigns'),
            (WebhookLog, 'webhook_logs'),
            (MessageReaction, 'message_reactions')
        ]
        
        print("   Testing all tables...")
        for model, name in tables_to_test:
            try:
                count = db.query(model).count()
                print(f"      ✓ {name}: {count} rows")
            except Exception as e:
                print(f"      ✗ {name}: ERROR - {e}")
        
    print("   ✅ All tables verified and working")
    
except Exception as e:
    print(f"   ⚠️  Verification warning: {e}")

# Success!
print("\n" + "=" * 70)
print("✅ SETUP COMPLETED SUCCESSFULLY!")
print("=" * 70)

print(f"\n📌 Admin Login Credentials:")
print(f"   Username: {ADMIN_USERNAME}")
print(f"   Password: {ADMIN_PASSWORD}")
print(f"   Tenant ID: default")
print(f"\n   🔒 IMPORTANT: Change password after first login!")

print("\n🚀 Start the Application:")
print("   python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8002")

print("\n📚 Access Points:")
print("   Login:         http://localhost:8002/login")
print("   Chat UI:       http://localhost:8002/chat")
print("   Dashboard:     http://localhost:8002/dashboard")
print("   Swagger Docs:  http://localhost:8002/docs")
print("   Health Check:  http://localhost:8002/healthz")

print("\n" + "=" * 70)
print("✅ Ready to use!")
print("=" * 70)

#dlets do it


