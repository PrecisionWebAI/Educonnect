"""Response models for the Classroom screen (camelCase, like `/classroom/classes`)."""

from datetime import date
from uuid import UUID
from pydantic import BaseModel


class SectionCard(BaseModel):
    """One class-section card - the unit the Classroom grid shows.

    Every field is computed from real rows. A field with no data behind it is
    `None` and the card renders "—" rather than inventing a number.
    """

    sectionId: UUID
    sectionName: str
    classTeacher: str | None = None
    strength: int = 0
    boys: int = 0
    girls: int = 0
    #: Students present on `attendanceDate` (the section's latest register day).
    presentToday: int = 0
    attendanceDate: date | None = None
    attendancePercent: float | None = None
    #: Sum of the class's fee structures across the section's students.
    feesExpected: float | None = None
    feesCollected: float | None = None
    feesPercent: float | None = None
    #: `chapters_done / chapters_total` across the section's tracked subjects.
    syllabusPercent: float | None = None
    subjectsTracked: int = 0
    #: Assignments whose due date has not passed yet.
    homeworkOpen: int = 0
    timetablePeriods: int = 0
    #: Average `marks_obtained / max_marks` across the section's marks.
    avgMarksPercent: float | None = None
    examsCount: int = 0
    lastDiaryDate: date | None = None


class ClassGroup(BaseModel):
    """A class heading ("Class 6") with its section cards beneath it."""

    classroomId: UUID
    className: str
    level: int
    stage: str
    strength: int = 0
    sectionCount: int = 0
    sections: list[SectionCard] = []


# ---------------------------------------------------------------------------
# Phase 2 - the drill-down behind one class-section card
# ---------------------------------------------------------------------------


class ClassTeacherInfo(BaseModel):
    """Who runs this section (`section.class_teacher_id` -> employee -> user)."""

    #: The employee, so the screen can preselect them in the picker.
    employeeId: UUID | None = None
    name: str | None = None
    email: str | None = None
    phone: str | None = None


class SectionStudent(BaseModel):
    studentId: UUID
    name: str
    admissionNumber: str
    guardian: str | None = None
    gender: str | None = None
    attendancePercent: float | None = None
    feesPaid: float = 0.0
    feesDue: float = 0.0


class AttendanceDay(BaseModel):
    date: date
    present: int = 0
    absent: int = 0
    leave: int = 0
    late: int = 0
    total: int = 0
    percent: float = 0.0


class TimetableSlot(BaseModel):
    day: str
    startTime: str
    endTime: str
    subject: str
    teacher: str | None = None
    room: str | None = None


class HomeworkRow(BaseModel):
    id: UUID
    title: str
    subject: str
    teacher: str | None = None
    dueDate: date
    submitted: int = 0
    total: int = 0


class DiaryRow(BaseModel):
    """One line of the class log - the class's day, not a per-student note."""

    id: UUID
    date: date
    note: str
    teacher: str | None = None


class ExamRow(BaseModel):
    id: UUID
    name: str
    term: str | None = None
    status: str
    averagePercent: float | None = None
    marksEntered: int = 0


class SubjectMarkRow(BaseModel):
    subject: str
    averagePercent: float | None = None
    highest: float | None = None
    lowest: float | None = None
    entries: int = 0


class SubjectTeacherRow(BaseModel):
    """One subject the school offers, and who takes it in this section.

    Every subject appears, with `teacherId`/`teacherName` null where nobody has
    been assigned yet - the empty slots are what the screen assigns into.
    """

    subjectId: UUID
    name: str
    code: str
    teacherId: UUID | None = None
    teacherName: str | None = None


class TeacherOption(BaseModel):
    """A teacher the Classroom screen can assign."""

    employeeId: UUID
    name: str
    email: str


class AssignTeacherIn(BaseModel):
    """Body of the two assignment routes: a teacher, or null to clear."""

    teacherId: UUID | None = None


# ---------------------------------------------------------------------------
# Marks of one class-section - the Academics tab
# ---------------------------------------------------------------------------


class SectionMarkSubjectRead(BaseModel):
    """One subject's score for one student. The maximum comes from the exam."""

    subjectId: UUID
    subject: str
    obtained: float
    max: float


class SectionMarkRead(BaseModel):
    """One student's marks in one exam - the row the Academics tab renders."""

    studentId: UUID
    studentName: str
    admissionNumber: str
    className: str
    examId: UUID
    exam: str
    rows: list[SectionMarkSubjectRead] = []


class SectionMarkEntryIn(BaseModel):
    """One score being written: a student, a subject, the marks obtained."""

    student_id: UUID
    subject_id: UUID
    marks_obtained: float


class SectionMarksSave(BaseModel):
    """Body of `PUT /classroom/sections/{id}/marks` - the scores just entered."""

    exam_id: UUID
    entries: list[SectionMarkEntryIn] = []


# ---------------------------------------------------------------------------
# School-wide results and mark disputes - the Classroom grid's tabs
# ---------------------------------------------------------------------------


class ClassResultRead(BaseModel):
    """One class's figures in one exam (the Results tab)."""

    #: `exam:class` - the row key the table needs.
    id: str
    exam: str
    className: str
    passRate: float
    avgScore: float
    topper: str


class ExamOptionRead(BaseModel):
    """An exam a dispute can be filed against."""

    id: UUID
    name: str


class DisputeRead(BaseModel):
    """A mark a family is challenging, with the names the screen shows."""

    id: UUID
    student: str
    exam: str
    subject: str
    reason: str
    status: str


class DisputeCreate(BaseModel):
    """Body of `POST /classroom/disputes`."""

    student_id: UUID
    exam_id: UUID
    subject_id: UUID
    reason: str


class DisputeStatusUpdate(BaseModel):
    """Body of `PUT /classroom/disputes/{id}` - where the challenge has got to."""

    status: str


class SectionDetail(BaseModel):
    """Everything the drill-down shows for one class-section."""
    sectionId: UUID
    classLabel: str
    className: str
    #: The class's own id — the Timetable tab reads this section's week through
    #: `/timetable/class/{classroomId}?section_id={sectionId}`.
    classroomId: UUID
    #: The section letter on its own ("J") - the Students / Attendance views on this
    #: page scope themselves by class and section, so they need the names apart.
    sectionName: str
    stage: str
    classTeacher: ClassTeacherInfo | None = None
    strength: int = 0
    boys: int = 0
    girls: int = 0
    attendancePercent: float | None = None
    syllabusPercent: float | None = None
    feesExpected: float | None = None
    feesCollected: float | None = None
    feesPercent: float | None = None
    students: list[SectionStudent] = []
    attendance: list[AttendanceDay] = []
    timetable: list[TimetableSlot] = []
    homework: list[HomeworkRow] = []
    diary: list[DiaryRow] = []
    exams: list[ExamRow] = []
    marks: list[SubjectMarkRow] = []
    #: Every subject with its teacher for this section (null where unassigned).
    subjects: list[SubjectTeacherRow] = []
