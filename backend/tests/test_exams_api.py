from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.core.db import get_session
from app.domains.academics.models import GradeClass, Subject
from app.domains.auth.dependencies import get_current_active_user
from app.domains.exams.models import (
    ExamPaper,
    ExamPaperStatus,
    ExamTerm,
)
from app.domains.students.models import StudentProfile
from app.domains.teachers.models import (
    ClassTeacherAssignment,
    TeacherAssignment,
    TeacherProfile,
)
from app.domains.users.models import RoleEnum, User
from app.main import app


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


def test_approve_and_publish_api_endpoints(db_session: Session):
    # Create Users
    u_st = User(
        id=1,
        email="st@test.com",
        full_name="Subject Teacher",
        role=RoleEnum.teacher,
        hashed_password="pw",
        is_active=True,
    )
    u_ct = User(
        id=2,
        email="ct@test.com",
        full_name="Class Teacher",
        role=RoleEnum.teacher,
        hashed_password="pw",
        is_active=True,
    )
    u_principal = User(
        id=3,
        email="principal@test.com",
        full_name="Principal",
        role=RoleEnum.principal,
        hashed_password="pw",
        is_active=True,
    )
    db_session.add_all([u_st, u_ct, u_principal])
    db_session.commit()

    # Create Profiles
    tp_st = TeacherProfile(
        id=1,
        user_id=u_st.id,
        department="Science",
        qualification="B.Sc",
        joining_date=date(2020, 1, 1),
    )
    tp_ct = TeacherProfile(
        id=2,
        user_id=u_ct.id,
        department="Math",
        qualification="M.Sc",
        joining_date=date(2020, 1, 1),
    )
    db_session.add_all([tp_st, tp_ct])
    db_session.commit()

    # Create Class & Subject
    gc = GradeClass(id=1, name="Class 9-A", level=9)
    sub = Subject(id=1, name="Science", code="SCI101")
    db_session.add_all([gc, sub])
    db_session.commit()

    # Assignments: u_ct is Class Teacher, u_st is Subject Teacher
    cta = ClassTeacherAssignment(id=1, teacher_id=tp_ct.id, grade_class_id=gc.id)
    sta = TeacherAssignment(
        id=1, teacher_id=tp_st.id, grade_class_id=gc.id, subject_id=sub.id
    )
    db_session.add_all([cta, sta])
    db_session.commit()

    # Student
    sp = StudentProfile(
        id=1,
        user_id=10,
        admission_number="ADM-100",
        date_of_birth=date(2011, 1, 1),
        guardian_name="Guardian",
        grade_class_id=gc.id,
    )
    db_session.add(sp)
    db_session.commit()

    # Exam Term & Paper
    term = ExamTerm(
        id=1,
        name="Midterm",
        grade_class_id=gc.id,
        start_date=date(2026, 9, 1),
        end_date=date(2026, 9, 10),
    )
    paper = ExamPaper(
        id=1,
        exam_term_id=term.id,
        subject_id=sub.id,
        status=ExamPaperStatus.approved,
        content_json={},
    )
    db_session.add_all([term, paper])
    db_session.commit()

    app.dependency_overrides[get_session] = lambda: db_session

    client = TestClient(app)

    # 1. Subject teacher uploads marks
    app.dependency_overrides[get_current_active_user] = lambda: u_st
    upload_res = client.post(
        "/exams/results/bulk",
        json={
            "exam_paper_id": paper.id,
            "results": [{"student_id": sp.id, "marks_obtained": 85.0}],
        },
    )
    assert upload_res.status_code == 201
    assert upload_res.json()[0]["status"] == "entered"

    # 2. Subject teacher attempts to approve -> 403 Forbidden (not class teacher)
    app.dependency_overrides[get_current_active_user] = lambda: u_st
    approve_fail = client.patch(f"/exams/results/paper/{paper.id}/approve")
    assert approve_fail.status_code == 403
    assert "not authorized to approve" in approve_fail.json()["detail"].lower()

    # 3. Class teacher approves -> 200 OK
    app.dependency_overrides[get_current_active_user] = lambda: u_ct
    approve_ok = client.patch(f"/exams/results/paper/{paper.id}/approve")
    assert approve_ok.status_code == 200
    assert approve_ok.json()[0]["status"] == "approved"
    assert approve_ok.json()[0]["approved_by_id"] == u_ct.id

    # 4. Class teacher attempts to publish -> 403 Forbidden (no marks.publish)
    app.dependency_overrides[get_current_active_user] = lambda: u_ct
    publish_fail = client.patch(f"/exams/results/paper/{paper.id}/publish")
    assert publish_fail.status_code == 403

    # 5. Principal publishes -> 200 OK
    app.dependency_overrides[get_current_active_user] = lambda: u_principal
    publish_ok = client.patch(f"/exams/results/paper/{paper.id}/publish")
    assert publish_ok.status_code == 200
    assert publish_ok.json()[0]["status"] == "published"
    assert publish_ok.json()[0]["published_by_id"] == u_principal.id

    # 6. Read paper results as assigned subject teacher -> 200 OK
    app.dependency_overrides[get_current_active_user] = lambda: u_st
    paper_res = client.get(f"/exams/results/paper/{paper.id}")
    assert paper_res.status_code == 200
    assert len(paper_res.json()) == 1

    # 7. Read paper results as unassigned teacher -> 403 Forbidden
    u_other = User(
        id=4,
        email="other@test.com",
        full_name="Other Teacher",
        role=RoleEnum.teacher,
        hashed_password="pw",
        is_active=True,
    )
    db_session.add(u_other)
    db_session.commit()
    tp_other = TeacherProfile(
        id=3,
        user_id=u_other.id,
        department="Arts",
        qualification="B.A",
        joining_date=date(2022, 1, 1),
    )
    db_session.add(tp_other)
    db_session.commit()

    app.dependency_overrides[get_current_active_user] = lambda: u_other
    paper_fail = client.get(f"/exams/results/paper/{paper.id}")
    assert paper_fail.status_code == 403

    # 8. Student view marks: own marks allowed, other student forbidden
    u_student = User(
        id=10,
        email="student@test.com",
        full_name="Student",
        role=RoleEnum.student,
        hashed_password="pw",
        is_active=True,
    )
    u_student2 = User(
        id=11,
        email="student2@test.com",
        full_name="Student 2",
        role=RoleEnum.student,
        hashed_password="pw",
        is_active=True,
    )
    db_session.add_all([u_student, u_student2])
    db_session.commit()

    sp2 = StudentProfile(
        id=2,
        user_id=u_student2.id,
        admission_number="ADM-101",
        date_of_birth=date(2011, 2, 1),
        guardian_name="Guardian 2",
        grade_class_id=gc.id,
    )
    db_session.add(sp2)
    db_session.commit()

    # Own marks -> 200 OK
    app.dependency_overrides[get_current_active_user] = lambda: u_student
    student_ok = client.get(f"/exams/results/student/{sp.id}")
    assert student_ok.status_code == 200
    assert len(student_ok.json()) == 1

    # Other student's marks -> 403 Forbidden
    student_fail = client.get(f"/exams/results/student/{sp2.id}")
    assert student_fail.status_code == 403

    # Clear overrides
    app.dependency_overrides.clear()
