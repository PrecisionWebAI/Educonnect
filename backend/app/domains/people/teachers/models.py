from datetime import datetime
from uuid import UUID

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel

from app.core.ids import UUIDMixin
from app.core.tenancy import TenantMixin


class TeacherSubjectBase(SQLModel):
    """One subject a teacher can teach - many rows per teacher.

    This is the teacher's own subject list (what the hire form collects), not
    *where* they teach: who actually takes a subject in a class-section is
    `academics.SubjectTeacher`, and who runs a section is
    `academics.Section.class_teacher_id`. Keeping the three apart means a teacher
    can be listed against five subjects before any class has been assigned to them.
    """

    teacher_id: UUID = Field(foreign_key="employee.id")
    subject_id: UUID = Field(foreign_key="subject.id")


class TeacherSubject(TeacherSubjectBase, TenantMixin, UUIDMixin, table=True):
    """`UNIQUE(teacher_id, subject_id)` - the same subject is not listed twice."""

    __table_args__ = (
        UniqueConstraint(
            "teacher_id", "subject_id", name="uq_teachersubject_teacher_subject"
        ),
    )


class TeacherReviewBase(SQLModel):
    """A single anonymous review/rating of a teacher (Tab 9.4 — Performance & Review).

    The screen shows a per-teacher summary (average star rating, review count,
    trend, score), so we store the individual ratings and aggregate them rather
    than keeping a denormalised snapshot. `reviewer_role` records who left the
    rating (\"Parent\" / \"Principal\" / \"HOD\") without storing their identity,
    which is what \"anonymous ratings\" means in the blueprint.
    """

    teacher_id: UUID = Field(foreign_key="employee.id")
    rating: int = Field(ge=1, le=5)
    reviewer_role: str = Field(default="Parent")
    comment: str | None = None


class TeacherReview(TeacherReviewBase, TenantMixin, UUIDMixin, table=True):
    created_at: datetime = Field(default_factory=datetime.utcnow)
