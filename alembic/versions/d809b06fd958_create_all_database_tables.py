"""Create all database tables

Revision ID: d809b06fd958
Revises: 
Create Date: 2026-09-02 19:12:03.870005

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'd809b06fd958'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # ### Create tables ###
    
    # Organizations table
    op.create_table('organizations',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_organizations_id', 'organizations', ['id'], unique=False)
    
    # Skills table
    op.create_table('skills',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('organization_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(), nullable=False, server_default='draft'),
        sa.Column('owner_id', sa.String(), nullable=False),
        sa.Column('current_version_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_skills_organization_id', 'skills', ['organization_id'], unique=False)
    op.create_index('ix_skills_id', 'skills', ['id'], unique=False)
    
    # Skill Versions table
    op.create_table('skill_versions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('skill_id', sa.UUID(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('configuration', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('requested_tools', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('created_by', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('activated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('activated_by', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['skill_id'], ['skills.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_skill_versions_skill_id', 'skill_versions', ['skill_id'], unique=False)
    
    # Audit Logs table
    op.create_table('audit_logs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('organization_id', sa.String(), nullable=False),
        sa.Column('skill_id', sa.UUID(), nullable=True),
        sa.Column('version_id', sa.UUID(), nullable=True),
        sa.Column('event_type', sa.Enum('SKILL_CREATED', 'SKILL_UPDATED', 'SKILL_ACTIVATED', 'SKILL_DISABLED', 'VERSION_CREATED', 'VERSION_ACTIVATED', name='auditeventtype'), nullable=False),
        sa.Column('actor', sa.String(), nullable=False),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('occurred_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['skill_id'], ['skills.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['version_id'], ['skill_versions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_audit_logs_organization_id', 'audit_logs', ['organization_id'], unique=False)
    op.create_index('ix_audit_logs_skill_id', 'audit_logs', ['skill_id'], unique=False)
    op.create_index('ix_audit_logs_occurred_at', 'audit_logs', ['occurred_at'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### Drop tables ###
    op.drop_index('ix_audit_logs_occurred_at', table_name='audit_logs')
    op.drop_index('ix_audit_logs_skill_id', table_name='audit_logs')
    op.drop_index('ix_audit_logs_organization_id', table_name='audit_logs')
    op.drop_table('audit_logs')
    
    op.drop_index('ix_skill_versions_skill_id', table_name='skill_versions')
    op.drop_table('skill_versions')
    
    op.drop_index('ix_skills_organization_id', table_name='skills')
    op.drop_index('ix_skills_id', table_name='skills')
    op.drop_table('skills')
    
    op.drop_index('ix_organizations_id', table_name='organizations')
    op.drop_table('organizations')
    
    # ### Drop ENUM type ###
    op.execute("DROP TYPE IF EXISTS auditeventtype")
    # ### end Alembic commands ###