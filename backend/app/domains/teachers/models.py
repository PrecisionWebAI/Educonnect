from datetime import date, datetime

from sqlmodel import Field, SQLModel

from app.core.tenancy import TenantMixin


class TeacherProfileBase(SQLModel):
    user_id: int = Field(foreign_key="user.id", unique=True)
    department: str
    qualification: str
    joining_date: date


class TeacherProfile(TeacherProfileBase, TenantMixin, table=True):
    id: int | None = Field(default=None, primary_key=True)


class TeacherAssignmentBase(SQLModel):
    """Maps a teacher to a specific class and subject."""

    teacher_id: int = Field(foreign_key="teacherprofile.id")
    classroom_id: int = Field(foreign_key="classroom.id")
    section_id: int | None = Field(default=None, foreign_key="section.id")
    subject_id: int = Field(foreign_key="subject.id")


class TeacherAssignment(TeacherAssignmentBase, TenantMixin, table=True):
    id: int | None = Field(default=None, primary_key=True)


class ClassTeacherAssignmentBase(SQLModel):
    """Maps a teacher to a specific class/section as the official Class Teacher."""

    teacher_id: int = Field(foreign_key="teacherprofile.id")
    classroom_id: int = Field(foreign_key="classroom.id")
    section_id: int | None = Field(default=None, foreign_key="section.id")


class ClassTeacherAssignment(ClassTeacherAssignmentBase, TenantMixin, table=True):
    id: int | None = Field(default=None, primary_key=True)


class TeacherReviewBase(SQLModel):
    """A single anonymous review/rating of a teacher (Tab 9.4 — Performance & Review).

    The screen shows a per-teacher summary (average star rating, review count,
    trend, score), so we store the individual ratings and aggregate them rather
    than keeping a denormalised snapshot. `reviewer_role` records who left the
    rating (\"Parent\" / \"Principal\" / \"HOD\") without storing their identity,
    which is what \"anonymous ratings\" means in the blueprint.
    """

    teacher_id: int = Field(foreign_key="teacherprofile.id")
    rating: int = Field(ge=1, le=5)
    reviewer_role: str = Field(default="Parent")
    comment: str | None = None


class TeacherReview(TeacherReviewBase, TenantMixin, table=True):
    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
