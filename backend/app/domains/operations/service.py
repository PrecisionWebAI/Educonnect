"""Queries behind the Operations screens that used to answer with fixtures.

The Classroom screen is the first of them: `/operations/classroom/classes` and
`/operations/classroom/lesson-detail` returned invented cards ("Physics -
Class 10A", "M. Iyer", 42 students) and a fixed "Ohm Law and Circuits" lesson.
The school already stores all of it - who teaches what (`teacherassignment`),
when (`timetableperiod`), the roll (`studentprofile`), the newest homework
(`homeworkassignment`) and the content library (`examsource`) - so these
functions read those tables instead of making it up.
"""

from sqlalchemy import func
from sqlmodel import Session, select

from app.domains.academics.models import Classroom, Section, Subject
from app.domains.auth.roles import has_role
from app.domains.exams.models import ExamSource, SourceType
from app.domains.homework.models import HomeworkAssignment
from app.domains.students.models import StudentProfile
from app.domains.teachers.models import TeacherAssignment, TeacherProfile
from app.domains.timetable.models import TimetablePeriod
from app.domains.users.models import User

from .schemas import ClassroomItem, LessonDetail, LessonResource

#: Roles that look after the whole school, so their Classroom screen lists every
#: class instead of only the ones they teach themselves.
SCHOOL_WIDE_ROLES = ("system_admin", "owner", "principal", "vice_principal", "hod")

#: `examsource.source_type` -> the label the lesson card shows for a resource.
RESOURCE_LABELS: dict[str, str] = {
    SourceType.pdf.value: "PDF",
    SourceType.image.value: "Image",
    SourceType.url.value: "Link",
    SourceType.text.value: "Notes",
    SourceType.bank.value: "Question bank",
}


def _strength_by_section(session: Session) -> dict[int, int]:
    """{section_id: students} - the roll printed on every card."""
    rows = session.exec(
        select(StudentProfile.section_id, func.count()).group_by(
            StudentProfile.section_id
        )
    ).all()
    return {
        int(section_id): int(count)
        for section_id, count in rows
        if section_id is not None
    }


def _teaching_rows(
    session: Session, user: User
) -> list[tuple[TeacherAssignment, Classroom, Section, Subject, User]]:
    """The (assignment, class, section, subject, teacher) rows this person may see.

    A teacher sees only their own assignments; an admin-type role sees the whole
    school's, which is what the screen means by "all classes".
    """
    statement = (
        select(TeacherAssignment, Classroom, Section, Subject, User)
        .join(Classroom, TeacherAssignment.classroom_id == Classroom.id)
        .join(Section, TeacherAssignment.section_id == Section.id)
        .join(Subject, TeacherAssignment.subject_id == Subject.id)
        .join(TeacherProfile, TeacherAssignment.teacher_id == TeacherProfile.id)
        .join(User, TeacherProfile.user_id == User.id)
        .order_by(Classroom.level, Section.name, Subject.name)
    )
    if not has_role(user, *SCHOOL_WIDE_ROLES):
        profile = session.exec(
            select(TeacherProfile).where(TeacherProfile.user_id == user.id)
        ).first()
        if profile is None or profile.id is None:
            return []
        statement = statement.where(TeacherAssignment.teacher_id == profile.id)
    return list(session.exec(statement).all())


def _next_period(
    session: Session, section_id: int, subject_id: int
) -> TimetablePeriod | None:
    """The first period of the week for that subject in that section."""
    return session.exec(
        select(TimetablePeriod)
        .where(
            TimetablePeriod.section_id == section_id,
            TimetablePeriod.subject_id == subject_id,
        )
        .order_by(  # type: ignore[arg-type]
            TimetablePeriod.day_of_week, TimetablePeriod.start_time
        )
    ).first()


def _latest_homework(
    session: Session, section_id: int, subject_id: int
) -> HomeworkAssignment | None:
    return session.exec(
        select(HomeworkAssignment)
        .where(
            HomeworkAssignment.section_id == section_id,
            HomeworkAssignment.subject_id == subject_id,
        )
        .order_by(HomeworkAssignment.due_date.desc())  # type: ignore[attr-defined]
    ).first()


def classroom_cards(session: Session, user: User) -> list[ClassroomItem]:
    """One card per class-section-subject the person teaches."""
    strengths = _strength_by_section(session)
    cards: list[ClassroomItem] = []
    for assignment, classroom, section, subject, teacher_user in _teaching_rows(
        session, user
    ):
        period = _next_period(session, section.id, subject.id)  # type: ignore[arg-type]
        homework = _latest_homework(session, section.id, subject.id)  # type: ignore[arg-type]
        if period is not None:
            next_lesson = (
                f"{subject.name} · "
                f"{period.day_of_week.value.title()} {period.start_time:%H:%M}"
            )
            if period.room:
                next_lesson = f"{next_lesson} · {period.room}"
        elif homework is not None:
            next_lesson = homework.title
        else:
            next_lesson = "Not scheduled yet"
        cards.append(
            ClassroomItem(
                id=assignment.id or 0,
                title=f"{subject.name} - {classroom.name}-{section.name}",
                subject=subject.name,
                className=f"{classroom.name}-{section.name}",
                teacher=teacher_user.full_name,
                nextLesson=next_lesson,
                students=strengths.get(section.id, 0),  # type: ignore[arg-type]
            )
        )
    return cards


def lesson_detail(session: Session, user: User) -> LessonDetail:
    """The lesson for the first class the person teaches, from real rows."""
    rows = _teaching_rows(session, user)
    if not rows:
        # Nobody has been assigned to this person (or the school has no
        # assignments yet): an empty lesson beats an invented one.
        return LessonDetail(
            id=0,
            title="No lesson scheduled",
            subject="",
            className="",
            duration="",
            topics=[],
            resources=[],
            homework="No homework set yet",
        )

    _, classroom, section, subject, _ = rows[0]
    period = _next_period(session, section.id, subject.id)  # type: ignore[arg-type]
    homework = _latest_homework(session, section.id, subject.id)  # type: ignore[arg-type]
    sources = list(
        session.exec(
            select(ExamSource).where(
                ExamSource.classroom_id == classroom.id,
                ExamSource.subject_id == subject.id,
            )
        ).all()
    )

    # The chapters of the class's own library sources become the topic list.
    topics: list[str] = []
    for source in sources:
        for chapter in source.chapters or []:
            if chapter not in topics:
                topics.append(chapter)

    duration = ""
    if period is not None:
        minutes = (
            period.end_time.hour * 60
            + period.end_time.minute
            - period.start_time.hour * 60
            - period.start_time.minute
        )
        if minutes > 0:
            duration = f"{minutes} min"

    return LessonDetail(
        id=section.id or 0,
        title=f"{subject.name} - {classroom.name}-{section.name}",
        subject=subject.name,
        className=f"{classroom.name}-{section.name}",
        duration=duration,
        topics=topics[:6],
        resources=[
            LessonResource(
                id=source.id or 0,
                type=RESOURCE_LABELS.get(source.source_type.value, "Resource"),
                title=source.title,
            )
            for source in sources[:4]
        ],
        homework=homework.title if homework is not None else "No homework set yet",
    )
