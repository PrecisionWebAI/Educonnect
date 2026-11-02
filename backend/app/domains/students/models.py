from datetime import date
from uuid import UUID

from sqlmodel import Field, SQLModel

from app.core.ids import UUIDMixin
from app.core.tenancy import TenantMixin


class StudentProfileBase(SQLModel):
    user_id: UUID = Field(foreign_key="user.id", unique=True)
    admission_number: str = Field(unique=True, index=True)
    date_of_birth: date
    guardian_name: str
    # "Male" / "Female" - free text on purpose (some records have no gender, and
    # schools may add local values). Used for the boys/girls split in the class
    # matrix; unknown gender counts towards strength only.
    gender: str | None = Field(default=None)
    #: The class-section the student sits in. The class comes from
    #: `section.classroom_id`, so it is not copied here. Nullable on purpose: a
    #: student can be registered before they are placed anywhere.
    section_id: UUID | None = Field(default=None, foreign_key="section.id")


class StudentProfile(StudentProfileBase, TenantMixin, UUIDMixin, table=True):
    pass


class StudentParentRelationshipBase(SQLModel):
    """Maps a parent/guardian user to a student."""

    student_id: UUID = Field(foreign_key="studentprofile.id")
    parent_user_id: UUID = Field(foreign_key="user.id")
    relationship_type: str = Field(default="Parent")  # E.g., Mother, Father, Guardian


class StudentParentRelationship(StudentParentRelationshipBase, TenantMixin, UUIDMixin, table=True):
    pass
