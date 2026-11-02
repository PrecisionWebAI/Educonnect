"""Response models for the Classroom screen (camelCase, like `/classroom/classes`)."""

from datetime import date

from pydantic import BaseModel


class SectionCard(BaseModel):
    """One class-section card - the unit the Classroom grid shows.

    Every field is computed from real rows. A field with no data behind it is
    `None` and the card renders "—" rather than inventing a number.
    """

    sectionId: int
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

    classroomId: int
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
    """Who runs this section (`classteacherassignment` -> employee -> user)."""

    name: str | None = None
    email: str | None = None
    phone: str | None = None


class SectionStudent(BaseModel):
    studentId: int
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
    id: int
    title: str
    subject: str
    teacher: str | None = None
    dueDate: date
    submitted: int = 0
    total: int = 0


class DiaryRow(BaseModel):
    id: int
    date: date
    student: str
    teacher: str | None = None
    note: str


class ExamRow(BaseModel):
    id: int
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


class SectionDetail(BaseModel):
    """Everything the drill-down shows for one class-section."""

    sectionId: int
    classLabel: str
    className: str
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
