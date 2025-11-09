"""add whatsapp templates

Revision ID: add_templates_001
Revises: 
Create Date: 2025-11-09

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_templates_001'
down_revision = None  # Set this to your latest migration ID
branch_labels = None
depends_on = None


def upgrade():
    # Create whatsapp_templates table
    op.create_table(
        'whatsapp_templates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        
        # Template identification
        sa.Column('template_id', sa.String(length=255), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('language', sa.String(length=10), nullable=False),
        
        # Template details
        sa.Column('category', sa.Enum('MARKETING', 'UTILITY', 'AUTHENTICATION', name='templatecategory'), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'APPROVED', 'REJECTED', 'PAUSED', 'DISABLED', name='templatestatus'), nullable=False),
        
        # Template structure
        sa.Column('components', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        
        # Metadata
        sa.Column('quality_score', sa.String(length=20), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        
        # Usage tracking
        sa.Column('usage_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('last_used_at', sa.String(), nullable=True),
        
        # Library template
        sa.Column('library_template_name', sa.String(length=255), nullable=True),
        
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('ix_whatsapp_templates_tenant_id', 'whatsapp_templates', ['tenant_id'])
    op.create_index('ix_whatsapp_templates_template_id', 'whatsapp_templates', ['template_id'])
    op.create_index('ix_whatsapp_templates_name', 'whatsapp_templates', ['name'])
    op.create_index('ix_whatsapp_templates_status', 'whatsapp_templates', ['status'])
    
    # Create template_send_logs table
    op.create_table(
        'template_send_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        
        # Template reference
        sa.Column('template_id', sa.Integer(), nullable=False),
        sa.Column('template_name', sa.String(length=255), nullable=False),
        
        # Recipient
        sa.Column('recipient_phone', sa.String(length=50), nullable=False),
        sa.Column('message_id', sa.String(length=255), nullable=True),
        
        # Parameters
        sa.Column('parameters', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        
        # Status
        sa.Column('send_status', sa.String(length=50), nullable=True, server_default='sent'),
        sa.Column('error_message', sa.Text(), nullable=True),
        
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for send logs
    op.create_index('ix_template_send_logs_tenant_id', 'template_send_logs', ['tenant_id'])
    op.create_index('ix_template_send_logs_template_id', 'template_send_logs', ['template_id'])
    op.create_index('ix_template_send_logs_template_name', 'template_send_logs', ['template_name'])
    op.create_index('ix_template_send_logs_recipient_phone', 'template_send_logs', ['recipient_phone'])


def downgrade():
    # Drop tables
    op.drop_index('ix_template_send_logs_recipient_phone', table_name='template_send_logs')
    op.drop_index('ix_template_send_logs_template_name', table_name='template_send_logs')
    op.drop_index('ix_template_send_logs_template_id', table_name='template_send_logs')
    op.drop_index('ix_template_send_logs_tenant_id', table_name='template_send_logs')
    op.drop_table('template_send_logs')
    
    op.drop_index('ix_whatsapp_templates_status', table_name='whatsapp_templates')
    op.drop_index('ix_whatsapp_templates_name', table_name='whatsapp_templates')
    op.drop_index('ix_whatsapp_templates_template_id', table_name='whatsapp_templates')
    op.drop_index('ix_whatsapp_templates_tenant_id', table_name='whatsapp_templates')
    op.drop_table('whatsapp_templates')
    
    # Drop enums
    op.execute('DROP TYPE templatestatus')
    op.execute('DROP TYPE templatecategory')