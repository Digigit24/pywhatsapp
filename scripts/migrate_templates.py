# scripts/migrate_templates.py
"""
Quick migration script for WhatsApp Templates.
Run this to add template tables to your existing database.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import engine, test_db_connection
from sqlalchemy import text

print("=" * 70)
print("🚀 WHATSAPP TEMPLATES MIGRATION")
print("=" * 70)

# Test connection
print("\n1️⃣  Testing database connection...")
if not test_db_connection():
    print("   ❌ Database connection failed!")
    sys.exit(1)
print("   ✅ Database connected")

# Create tables
print("\n2️⃣  Creating template tables...")

try:
    with engine.connect() as conn:
        # Create enums
        print("   Creating enum types...")
        conn.execute(text("""
            DO $$ BEGIN
                CREATE TYPE templatecategory AS ENUM ('MARKETING', 'UTILITY', 'AUTHENTICATION');
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
        """))
        
        conn.execute(text("""
            DO $$ BEGIN
                CREATE TYPE templatestatus AS ENUM ('PENDING', 'APPROVED', 'REJECTED', 'PAUSED', 'DISABLED');
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
        """))
        
        # Create whatsapp_templates table
        print("   Creating whatsapp_templates table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS whatsapp_templates (
                id SERIAL PRIMARY KEY,
                tenant_id VARCHAR(100) NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
                
                -- Template identification
                template_id VARCHAR(255),
                name VARCHAR(255) NOT NULL,
                language VARCHAR(10) NOT NULL,
                
                -- Template details
                category templatecategory NOT NULL,
                status templatestatus NOT NULL DEFAULT 'PENDING',
                
                -- Template structure
                components JSONB NOT NULL,
                
                -- Metadata
                quality_score VARCHAR(20),
                rejection_reason TEXT,
                
                -- Usage tracking
                usage_count INTEGER DEFAULT 0,
                last_used_at VARCHAR(255),
                
                -- Library template
                library_template_name VARCHAR(255)
            );
        """))
        
        # Create indexes
        print("   Creating indexes for whatsapp_templates...")
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_whatsapp_templates_tenant_id ON whatsapp_templates(tenant_id);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_whatsapp_templates_template_id ON whatsapp_templates(template_id);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_whatsapp_templates_name ON whatsapp_templates(name);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_whatsapp_templates_status ON whatsapp_templates(status);"))
        
        # Create template_send_logs table
        print("   Creating template_send_logs table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS template_send_logs (
                id SERIAL PRIMARY KEY,
                tenant_id VARCHAR(100) NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
                
                template_id INTEGER NOT NULL,
                template_name VARCHAR(255) NOT NULL,
                recipient_phone VARCHAR(50) NOT NULL,
                message_id VARCHAR(255),
                
                parameters JSONB,
                
                send_status VARCHAR(50) DEFAULT 'sent',
                error_message TEXT
            );
        """))
        
        # Create indexes
        print("   Creating indexes for template_send_logs...")
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_template_send_logs_tenant_id ON template_send_logs(tenant_id);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_template_send_logs_template_id ON template_send_logs(template_id);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_template_send_logs_template_name ON template_send_logs(template_name);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_template_send_logs_recipient_phone ON template_send_logs(recipient_phone);"))
        
        conn.commit()
        
    print("   ✅ Tables created successfully")
    
except Exception as e:
    print(f"   ❌ Migration failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Verify tables
print("\n3️⃣  Verifying tables...")
try:
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    required_tables = ['whatsapp_templates', 'template_send_logs']
    
    for table in required_tables:
        if table in tables:
            # Get column count
            columns = inspector.get_columns(table)
            print(f"   ✓ {table} ({len(columns)} columns)")
        else:
            print(f"   ✗ {table} (MISSING!)")
            
except Exception as e:
    print(f"   ⚠️  Verification failed: {e}")

# Success!
print("\n" + "=" * 70)
print("✅ MIGRATION COMPLETED!")
print("=" * 70)

print("\n📝 Next Steps:")
print("   1. Restart your application")
print("   2. Check API docs: http://localhost:8002/docs")
print("   3. Create your first template!")
print("\n📚 See TEMPLATES_SETUP_GUIDE.md for usage examples")
print()