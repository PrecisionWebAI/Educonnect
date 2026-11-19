from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import Index, UniqueConstraint, text
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


class SubjectBase(SQLModel):
    #: Both unique **inside a school** - two schools may each have a "Mathematics".
    #: `Subject` adds the (school_id, name) / (school_id, code) unique indexes.
    name: str = Field(index=True)
    code: str = Field(index=True)
    #: Retired subjects stay (papers, chapters and timetables point at them); they leave
    #: the "Add Subject" dropdown. Same shape as `department.is_active`.
    is_active: bool = Field(default=True)


class Subject(SubjectBase, TenantMixin, UUIDMixin, table=True):
    __table_args__ = (
        UniqueConstraint("school_id", "name", name="uq_subject_school_name"),
        UniqueConstraint("school_id", "code", name="uq_subject_school_code"),
    )


class SubjectTeacherBase(SQLModel):
    """Which teacher takes a subject in one class-section - and since when.

    The mapping belongs to the subject - it is *about* a subject - so it lives here next
    to `Subject` rather than with the timetable. It is keyed by `(classroom, subject)`
    and not by subject alone: a school has a single "Mathematics" row but many teachers
    of it, because Class 9-A and Class 9-B usually have different ones.

    **History, not a pointer** (Phase 5): a teacher change closes the old row
    (`effective_to`) and opens a new one (`effective_from`). Nothing is overwritten,
    which is what lets the course bar say "2 of 10 chapters were done by the last
    teacher" instead of moving that work to whoever holds the subject today.
    """

    classroom_id: UUID = Field(foreign_key="classroom.id")
    subject_id: UUID = Field(foreign_key="subject.id")
    #: The `classroomsubject` row this assignment belongs to ("this subject is in this
    #: section, in this session"). NULL only on rows written before Phase 1's backfill;
    #: the legacy `(classroom_id, subject_id)` columns stay so every existing read keeps
    #: working.
    classroom_subject_id: UUID | None = Field(
        default=None, foreign_key="classroomsubject.id", index=True
    )
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
    """The history of a subject in a section - one **open** row per subject.

    `UNIQUE(classroom_id, subject_id, effective_from)` stops one person being recorded
    twice on the same day. The two partial unique indexes are the Phase 1 rule that makes
    "who teaches this now" a single answer: at most one open row per `classroomsubject`
    (and, for rows written before that column existed, per class-section + subject).
    A teacher change closes the open row (`effective_to`) and opens a new one - nothing
    is ever overwritten.
    """

    __table_args__ = (
        UniqueConstraint(
            "classroom_id",
            "subject_id",
            "effective_from",
            name="uq_subjectteacher_classroom_subject_from",
        ),
        Index(
            "uq_subjectteacher_open_cs",
            "classroom_subject_id",
            unique=True,
            postgresql_where=text(
                "effective_to IS NULL AND classroom_subject_id IS NOT NULL"
            ),
            sqlite_where=text(
                "effective_to IS NULL AND classroom_subject_id IS NOT NULL"
            ),
        ),
        Index(
            "uq_subjectteacher_open_legacy",
            "classroom_id",
            "subject_id",
            unique=True,
            postgresql_where=text(
                "effective_to IS NULL AND classroom_subject_id IS NULL"
            ),
            sqlite_where=text("effective_to IS NULL AND classroom_subject_id IS NULL"),
        ),
    )


class ChapterBase(SQLModel):
    """One chapter of a subject's syllabus, for a class, in one session.

    A chapter belongs to the **class** (Class 9), not to a section: every section of
    Class 9 reads the same book in the same order. *How far each section has got* is
    `ChapterProgress`, one row per chapter per class-section - which is exactly what the
    Course tab needs and what the old two-counter table used to guess at.
    """

    class_id: UUID = Field(foreign_key="classname.class_id", index=True)
    subject_id: UUID = Field(foreign_key="subject.id", index=True)
    #: The session the plan belongs to (`academic_year.id`).
    academic_year_id: UUID = Field(foreign_key="academic_year.id", index=True)
    #: 1-based position in the book - what the screen numbers.
    sequence: int
    name: str
    #: The date the school planned to finish it. NULL = nobody planned it.
    planned_date: date | None = None


class Chapter(ChapterBase, TenantMixin, UUIDMixin, table=True):
    """`UNIQUE(school_id, class_id, subject_id, academic_year_id, sequence)`."""

    __table_args__ = (
        UniqueConstraint(
            "school_id",
            "class_id",
            "subject_id",
            "academic_year_id",
            "sequence",
            name="uq_chapter_school_class_subject_year_sequence",
        ),
    )


#: The words the Course tab shows. Stored as words (like every other status here) so a
#: report does not have to translate a code, and `CanonicalRequest` keeps their case.
CHAPTER_PENDING = "Pending"
CHAPTER_IN_PROGRESS = "In progress"
CHAPTER_COMPLETED = "Completed"
CHAPTER_STATUSES: tuple[str, ...] = (
    CHAPTER_PENDING,
    CHAPTER_IN_PROGRESS,
    CHAPTER_COMPLETED,
)


class ChapterProgressBase(SQLModel):
    """How far **one class-section** has got with one chapter.

    The single source of "chapters done": the Course bar, the Classroom card and the
    Teachers performance score all count these rows, so the three can never disagree and
    there is no second copy of the number anywhere.
    """

    chapter_id: UUID = Field(foreign_key="chapter.id", index=True)
    classroom_id: UUID = Field(foreign_key="classroom.id", index=True)
    status: str = Field(default=CHAPTER_PENDING)
    #: Set when the status becomes `Completed`, cleared when it leaves `Completed`.
    completed_on: date | None = None
    #: Who ticked it - an employee, so a teacher change does not move old work.
    completed_by_employee_id: UUID | None = Field(
        default=None, foreign_key="employee.id", index=True
    )


class ChapterProgress(ChapterProgressBase, TenantMixin, UUIDMixin, table=True):
    """`UNIQUE(chapter_id, classroom_id)` - one answer per chapter per section."""

    __table_args__ = (
        UniqueConstraint(
            "chapter_id",
            "classroom_id",
            name="uq_chapterprogress_chapter_classroom",
        ),
    )

    updated_at: datetime = Field(default_factory=datetime.utcnow)
