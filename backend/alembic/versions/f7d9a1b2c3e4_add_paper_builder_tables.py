"""Add Paper Builder tables (PaperDraft, GenerationJob, ExamSource)

Revision ID: f7d9a1b2c3e4
Revises: b2c3d4e5f6a7
Create Date: 2026-09-17

Yeh migration sirf NAYI tables banata hai (exam paper builder domain —
blueprint §2.3). Purane examterm/exampaper/examresult tables NAHI chhedta
(woh unke apne migrations ki history mein hain — data migration kabhi
delete nahi karte).

Naye tables:
  paperdraft     — AI paper draft (blueprint + coverage + part_a + part_b)
  generationjob  — async generation ka record (polling + checkpoint)
  examsource     — content library row (Phase 3 RAG base)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'f7d9a1b2c3e4'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ---- enums pehle create (Postgres native enum types) ----
    # create_type=False isliye: enums explicit `enum.create()` se ban rahe hain,
    # aur op.create_table ke andar SQLAlchemy phir se CREATE TYPE nahi karega
    # (warna "type already exists" — classic postgres enum gotcha).
    paperstatus_enum = postgresql.ENUM('draft', 'in_review', 'approved', name='paperstatus', create_type=False)
    coveragemode_enum = postgresql.ENUM('auto', 'marks', 'percent', name='coveragemode', create_type=False)
    jobstatus_enum = postgresql.ENUM('queued', 'running', 'done', 'failed', 'canceled', name='generationjobstatus', create_type=False)
    sourcetype_enum = postgresql.ENUM('pdf', 'image', 'url', 'text', 'bank', name='sourcetype', create_type=False)
    for enum in (paperstatus_enum, coveragemode_enum, jobstatus_enum, sourcetype_enum):
        enum.create(op.get_bind(), checkfirst=True)

    # ---- PaperDraft ----
    op.create_table('paperdraft',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('grade_class_id', sa.Integer(), nullable=True),
        sa.Column('subject_id', sa.Integer(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('total_marks', sa.Integer(), nullable=False),
        sa.Column('duration_minutes', sa.Integer(), nullable=False),
        sa.Column('blueprint', sa.JSON(), nullable=False),
        sa.Column('coverage_mode', coveragemode_enum, nullable=False),
        sa.Column('coverage_plan', sa.JSON(), nullable=False),
        sa.Column('part_a', sa.JSON(), nullable=False),
        sa.Column('part_b', sa.JSON(), nullable=False),
        sa.Column('status', paperstatus_enum, nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['grade_class_id'], ['gradeclass.id'], ),
        sa.ForeignKeyConstraint(['subject_id'], ['subject.id'], ),
        sa.ForeignKeyConstraint(['created_by'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_paperdraft_grade_class_id', 'paperdraft', ['grade_class_id'])
    op.create_index('ix_paperdraft_subject_id', 'paperdraft', ['subject_id'])

    # ---- GenerationJob ----
    op.create_table('generationjob',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('paper_id', sa.Integer(), nullable=False),
        sa.Column('status', jobstatus_enum, nullable=False),
        sa.Column('graph_state', sa.JSON(), nullable=False),
        sa.Column('stages', sa.JSON(), nullable=False),
        sa.Column('blueprint_snapshot', sa.JSON(), nullable=False),
        sa.Column('coverage_snapshot', sa.JSON(), nullable=False),
        sa.Column('model_info', sa.JSON(), nullable=False),
        sa.Column('error', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('trace_id', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['paper_id'], ['paperdraft.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_generationjob_paper_id', 'generationjob', ['paper_id'])

    # ---- ExamSource ----
    op.create_table('examsource',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('grade_class_id', sa.Integer(), nullable=False),
        sa.Column('subject_id', sa.Integer(), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('source_type', sourcetype_enum, nullable=False),
        sa.Column('title', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('chapters', sa.JSON(), nullable=False),
        sa.Column('storage_key', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.Column('page_count', sa.Integer(), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['grade_class_id'], ['gradeclass.id'], ),
        sa.ForeignKeyConstraint(['subject_id'], ['subject.id'], ),
        sa.ForeignKeyConstraint(['created_by'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_examsource_grade_class_id', 'examsource', ['grade_class_id'])
    op.create_index('ix_examsource_subject_id', 'examsource', ['subject_id'])
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_examsource_subject_id', table_name='examsource')
    op.drop_index('ix_examsource_grade_class_id', table_name='examsource')
    op.drop_table('examsource')
    op.drop_index('ix_generationjob_paper_id', table_name='generationjob')
    op.drop_table('generationjob')
    op.drop_index('ix_paperdraft_subject_id', table_name='paperdraft')
    op.drop_index('ix_paperdraft_grade_class_id', table_name='paperdraft')
    op.drop_table('paperdraft')

    # enums drop (pehle tables drop, phir types)
    for name in ('sourcetype', 'generationjobstatus', 'coveragemode', 'paperstatus'):
        postgresql.ENUM(name=name).drop(op.get_bind(), checkfirst=True)
    # ### end Alembic commands ###