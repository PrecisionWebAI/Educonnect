"""Add permission and role_permission tables

Revision ID: a1b2c3d4e5f6
Revises: e08a27be1a21
Create Date: 2026-09-08 17:56:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'e08a27be1a21'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add permission catalog and role_permission join tables."""
    op.create_table(
        'permission',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('codename', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('category', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default='General'),
        sa.Column('label', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default=''),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('codename'),
    )
    op.create_index('ix_permission_codename', 'permission', ['codename'], unique=True)

    op.create_table(
        'rolepermission',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('role', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('permission_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['permission_id'], ['permission.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_rolepermission_role', 'rolepermission', ['role'], unique=False)
    op.create_index('ix_rolepermission_permission_id', 'rolepermission', ['permission_id'], unique=False)


def downgrade() -> None:
    """Drop permission and role_permission tables."""
    op.drop_index('ix_rolepermission_permission_id', table_name='rolepermission')
    op.drop_index('ix_rolepermission_role', table_name='rolepermission')
    op.drop_table('rolepermission')
    op.drop_index('ix_permission_codename', table_name='permission')
    op.drop_table('permission')
