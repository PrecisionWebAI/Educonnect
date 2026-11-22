"""Phase 7 - the exam: date sheet, marks, publication, results, ranks and the reminder.

The audit found the marks side of a classroom had nowhere to live: `marks` was a float
with its maximum stored per exam in the old per-exam table, an absent child had to be given a zero,
and a published mark could be changed with no trace at all. These scenarios pin the
replacement (`exam` + `exam_paper` + `marks` + `marks_audit` + `grade_scale`):

1. **who may plan what** - a teacher plans and marks only the subject they hold; the
   office plans anything; another school's exam is a `404`, never a `403`;
2. **a mark cannot lie** - more than the paper's maximum is refused, a student of
   another class is refused, and `exam_paper.max_marks` is the only maximum in play;
3. **unpublished means invisible** - a family gets no result until the paper is
   published, and then sees **only** its own child;
4. **ranks are competition ranks** - `1, 2, 2, 4` for a tie, and an absent child is not
   ranked at all (an absence is not a zero);
5. **publication is a promise** - after it, a change goes through `change_mark`, writes
   `marks_audit` (old value, new value, who) and tells the family once;
6. **the reminder fires once** per paper, only for a `scheduled` exam, the day before.

Runs under pytest and as `python tests/test_classroom_exams.py`.
"""

import importlib
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.core.schema import MODEL_MODULES
from app.domains.academic.classroom import service as classroom_service
from app.domains.academic.classroom.academics.models import (
    ClassName,
    Section,
    SubjectTeacher,
)
from app.domains.academic.classroom.academics.repository import ensure_room
from app.domains.academic.classroom.exams.models import (
    Exam,
    GradeScale,
    Mark,
    MarksAudit,
)
from app.domains.academic.classroom.exams.plan import grades, service
from app.domains.academic.classroom.exams.plan.schemas import (
    ExamCreateIn,
    ExamUpdateIn,
    MarkChangeIn,
    MarkEntryIn,
    MarksSaveIn,
    PaperScheduleIn,
)
from app.domains.academic.classroom.schemas import SectionMarkEntryIn, SectionMarksSave
from app.domains.academic.classroom.students import service as student_service
from app.domains.academic.classroom.students.models import (
    Guardian,
    Student,
    StudentGuardianRelationship,
)
from app.domains.academic.classroom.students.schemas import StudentCreate
from app.domains.admin.platform.models import School
from app.domains.admin.settings import values as setting_values
from app.domains.admin.settings.models import AcademicYear
from app.domains.admin.users.models import User
from app.domains.auth.models import Permission, Role, RolePermission, UserRole
from app.domains.main.notifications.models import Notification
from app.domains.people.staff.models import Employee
from tests.course_support import section_subject

TODAY = date(2026, 11, 16)
TOMORROW = TODAY + timedelta(days=1)


def memory_session() -> Session:
    for domain in MODEL_MODULES:
        importlib.import_module(f"app.domains.{domain}.models")
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def _school(session: Session, name: str, code: str) -> School:
    school = School(name=name, code=code, email=f"{code}@test")
    session.add(school)
    session.commit()
    session.refresh(school)
    session.info["school_id"] = school.id
    return school


def _user(session: Session, email: str) -> User:
    user = User(email=email, full_name=email.split("@")[0], hashed_password="pw")
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def _role(session: Session, codename: str) -> Role:
    role = session.exec(select(Role).where(Role.codename == codename)).first()
    if role is None:
        role = Role(codename=codename, label=codename.title())
        session.add(role)
        session.commit()
        session.refresh(role)
    return role


def _grant(session: Session, role: Role, codename: str) -> None:
    """Give a role one permission, the way the seed does (row, not a shortcut)."""
    permission = session.exec(
        select(Permission).where(Permission.codename == codename)
    ).first()
    if permission is None:
        permission = Permission(codename=codename, category="Marks", label=codename)
        session.add(permission)
        session.commit()
        session.refresh(permission)
    session.add(RolePermission(role_id=role.id, permission_id=permission.id))
    session.commit()


def _office(session: Session, email: str = "office@test") -> User:
    """A login that really holds `marks.update` + `classes.update` (role + grants)."""
    role = _role(session, "school_admin")
    _grant(session, role, "marks.update")
    _grant(session, role, "classes.update")
    _grant(session, role, "marks.read")
    user = _user(session, email)
    session.add(UserRole(user_id=user.id, role_id=role.id))
    session.commit()
    return user


def _room(session: Session, class_name: str, section_name: str, level: int):
    klass = session.exec(
        select(ClassName).where(ClassName.classname == class_name)
    ).first()
    if klass is None:
        klass = ClassName(classname=class_name, level=level)
        session.add(klass)
        session.commit()
        session.refresh(klass)
    section = session.exec(
        select(Section).where(Section.section_name == section_name)
    ).first()
    if section is None:
        section = Section(section_name=section_name)
        session.add(section)
        session.commit()
        session.refresh(section)
    return ensure_room(session, klass.class_id, section.section_id)


def _student(session: Session, name: str, number: str, room) -> Student:
    return student_service.create_student(
        session,
        StudentCreate(
            full_name=name,
            gender="Female",
            admission_number=number,
            classroom_id=room.id,
        ),
    )


def _family(session: Session, student: Student, email: str) -> User:
    """A parent login linked to this child (one guardian row, one relationship)."""
    parent = _user(session, email)
    guardian = Guardian(
        name=email.split("@")[0],
        phone=f"90{uuid4().int % 100000000:08d}",
        user_id=parent.id,
    )
    session.add(guardian)
    session.commit()
    session.refresh(guardian)
    session.add(
        StudentGuardianRelationship(
            student_id=student.id, guardian_id=guardian.id, is_primary=True
        )
    )
    session.commit()
    return parent


def _teacher(session: Session, email: str, code: str) -> tuple[Employee, User]:
    user = _user(session, email)
    employee = Employee(
        user_id=user.id,
        employee_code=code,
        department="Science",
        joining_date=date(2024, 6, 1),
    )
    session.add(employee)
    session.commit()
    session.refresh(employee)
    return employee, user


def seed(session: Session) -> dict:
    """One school: Class 9-A (4 children, 2 families), Class 9-B, Maths + Science.

    The Maths teacher is Meera - the only person who may plan or mark a Maths paper in
    9-A. The principal holds the role, not a permission, so `_is_leadership` is what
    lets her see the school's results.
    """
    school = _school(session, "phase seven school", "p7s")
    session.add(
        AcademicYear(
            name="2026-27",
            start_date=date(2026, 6, 1),
            end_date=date(2027, 4, 30),
            is_current=True,
        )
    )
    session.commit()

    room = _room(session, "Class 9", "A", 9)
    other_room = _room(session, "Class 9", "B", 9)

    # The section's own subjects. 9-B has the same names: a subject is never shared.
    maths = section_subject(session, room.id, "Mathematics", code="MATH")
    science = section_subject(session, room.id, "Science", code="SCI")
    section_subject(session, other_room.id, "Mathematics", code="MATH")

    employee, meera = _teacher(session, "meera@test", "EMP-P7-1")
    room.class_teacher_id = employee.id
    session.add(room)
    session.add(
        SubjectTeacher(
            classroom_id=room.id,
            classroom_subject_id=maths.id,
            teacher_id=employee.id,
            effective_from=date(2026, 6, 1),
        )
    )
    session.commit()

    aarav = _student(session, "aarav sharma", "P7-1", room)
    kabir = _student(session, "kabir singh", "P7-2", room)
    ishaan = _student(session, "ishaan rao", "P7-3", room)
    dev = _student(session, "dev nair", "P7-4", room)

    aarav_parent = _family(session, aarav, "aarav.parent@test")
    kabir_parent = _family(session, kabir, "kabir.parent@test")
    ishaan_parent = _family(session, ishaan, "ishaan.parent@test")
    dev_parent = _family(session, dev, "dev.parent@test")

    office = _office(session)
    principal = _user(session, "principal@test")
    session.add(UserRole(user_id=principal.id, role_id=_role(session, "principal").id))
    session.commit()

    outsider = _user(session, "outsider@test")
    session.add(UserRole(user_id=outsider.id, role_id=_role(session, "teacher").id))
    session.commit()

    # The reminder hour is a setting; midnight keeps the test independent of the clock.
    setting_values.set_value(session, "exam.reminder_time", "00:00")

    return {
        "school": school,
        "room": room,
        "other_room": other_room,
        "maths": maths,
        "science": science,
        "meera": meera,
        "employee": employee,
        "aarav": aarav,
        "kabir": kabir,
        "ishaan": ishaan,
        "dev": dev,
        "aarav_parent": aarav_parent,
        "kabir_parent": kabir_parent,
        "ishaan_parent": ishaan_parent,
        "dev_parent": dev_parent,
        "office": office,
        "principal": principal,
        "outsider": outsider,
    }


# ---------------------------------------------------------------------------
# Helpers - one place that builds the exam the scenarios then poke at
# ---------------------------------------------------------------------------


def _maths_paper(
    data, *, exam_date=TODAY, maximum="80", passing="24"
) -> PaperScheduleIn:
    return PaperScheduleIn(
        classroom_subject_id=data["maths"].id,
        exam_date=exam_date,
        start_time=time(9, 0),
        end_time=time(11, 0),
        max_marks=Decimal(maximum),
        passing_marks=Decimal(passing),
        room="Hall 1",
    )


def _science_paper(data, *, exam_date=TOMORROW, maximum="50") -> PaperScheduleIn:
    return PaperScheduleIn(
        classroom_subject_id=data["science"].id,
        exam_date=exam_date,
        max_marks=Decimal(maximum),
        passing_marks=Decimal("15"),
    )


def _create(
    session, data, *, papers=None, status="scheduled", user=None, scope="class"
):
    return service.create_exam(
        session,
        ExamCreateIn(
            name="Mid-Term 2026",
            term="Term 1",
            exam_type="Mid term",
            scope=scope,
            classroom_id=data["room"].id if scope == "class" else None,
            class_id=data["room"].class_id if scope == "class" else None,
            start_date=TODAY,
            end_date=TODAY + timedelta(days=5),
            status=status,
            papers=papers if papers is not None else [_maths_paper(data)],
        ),
        user or data["office"],
    )


def _paper_of(exam_read, classroom_subject_id) -> object:
    return next(
        paper
        for paper in exam_read.papers
        if paper.classroom_subject_id == classroom_subject_id
    )


def _save(session, data, paper_id, rows, user=None):
    """`rows` is (student, score) pairs; `None` means absent."""
    return service.save_marks(
        session,
        paper_id,
        MarksSaveIn(
            entries=[
                MarkEntryIn(
                    student_id=student.id, marks_obtained=score, absent=score is None
                )
                for student, score in rows
            ]
        ),
        user or data["meera"],
    )


def _publish(session, data, paper_id, user=None):
    return service.publish_paper(session, paper_id, user or data["meera"])


def _row(result, student) -> object:
    return next(row for row in result.rows if row.student_id == student.id)


# ---------------------------------------------------------------------------
# 1. Who may plan and mark what
# ---------------------------------------------------------------------------


def test_a_teacher_plans_and_marks_only_the_subject_they_hold():
    """Meera holds Maths in 9-A: she can plan and mark it, and nothing else."""
    session = memory_session()
    data = seed(session)

    planned = service.create_exam(
        session,
        ExamCreateIn(
            name="Unit Test 3",
            classroom_id=data["room"].id,
            status="scheduled",
            papers=[_maths_paper(data, maximum="25", passing="8")],
        ),
        data["meera"],
    )
    assert [paper.classroom_subject_id for paper in planned.papers] == [data["maths"].id]
    assert planned.papers[0].can_edit is True
    session.info["school_id"] = data["school"].id
    assert planned.status == "scheduled"

    with pytest.raises(HTTPException) as refused:
        service.create_exam(
            session,
            ExamCreateIn(
                name="Unit Test 4",
                classroom_id=data["room"].id,
                papers=[_science_paper(data)],
            ),
            data["meera"],
        )
    assert refused.value.status_code == 403

    # A teacher of no subject in this school cannot plan anything here.
    with pytest.raises(HTTPException) as stranger:
        service.create_exam(
            session,
            ExamCreateIn(
                name="Unit Test 5",
                classroom_id=data["room"].id,
                papers=[_maths_paper(data)],
            ),
            data["outsider"],
        )
    assert stranger.value.status_code == 403

    # The office plans the Science paper; Meera still may not mark it.
    exam = _create(
        session,
        data,
        papers=[_maths_paper(data), _science_paper(data)],
        user=data["office"],
    )
    science = _paper_of(exam, data["science"].id)
    # The office may edit both papers; Meera's own view of the same exam says otherwise.
    assert science.can_edit is True
    meera_view = service.read_exam(session, exam.id, data["meera"])
    assert _paper_of(meera_view, data["maths"].id).can_edit is True
    assert _paper_of(meera_view, data["science"].id).can_edit is False
    with pytest.raises(HTTPException) as not_mine:
        _save(session, data, science.id, [(data["aarav"], Decimal("40"))])
    assert not_mine.value.status_code == 403


def test_a_school_exam_is_the_heads_to_plan_and_covers_each_class():
    """A school-wide exam needs the head; its papers are per class."""
    session = memory_session()
    data = seed(session)
    class_ten = _room(session, "Class 10", "A", 10)
    section_subject(session, class_ten.id, "Mathematics", code="MATH")

    school_exam = service.create_exam(
        session,
        ExamCreateIn(
            name="Annual Exam",
            scope="school",
            class_id=data["room"].class_id,
            status="draft",
            papers=[
                _maths_paper(data),
                PaperScheduleIn(
                    subject_name="Mathematics",
                    class_id=class_ten.class_id,
                    exam_date=TOMORROW,
                    max_marks=Decimal("80"),
                ),
            ],
        ),
        data["principal"],
    )
    assert school_exam.scope == "school"
    assert {paper.class_id for paper in school_exam.papers} == {
        data["room"].class_id,
        class_ten.class_id,
    }

    with pytest.raises(HTTPException) as refused:
        service.create_exam(
            session,
            ExamCreateIn(
                name="Annual Exam 2",
                scope="school",
                class_id=data["room"].class_id,
                papers=[_maths_paper(data)],
            ),
            data["meera"],
        )
    assert refused.value.status_code == 403


# ---------------------------------------------------------------------------
# 2. A mark cannot lie - bounds, class membership, and the paper's maximum
# ---------------------------------------------------------------------------


def test_a_mark_cannot_exceed_the_paper_or_belong_to_another_class():
    session = memory_session()
    data = seed(session)
    exam = _create(session, data, papers=[_maths_paper(data)])
    maths = _paper_of(exam, data["maths"].id)

    with pytest.raises(HTTPException) as too_many:
        _save(session, data, maths.id, [(data["aarav"], Decimal("81"))])
    assert too_many.value.status_code == 422
    assert "out of 80" in too_many.value.detail

    with pytest.raises(HTTPException) as negative:
        _save(session, data, maths.id, [(data["aarav"], Decimal("-1"))])
    assert negative.value.status_code == 422

    # A child of another **section** is not on this paper - only 9-A sits this one.
    stranger_in_9b = _student(session, "nina das", "P7-9", data["other_room"])
    with pytest.raises(HTTPException) as wrong_section:
        _save(session, data, maths.id, [(stranger_in_9b, Decimal("10"))])
    assert wrong_section.value.status_code == 422

    saved = _save(session, data, maths.id, [(data["aarav"], Decimal("72.5"))])
    assert saved.written == 1
    assert saved.exam_status == "marks_entry"
    mark = session.exec(select(Mark).where(Mark.student_id == data["aarav"].id)).one()
    # The paper is the authority: the mark names the paper, never a subject of its own.
    assert mark.exam_paper_id == maths.id
    assert mark.subject_id is None
    assert mark.exam_id == exam.id
    assert float(mark.marks_obtained) == 72.5
    assert mark.grade is None  # a stored grade would be a second truth

    # Saving twice updates the row; it never doubles it.
    _save(session, data, maths.id, [(data["aarav"], Decimal("70"))])
    rows = session.exec(select(Mark).where(Mark.exam_paper_id == maths.id)).all()
    assert len(rows) == 1 and float(rows[0].marks_obtained) == 70.0


def test_an_absence_is_a_fact_of_its_own():
    session = memory_session()
    data = seed(session)
    exam = _create(session, data, papers=[_maths_paper(data)])
    maths = _paper_of(exam, data["maths"].id)

    saved = _save(
        session,
        data,
        maths.id,
        [(data["aarav"], Decimal("72")), (data["dev"], None)],
    )
    assert saved.written == 2 and saved.absent == 1
    absent_mark = session.exec(
        select(Mark).where(Mark.student_id == data["dev"].id)
    ).one()
    assert absent_mark.is_absent is True
    assert absent_mark.marks_obtained is None


# ---------------------------------------------------------------------------
# 3. Unpublished means invisible, published means narrow
# ---------------------------------------------------------------------------


def _two_paper_exam(session, data):
    """Both papers, marks on both, nothing published yet."""
    exam = _create(session, data, papers=[_maths_paper(data), _science_paper(data)])
    maths = _paper_of(exam, data["maths"].id)
    science = _paper_of(exam, data["science"].id)
    _save(
        session,
        data,
        maths.id,
        [
            (data["aarav"], Decimal("72")),
            (data["kabir"], Decimal("72")),
            (data["dev"], Decimal("30")),
        ],
    )
    _save(
        session,
        data,
        science.id,
        [
            (data["aarav"], Decimal("40")),
            (data["kabir"], Decimal("40")),
            (data["dev"], None),
        ],
        user=data["office"],
    )
    return exam, maths, science


def test_an_unpublished_paper_is_invisible_to_a_family_and_the_teacher_sees_it():
    session = memory_session()
    data = seed(session)
    exam, _maths, _science = _two_paper_exam(session, data)

    with pytest.raises(HTTPException) as hidden:
        service.results(session, exam.id, data["aarav_parent"])
    assert hidden.value.status_code == 404

    teacher_view = service.results(session, exam.id, data["meera"])
    assert teacher_view.own_only is False
    assert len(teacher_view.papers) == 2
    # Nobody has published either paper, so the to-do list holds both.
    assert set(teacher_view.unpublished) == {
        paper.paper_id for paper in teacher_view.papers
    }
    assert _row(teacher_view, data["aarav"]).total == Decimal("112")


def test_a_family_sees_only_its_own_child_and_only_published_papers():
    session = memory_session()
    data = seed(session)
    exam, maths, science = _two_paper_exam(session, data)
    _publish(session, data, maths.id)

    family = service.results(session, exam.id, data["aarav_parent"])
    assert family.own_only is True
    assert [row.student_id for row in family.rows] == [data["aarav"].id]
    # Science is not published, so it is not on the family's sheet at all.
    assert [paper.paper_id for paper in family.papers] == [maths.id]
    assert family.unpublished == []
    row = family.rows[0]
    assert row.marks[0].subject == "Mathematics"
    assert float(row.total) == 72.0
    assert row.grade == "A1"  # 90% on the default ladder
    assert row.rank == 1

    # Publishing the second paper widens the family's sheet, still for one child.
    _publish(session, data, science.id, user=data["office"])
    family = service.results(session, exam.id, data["aarav_parent"])
    assert {paper.paper_id for paper in family.papers} == {maths.id, science.id}
    assert [row.student_id for row in family.rows] == [data["aarav"].id]
    assert float(family.rows[0].total) == 112.0


def test_another_schools_exam_is_a_404():
    session = memory_session()
    data = seed(session)
    exam = _create(session, data, papers=[_maths_paper(data)])

    other = _school(session, "another school", "p7other")
    foreign = Exam(name="Their exam", class_id=data["room"].class_id, status="draft")
    session.add(foreign)
    session.commit()
    session.refresh(foreign)
    assert foreign.school_id == other.id

    session.info["school_id"] = data["school"].id
    with pytest.raises(HTTPException) as missing:
        service.read_exam(session, foreign.id, data["office"])
    assert missing.value.status_code == 404
    with pytest.raises(HTTPException) as missing_results:
        service.results(session, foreign.id, data["office"])
    assert missing_results.value.status_code == 404
    # The school's own exam still reads.
    assert service.read_exam(session, exam.id, data["office"]).id == exam.id


# ---------------------------------------------------------------------------
# 4. Ranks: 1, 2, 2, 4 - and a child who sat nothing is not ranked
# ---------------------------------------------------------------------------


def test_ranks_are_competition_ranks_and_an_absence_is_not_ranked():
    session = memory_session()
    data = seed(session)
    exam, maths, science = _two_paper_exam(session, data)
    _publish(session, data, maths.id)
    _publish(session, data, science.id, user=data["office"])

    result = service.results(session, exam.id, data["principal"])
    percent = {row.student_id: float(row.percent or 0) for row in result.rows}
    # aarav and kabir tie on 112/130; dev sat only the Maths paper; ishaan sat nothing.
    assert percent[data["aarav"].id] == percent[data["kabir"].id] == 86.15
    assert _row(result, data["aarav"]).rank == 1
    assert _row(result, data["kabir"]).rank == 1
    assert _row(result, data["dev"]).rank == 3  # the tie took second place away
    assert _row(result, data["ishaan"]).rank is None
    assert _row(result, data["dev"]).absent_count == 1
    # An absent paper is not "out of" anything, so 30/80 is the whole total.
    assert _row(result, data["dev"]).out_of == Decimal("80")

    # The ladder is a setting: a school that turns ranks off gets no numbers.
    setting_values.set_value(session, "exam.rank_display", "off")
    off = service.results(session, exam.id, data["principal"])
    assert all(row.rank is None for row in off.rows)
    assert off.rank_display == "off"

    # A school's own ladder wins over the default one - and it replaces it wholly, so a
    # ladder without a floor row leaves the lowest child ungraded until the school adds one.
    setting_values.set_value(session, "exam.rank_display", "section")
    session.add_all(
        [
            GradeScale(min_percent=Decimal("85"), grade="DIST"),
            GradeScale(min_percent=Decimal("0"), grade="E"),
        ]
    )
    session.commit()
    ladder_result = service.results(session, exam.id, data["principal"])
    assert _row(ladder_result, data["aarav"]).grade == "DIST"
    assert _row(ladder_result, data["dev"]).grade == "E"


def test_competition_ranks_skip_and_ties_share():
    session = memory_session()
    seed(session)
    scores = {uuid4(): Decimal("92"), uuid4(): Decimal("92"), uuid4(): Decimal("80")}
    ids = list(scores)
    ranks = grades.competition_ranks(scores)
    assert [ranks[key] for key in ids] == [1, 1, 3]
    assert grades.grade_for(session, Decimal("90")) == "A1"
    assert grades.grade_for(session, Decimal("89.99")) == "A2"
    assert grades.grade_for(session, None) is None


# ---------------------------------------------------------------------------
# 5. Publication is a promise: no silent overwrite, an audit row, one message
# ---------------------------------------------------------------------------


def test_a_published_mark_cannot_be_overwritten_as_a_draft():
    session = memory_session()
    data = seed(session)
    exam, maths, _science = _two_paper_exam(session, data)
    _publish(session, data, maths.id)

    with pytest.raises(HTTPException) as closed:
        _save(session, data, maths.id, [(data["aarav"], Decimal("10"))])
    assert closed.value.status_code == 409
    assert "audited" in closed.value.detail

    # Changing a mark before publication is refused too - the draft save is the path.
    science = _paper_of(
        service.read_exam(session, exam.id, data["office"]), data["science"].id
    )
    with pytest.raises(HTTPException) as not_published:
        service.change_mark(
            session,
            science.id,
            data["aarav"].id,
            MarkChangeIn(marks_obtained=Decimal("45")),
            data["office"],
        )
    assert not_published.value.status_code == 409


def test_a_change_after_publication_is_audited_and_told_once():
    session = memory_session()
    data = seed(session)
    _exam, maths, _science = _two_paper_exam(session, data)
    _publish(session, data, maths.id)

    row = service.change_mark(
        session,
        maths.id,
        data["kabir"].id,
        MarkChangeIn(marks_obtained=Decimal("60"), reason="re-totalled"),
        data["office"],
    )
    assert float(row.marks_obtained) == 60.0
    assert row.changed_after_publish is True

    audit = session.exec(select(MarksAudit)).one()
    assert float(audit.old_value) == 72.0
    assert float(audit.new_value) == 60.0
    assert audit.changed_by_user_id == data["office"].id
    assert audit.reason == "re-totalled"

    def messages() -> int:
        return len(
            session.exec(
                select(Notification).where(
                    Notification.event_type == "exam.mark_changed",
                    Notification.user_id == data["kabir_parent"].id,
                )
            ).all()
        )

    assert messages() == 1

    # The same value twice is refused (it is on file), so no second message.
    with pytest.raises(HTTPException) as same:
        service.change_mark(
            session,
            maths.id,
            data["kabir"].id,
            MarkChangeIn(marks_obtained=Decimal("60")),
            data["office"],
        )
    assert same.value.status_code == 409
    assert messages() == 1

    # A second, real change rings again - the dedupe key carries the revision.
    service.change_mark(
        session,
        maths.id,
        data["kabir"].id,
        MarkChangeIn(marks_obtained=Decimal("64")),
        data["office"],
    )
    assert messages() == 2


def test_publishing_twice_is_refused():
    session = memory_session()
    data = seed(session)
    _exam, maths, _science = _two_paper_exam(session, data)
    _publish(session, data, maths.id)
    with pytest.raises(HTTPException) as twice:
        _publish(session, data, maths.id)
    assert twice.value.status_code == 409


# ---------------------------------------------------------------------------
# 6. The reminder, and one message per family per event
# ---------------------------------------------------------------------------


def test_the_reminder_fires_once_and_only_for_a_scheduled_exam():
    session = memory_session()
    data = seed(session)
    # The job asks about **today's** tomorrow, so the paper must be dated that way.
    real_tomorrow = datetime.utcnow().date() + timedelta(days=1)
    _create(session, data, papers=[_maths_paper(data, exam_date=real_tomorrow)])
    assert (
        session.exec(
            select(Notification).where(Notification.event_type == "exam.reminder")
        ).all()
        == []
    )

    assert service.reminder_job(session) >= 1
    told = session.exec(
        select(Notification).where(
            Notification.event_type == "exam.reminder",
            Notification.user_id == data["aarav_parent"].id,
        )
    ).all()
    assert len(told) == 1
    assert "tomorrow" in told[0].title.lower()

    # The scheduler ticks every minute; the second tick must not repeat itself.
    assert service.reminder_job(session) == 0

    # A draft exam's paper is nobody's business yet: no reminder.
    draft = _create(
        session,
        data,
        papers=[_science_paper(data, exam_date=real_tomorrow)],
        status="draft",
    )
    assert draft.status == "draft"
    assert service.reminder_job(session) == 0


def test_the_date_sheet_is_announced_once_per_family_and_again_when_it_moves():
    session = memory_session()
    data = seed(session)
    exam = _create(session, data, papers=[_maths_paper(data)])

    def count(event: str) -> int:
        return len(
            session.exec(
                select(Notification).where(
                    Notification.event_type == event,
                    Notification.user_id == data["aarav_parent"].id,
                )
            ).all()
        )

    assert count("exam.scheduled") == 1
    # Re-announcing the same event writes nothing (dedupe), even from a second call.
    service._announce(
        session, session.get(Exam, exam.id), event="exam.scheduled", changed=False
    )
    assert count("exam.scheduled") == 1

    # Moving the date is a new event, and the family hears about it once.
    service.update_exam(
        session,
        exam.id,
        ExamUpdateIn(
            start_date=TOMORROW, papers=[_maths_paper(data, exam_date=TOMORROW)]
        ),
        data["office"],
    )
    assert count("exam.changed") == 1

    # A note does not move the date sheet, so it is not news.
    service.update_exam(
        session, exam.id, ExamUpdateIn(note="Hall changed"), data["office"]
    )
    assert count("exam.changed") == 1


# ---------------------------------------------------------------------------
# 7. One writer: the older Academics save goes through the paper
# ---------------------------------------------------------------------------


def test_the_old_academics_save_writes_through_the_paper():
    session = memory_session()
    data = seed(session)
    # An exam with no paper for Science: there is nothing to be marked against.
    exam = _create(session, data, papers=[_maths_paper(data)])
    payload = SectionMarksSave(
        exam_id=exam.id,
        entries=[
            SectionMarkEntryIn(
                student_id=data["aarav"].id,
                classroom_subject_id=data["science"].id,
                marks_obtained=Decimal("30"),
            )
        ],
    )
    with pytest.raises(HTTPException) as no_paper:
        classroom_service.save_section_marks(
            session, data["room"].id, payload, data["office"]
        )
    assert no_paper.value.status_code == 422

    # With the paper in place the same call writes one row, with the paper attached.
    maths = _paper_of(exam, data["maths"].id)
    payload = SectionMarksSave(
        exam_id=exam.id,
        entries=[
            SectionMarkEntryIn(
                student_id=data["aarav"].id,
                classroom_subject_id=data["maths"].id,
                marks_obtained=Decimal("64"),
            )
        ],
    )
    assert (
        classroom_service.save_section_marks(
            session, data["room"].id, payload, data["office"]
        )
        == 1
    )
    mark = session.exec(select(Mark).where(Mark.student_id == data["aarav"].id)).one()
    assert mark.exam_paper_id == maths.id
    assert float(mark.marks_obtained) == 64.0
