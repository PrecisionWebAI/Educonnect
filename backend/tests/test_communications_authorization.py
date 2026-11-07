from datetime import date

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.domains.academics.models import Classroom, Section, Subject, SubjectTeacher
from app.domains.chat.schemas import ChatThreadCreate
from app.domains.chat.service import create_thread, get_authorized_contact_user_ids
from app.domains.students.models import StudentGuardianRelationship, Student
from app.domains.staff.models import Employee
from app.domains.users.models import RoleEnum, User


@pytest.fixture(name="db_session")
def db_session_fixture():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def setup_mock_school(db_session: Session):
    # Admin
    u_admin = User(
        email="admin@test.com",
        role=RoleEnum.admin,
        full_name="Admin",
        is_active=True,
        hashed_password="pw",
    )
    # Teachers
    u_t_math = User(
        email="t_math@test.com",
        role=RoleEnum.teacher,
        full_name="Math Teacher",
        is_active=True,
        hashed_password="pw",
    )
    u_t_sci = User(
        email="t_sci@test.com",
        role=RoleEnum.teacher,
        full_name="Sci Teacher",
        is_active=True,
        hashed_password="pw",
    )
    u_t_other = User(
        email="t_other@test.com",
        role=RoleEnum.teacher,
        full_name="Other Teacher",
        is_active=True,
        hashed_password="pw",
    )
    # Students
    u_s1 = User(
        email="s1@test.com",
        role=RoleEnum.student,
        full_name="Student 1",
        is_active=True,
        hashed_password="pw",
    )
    u_s2 = User(
        email="s2@test.com",
        role=RoleEnum.student,
        full_name="Student 2",
        is_active=True,
        hashed_password="pw",
    )
    # Parents
    u_p1 = User(
        email="p1@test.com",
        role=RoleEnum.guardian,
        full_name="Parent 1",
        is_active=True,
        hashed_password="pw",
    )
    u_p2 = User(
        email="p2@test.com",
        role=RoleEnum.guardian,
        full_name="Parent 2",
        is_active=True,
        hashed_password="pw",
    )

    db_session.add_all([u_admin, u_t_math, u_t_sci, u_t_other, u_s1, u_s2, u_p1, u_p2])
    db_session.commit()

    gc1 = Classroom(name="Class A", level=1)
    gc2 = Classroom(name="Class B", level=1)
    db_session.add_all([gc1, gc2])
    db_session.commit()

    tp_math = Employee(
        user_id=u_t_math.id,
        employee_code="EMP-0001",
        department="Math",
        qualification="B.Ed",
        joining_date=date(2020, 1, 1),
    )
    tp_sci = Employee(
        user_id=u_t_sci.id,
        employee_code="EMP-0002",
        department="Science",
        qualification="B.Ed",
        joining_date=date(2020, 1, 1),
    )
    tp_other = Employee(
        user_id=u_t_other.id,
        employee_code="EMP-0003",
        department="Art",
        qualification="B.Ed",
        joining_date=date(2020, 1, 1),
    )
    db_session.add_all([tp_math, tp_sci, tp_other])
    db_session.commit()

    sub = Subject(name="Math", code="M1")
    db_session.add(sub)
    db_session.commit()

    # Math Teacher runs Class A's section; Sci Teacher takes Math in that section.
    section = Section(name="A", classroom_id=gc1.id)
    db_session.add(section)
    db_session.commit()
    section.class_teacher_id = tp_math.id
    db_session.add(section)
    db_session.add(
        SubjectTeacher(section_id=section.id, subject_id=sub.id, teacher_id=tp_sci.id)
    )
    db_session.commit()

    # Student 1 in Class A, Student 2 in Class B
    sp1 = Student(
        user_id=u_s1.id,
        admission_number="A1",
        date_of_birth=date(2010, 1, 1),
        classroom_id=gc1.id,
    )
    sp2 = Student(
        user_id=u_s2.id,
        admission_number="A2",
        date_of_birth=date(2010, 1, 1),
        classroom_id=gc2.id,
    )
    db_session.add_all([sp1, sp2])
    db_session.commit()

    # Parent relationships
    rel1 = StudentGuardianRelationship(
        student_id=sp1.id, parent_user_id=u_p1.id, relationship_type="Father"
    )
    rel2 = StudentGuardianRelationship(
        student_id=sp2.id, parent_user_id=u_p2.id, relationship_type="Mother"
    )
    db_session.add_all([rel1, rel2])
    db_session.commit()

    return {
        "admin": u_admin,
        "t_math": u_t_math,
        "t_sci": u_t_sci,
        "t_other": u_t_other,
        "p1": u_p1,
        "p2": u_p2,
        "s1": u_s1,
        "s2": u_s2,
    }


def test_admin_chat_contacts(db_session: Session):
    users = setup_mock_school(db_session)
    admin = users["admin"]

    allowed = get_authorized_contact_user_ids(db_session, admin)
    assert allowed is None  # Admins can talk to anyone


def test_teacher_chat_contacts(db_session: Session):
    users = setup_mock_school(db_session)
    t_math = users["t_math"]

    allowed = get_authorized_contact_user_ids(db_session, t_math)
    assert allowed is not None
    assert users["admin"].id in allowed
    assert users["t_sci"].id in allowed  # Can talk to other teachers
    assert users["t_other"].id in allowed

    # Can talk to assigned student (s1) and parent (p1)
    assert users["s1"].id in allowed
    assert users["p1"].id in allowed

    # Cannot talk to unassigned student (s2) and parent (p2)
    assert users["s2"].id not in allowed
    assert users["p2"].id not in allowed


def test_parent_chat_contacts(db_session: Session):
    users = setup_mock_school(db_session)
    p1 = users["p1"]

    allowed = get_authorized_contact_user_ids(db_session, p1)
    assert allowed is not None
    assert users["admin"].id in allowed

    # Can talk to assigned teachers (math and sci)
    assert users["t_math"].id in allowed
    assert users["t_sci"].id in allowed

    # Cannot talk to unassigned teacher
    assert users["t_other"].id not in allowed

    # Cannot talk to other parents or students (except maybe own child? currently logic blocks all students/parents in get_chat_contacts though)
    assert users["p2"].id not in allowed


def test_create_thread_validation(db_session: Session):
    from fastapi import HTTPException

    users = setup_mock_school(db_session)

    t_math = users["t_math"]
    p2 = users["p2"]  # Unassigned parent

    thread_in = ChatThreadCreate(is_group=False, participant_user_ids=[p2.id])

    with pytest.raises(HTTPException) as excinfo:
        create_thread(db_session, thread_in, t_math.id)

    assert excinfo.value.status_code == 403
    assert "Not authorized" in str(excinfo.value.detail)

    # Valid thread
    p1 = users["p1"]
    thread_in_valid = ChatThreadCreate(is_group=False, participant_user_ids=[p1.id])
    thread = create_thread(db_session, thread_in_valid, t_math.id)
    assert thread is not None
