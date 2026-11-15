from datetime import date
from uuid import UUID

from pydantic import BaseModel

from app.core.text import CanonicalRequest


class ChapterRowRead(BaseModel):
    """One chapter as the Course tab draws it: the plan plus this section's answer."""

    chapter_id: UUID
    sequence: int
    name: str
    planned_date: date | None = None
    #: Pending / In progress / Completed - the words the tab shows.
    status: str
    completed_on: date | None = None
    completed_by: str | None = None
    completed_by_employee_id: UUID | None = None
    #: The saved row, when there is one (a plan with no progress has none yet).
    progress_id: UUID | None = None
    #: True when the chapter was finished on or before its planned date.
    ahead: bool | None = None
    #: True when the planned date has passed and it is not finished.
    behind: bool = False
    #: May this caller tick it? (the subject teacher, or the office)
    can_tick: bool = False


class CourseTeacherRead(BaseModel):
    """Who taught this subject, and how much of the plan they finished.

    The share is what makes a teacher change legible: "2 of 10" for the person who left,
    "0 of 10" for the one who took over, instead of moving the old work to the new name.
    """

    employee_id: UUID
    name: str
    effective_from: date | None = None
    effective_to: date | None = None
    #: True for the person holding the subject today.
    current: bool = False
    #: Chapters of this subject **this** person completed in this section.
    completed: int = 0


class SubjectCourseRead(BaseModel):
    """One subject's course in one class-section."""

    subject_id: UUID
    subject: str
    #: The teacher holding it today (`None` when nobody is assigned).
    current_teacher: str | None = None
    current_teacher_id: UUID | None = None
    #: Everyone who has held it, oldest first.
    teachers: list[CourseTeacherRead] = []
    done: int = 0
    total: int = 0
    #: `None` when there is no plan - "no plan" is not "0%".
    percent: float | None = None
    #: The first chapter that is not completed (what the class is on now).
    next_chapter: str | None = None
    #: Chapters whose planned date has passed and that are not completed.
    behind: int = 0
    #: True when at least one chapter carries a planned date.
    planned: bool = False
    chapters: list[ChapterRowRead] = []


class SectionCourseRead(BaseModel):
    """`GET /classroom/sections/{id}/course` - the whole Course tab in one read."""

    section_id: UUID
    label: str
    #: The session the plan belongs to ("2026-27"), when one is open.
    academic_year: str | None = None
    subjects: list[SubjectCourseRead] = []


class ChapterTickIn(CanonicalRequest):
    """Tick a chapter for one class-section.

    The section is part of the body because a chapter belongs to the **class** and the
    progress belongs to the **section**: the same chapter can be done in 9-A and not in
    9-B, and only the caller knows which register they are looking at.
    """

    classroom_id: UUID
    #: Pending / In progress / Completed (the tab's own words).
    status: str
