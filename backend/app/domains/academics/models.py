from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

from app.core.ids import UUIDMixin
from app.core.tenancy import TenantMixin


class ClassNameBase(SQLModel):
    """The platform's class vocabulary - the wording a class is known by."""

    #: "Nursery", "LKG", "UKG", "Class 1" … "Class 12".
    classname: str = Field(index=True)
    #: School stage for grouping/reporting: pre_primary, primary, middle,
    #: secondary, senior_secondary.
    stage: str = Field(default="primary")
    #: Position in the school (0 = Nursery). The name is the truth; the level
    #: only sorts - a class list sorted as text puts "Class 10" before "Class 2".
    level: int = Field(default=0)


class ClassName(ClassNameBase, table=True):
    """**Platform catalog** - 15 classes, seeded once, never growing per school.

    Deliberately has no `school_id`: every school reads the same 15 rows, so a
    class id means the same thing everywhere. (The school-owned tables are the
    ones that need a tenant column; a platform catalog is like `role`.)
    """

    __tablename__ = "classname"

    class_id: UUID = Field(default_factory=uuid4, primary_key=True)

    __table_args__ = (UniqueConstraint("classname", name="uq_classname_name"),)


class SectionBase(SQLModel):
    """The platform's section vocabulary."""

    #: "A" … "J" - the letters a class is split into.
    section_name: str = Field(index=True)


class Section(SectionBase, table=True):
    """**Platform catalog** - A-J, seeded once, never growing per school."""

    __tablename__ = "section"

    section_id: UUID = Field(default_factory=uuid4, primary_key=True)

    __table_args__ = (UniqueConstraint("section_name", name="uq_section_name"),)


class ClassroomBase(SQLModel):
    """One class-section a school actually runs: "Class 10-A".

    The class and the section are ids into the two platform catalogs, so the
    wording lives in exactly one place (`classname` / `section`) and a rename
    follows through everywhere.
    """

    class_id: UUID = Field(foreign_key="classname.class_id", index=True)
    section_id: UUID = Field(foreign_key="section.section_id", index=True)
    #: Who runs this class-section: one teacher, or nobody yet. It is a column
    #: rather than an assignment row because the rule *is* "at most one class
    #: teacher per class-section" - the column cannot express anything else.
    class_teacher_id: UUID | None = Field(
        default=None, foreign_key="employee.id", index=True
    )


class Classroom(ClassroomBase, TenantMixin, UUIDMixin, table=True):
    """A school's class-section row - created the moment it is used.

    It belongs to one school (the tenant column) and grows with it: the row is
    written when a student is registered into that class-section, when a class
    teacher is assigned, or when a timetable period is added - never in bulk for
    all 15 x 10 combinations. `UNIQUE(school_id, class_id, section_id)` keeps it
    to one row per class-section per school.
    """

    __table_args__ = (
        UniqueConstraint(
            "school_id",
            "class_id",
            "section_id",
            name="uq_classroom_school_class_section",
        ),
    )


class SubjectBase(SQLModel):
    #: Both unique **inside a school** - two schools may each have a "Mathematics".
    #: `Subject` adds the (school_id, name) / (school_id, code) unique indexes.
    name: str = Field(index=True)
    code: str = Field(index=True)


class Subject(SubjectBase, TenantMixin, UUIDMixin, table=True):
    __table_args__ = (
        UniqueConstraint("school_id", "name", name="uq_subject_school_name"),
        UniqueConstraint("school_id", "code", name="uq_subject_school_code"),
    )


class SubjectTeacherBase(SQLModel):
    """Which teacher takes a subject in one class-section.

    The mapping belongs to the subject - it is *about* a subject - so it lives
    here next to `Subject` rather than with the timetable. It is keyed by
    `(classroom, subject)` and not by subject alone: a school has a single
    "Mathematics" row but many teachers of it, because Class 9-A and Class 9-B
    usually have different ones.
    """

    classroom_id: UUID = Field(foreign_key="classroom.id")
    subject_id: UUID = Field(foreign_key="subject.id")
    #: An `employee`, not a user: only staff take a class.
    teacher_id: UUID = Field(foreign_key="employee.id")


class SubjectTeacher(SubjectTeacherBase, TenantMixin, UUIDMixin, table=True):
    """`UNIQUE(classroom_id, subject_id)` - one teacher per subject per class-section."""

    __table_args__ = (
        UniqueConstraint(
            "classroom_id", "subject_id", name="uq_subjectteacher_classroom_subject"
        ),
    )



class SyllabusProgressBase(SQLModel):
    """How far a class-section has got through a subject's syllabus.

    The card's "course complete %" is `chapters_done / chapters_total`. It hangs
    off the **class-section** (the card shows one), and the class is reached
    through `classroom.class_id` - no second copy of the class id.
    """

    classroom_id: UUID = Field(foreign_key="classroom.id")
    subject_id: UUID = Field(foreign_key="subject.id")
    chapters_total: int = 0
    chapters_done: int = 0


class SyllabusProgress(SyllabusProgressBase, TenantMixin, UUIDMixin, table=True):
    """`UNIQUE(classroom_id, subject_id)` - one progress row per subject per class-section."""

    __table_args__ = (
        UniqueConstraint(
            "classroom_id", "subject_id", name="uq_syllabusprogress_classroom_subject"
        ),
    )

    updated_at: datetime = Field(default_factory=datetime.utcnow)
