from datetime import date
from uuid import UUID

from sqlmodel import Field, SQLModel

from app.core.ids import UUIDMixin
from app.core.tenancy import TenantMixin


class StudentProfileBase(SQLModel):
    #: The student's own name, stored **on the profile**: a student whose admission
    #: form gave no email has no login, and still needs a name to show.
    full_name: str | None = None
    #: The login this student signs in with, when the form gave an email. `None`
    #: means they have no login at all - the office can add one later.
    user_id: UUID | None = Field(default=None, foreign_key="user.id", unique=True)
    admission_number: str = Field(unique=True, index=True)
    date_of_birth: date
    guardian_name: str
    # "Male" / "Female" - free text on purpose (some records have no gender, and
    # schools may add local values). Used for the boys/girls split in the class
    # matrix; unknown gender counts towards strength only.
    gender: str | None = Field(default=None)
    #: The class-section the student sits in - a `classroom` row ("Class 10-A"),
    #: which is exactly what makes that row exist. The class and the section are
    #: reached through it. Nullable on purpose: a student can be registered before
    #: they are placed anywhere.
    classroom_id: UUID | None = Field(
        default=None, foreign_key="classroom.id", index=True
    )


class StudentProfile(StudentProfileBase, TenantMixin, UUIDMixin, table=True):
    pass


class StudentParentRelationshipBase(SQLModel):
    """Maps a parent/guardian user to a student."""

    student_id: UUID = Field(foreign_key="studentprofile.id")
    parent_user_id: UUID = Field(foreign_key="user.id")
    relationship_type: str = Field(default="Parent")  # E.g., Mother, Father, Guardian


class StudentParentRelationship(StudentParentRelationshipBase, TenantMixin, UUIDMixin, table=True):
    pass
