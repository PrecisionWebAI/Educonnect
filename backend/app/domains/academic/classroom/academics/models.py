from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, Index, UniqueConstraint, text
from sqlmodel import Field, SQLModel

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


class SubjectTeacherBase(SQLModel):
    """Which teacher takes one section subject - and since when.

    **History, not a pointer** (Phase 5): a teacher change closes the old row
    (`effective_to`) and opens a new one (`effective_from`). Nothing is overwritten,
    which is what lets the course bar say "2 of 10 chapters were done by the last
    teacher" instead of moving that work to whoever holds the subject today.

    The row names the **section subject** (`classroomsubject`) and nothing else: the
    section and the session are read from it, so the two can never disagree.
    """

    classroom_subject_id: UUID = Field(foreign_key="classroomsubject.id", index=True)
    #: An `employee`, not a user: only staff take a class.
    teacher_id: UUID = Field(foreign_key="employee.id")
    #: The session the assignment belongs to (the `academic_year` row).
    academic_year_id: UUID | None = Field(
        default=None, foreign_key="academic_year.id", index=True
    )
    #: The day this teacher took the subject. Part of the key, so one person cannot be
    #: recorded twice for the same day and two people can hold the subject in sequence.
    effective_from: date = Field(default_factory=date.today)
    #: The day they stopped. NULL = they hold it now.
    effective_to: date | None = None


class SubjectTeacher(SubjectTeacherBase, TenantMixin, UUIDMixin, table=True):
    """The history of a section subject - one **open** row at a time.

    `UNIQUE(classroom_subject_id, effective_from)` stops one person being recorded twice
    on the same day; the partial unique index makes "who teaches this now" a single
    answer (at most one open row per section subject). A teacher change closes the open
    row (`effective_to`) and opens a new one - nothing is ever overwritten.
    """

    __table_args__ = (
        UniqueConstraint(
            "classroom_subject_id",
            "effective_from",
            name="uq_subjectteacher_cs_from",
        ),
        Index(
            "uq_subjectteacher_open_cs",
            "classroom_subject_id",
            unique=True,
            postgresql_where=text("effective_to IS NULL"),
            sqlite_where=text("effective_to IS NULL"),
        ),
    )


class ChapterBase(SQLModel):
    """One chapter of one section subject's syllabus, in one session.

    A chapter belongs to the **classroom subject** (Class 9-A's "Mathematics"), not to
    the class: two sections plan independently, and "Copy chapters" is only a
    convenience. Progress (`status`, `completed_on`, `completed_by_employee_id`) lives
    on the row itself because the row is already section-owned.
    """

    #: The section-owned subject this chapter belongs to (Phase 2).
    classroom_subject_id: UUID = Field(foreign_key="classroomsubject.id", index=True)
    #: The session the plan belongs to (`academic_year.id`).
    academic_year_id: UUID = Field(foreign_key="academic_year.id", index=True)
    #: 1-based position in the book - what the screen numbers.
    sequence: int
    name: str
    #: The date the school planned to finish it. NULL = nobody planned it.
    planned_date: date | None = None
    #: Progress lives on the chapter because the chapter is already section-owned.
    status: str = Field(default="Pending")
    completed_on: date | None = None
    completed_by_employee_id: UUID | None = Field(
        default=None, foreign_key="employee.id", index=True
    )
    #: What the teacher saved and the principal has not approved yet: `Completed` or
    #: `Skipped`. `status` (and every count) moves only when it is approved.
    proposed_status: str | None = None
    proposed_by_employee_id: UUID | None = Field(
        default=None, foreign_key="employee.id", index=True
    )
    proposed_at: datetime | None = None
    #: Skipped by the *rule* (a later chapter was finished), not by the teacher's
    #: choice. Such a skip is undone when the chapter is no longer in between.
    auto_skipped: bool = Field(default=False)
    proposed_auto: bool = Field(default=False)


class Chapter(ChapterBase, TenantMixin, UUIDMixin, table=True):
    """One chapter in one section subject, in one order."""

    __table_args__ = (
        UniqueConstraint(
            "classroom_subject_id",
            "sequence",
            name="uq_chapter_classroom_subject_sequence",
        ),
        CheckConstraint(
            "status IN ('Pending', 'In progress', 'Completed', 'Skipped')",
            name="ck_chapter_status",
        ),
    )


#: The words the Course tab shows. Stored as words (like every other status here) so a
#: report does not have to translate a code, and `CanonicalRequest` keeps their case.
CHAPTER_PENDING = "Pending"
CHAPTER_IN_PROGRESS = "In progress"
CHAPTER_COMPLETED = "Completed"
CHAPTER_SKIPPED = "Skipped"
CHAPTER_STATUSES: tuple[str, ...] = (
    CHAPTER_PENDING,
    CHAPTER_IN_PROGRESS,
    CHAPTER_COMPLETED,
    CHAPTER_SKIPPED,
)
