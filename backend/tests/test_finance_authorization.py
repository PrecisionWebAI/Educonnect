from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.core.db import get_session
from app.domains.academics.models import GradeClass
from app.domains.auth.dependencies import get_current_active_user
from app.domains.students.models import StudentParentRelationship, StudentProfile
from app.domains.teachers.models import TeacherProfile
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


def test_finance_authorization(db_session: Session):
    # Setup mock users
    u_admin = User(
        id=1,
        email="admin@test.com",
        full_name="Admin",
        role=RoleEnum.admin,
        hashed_password="pw",
        is_active=True,
    )
    u_teacher1 = User(
        id=2,
        email="t1@test.com",
        full_name="Teacher 1",
        role=RoleEnum.teacher,
        hashed_password="pw",
        is_active=True,
    )
    u_teacher2 = User(
        id=3,
        email="t2@test.com",
        full_name="Teacher 2",
        role=RoleEnum.teacher,
        hashed_password="pw",
        is_active=True,
    )
    u_student1 = User(
        id=4,
        email="s1@test.com",
        full_name="Student 1",
        role=RoleEnum.student,
        hashed_password="pw",
        is_active=True,
    )
    u_student2 = User(
        id=5,
        email="s2@test.com",
        full_name="Student 2",
        role=RoleEnum.student,
        hashed_password="pw",
        is_active=True,
    )
    u_parent1 = User(
        id=6,
        email="p1@test.com",
        full_name="Parent 1",
        role=RoleEnum.guardian,
        hashed_password="pw",
        is_active=True,
    )

    db_session.add_all(
        [u_admin, u_teacher1, u_teacher2, u_student1, u_student2, u_parent1]
    )
    db_session.commit()

    gc = GradeClass(id=1, name="Class 9-A", level=9)
    db_session.add(gc)
    db_session.commit()

    tp1 = TeacherProfile(
        id=1,
        user_id=u_teacher1.id,
        department="Math",
        qualification="B.Sc",
        joining_date=date(2020, 1, 1),
    )
    tp2 = TeacherProfile(
        id=2,
        user_id=u_teacher2.id,
        department="Science",
        qualification="M.Sc",
        joining_date=date(2021, 1, 1),
    )
    db_session.add_all([tp1, tp2])
    db_session.commit()

    sp1 = StudentProfile(
        id=1,
        user_id=u_student1.id,
        admission_number="ADM-100",
        date_of_birth=date(2011, 1, 1),
        guardian_name="Parent 1",
        grade_class_id=gc.id,
    )
    sp2 = StudentProfile(
        id=2,
        user_id=u_student2.id,
        admission_number="ADM-101",
        date_of_birth=date(2011, 2, 1),
        guardian_name="Other Parent",
        grade_class_id=gc.id,
    )
    db_session.add_all([sp1, sp2])
    db_session.commit()

    # Parent 1 is guardian of Student 1
    rel = StudentParentRelationship(
        id=1, student_id=sp1.id, parent_user_id=u_parent1.id, relationship_type="Father"
    )
    db_session.add(rel)
    db_session.commit()

    app.dependency_overrides[get_session] = lambda: db_session
    client = TestClient(app)

    # 1. Student1 accesses their own dues -> 200
    app.dependency_overrides[get_current_active_user] = lambda: u_student1
    res = client.get(f"/finance/students/{sp1.id}/dues")
    assert res.status_code == 200

    # 2. Student1 accesses Student2's dues -> 403
    res = client.get(f"/finance/students/{sp2.id}/dues")
    assert res.status_code == 403

    # 3. Parent1 accesses Student1's dues -> 200
    app.dependency_overrides[get_current_active_user] = lambda: u_parent1
    res = client.get(f"/finance/students/{sp1.id}/dues")
    assert res.status_code == 200

    # 4. Parent1 accesses Student2's dues -> 403
    res = client.get(f"/finance/students/{sp2.id}/dues")
    assert res.status_code == 403

    # 5. Teacher1 accesses Student1's dues -> 403 (teachers have no fee access)
    app.dependency_overrides[get_current_active_user] = lambda: u_teacher1
    res = client.get(f"/finance/students/{sp1.id}/dues")
    assert res.status_code == 403

    # 6. Admin accesses Student1's dues -> 200
    app.dependency_overrides[get_current_active_user] = lambda: u_admin
    res = client.get(f"/finance/students/{sp1.id}/dues")
    assert res.status_code == 200

    # Payroll Tests
    # 7. Teacher1 accesses own payroll -> 200
    app.dependency_overrides[get_current_active_user] = lambda: u_teacher1
    res = client.get(f"/finance/payroll?teacher_id={tp1.id}")
    assert res.status_code == 200

    # 8. Teacher1 accesses Teacher2's payroll -> 403
    res = client.get(f"/finance/payroll?teacher_id={tp2.id}")
    assert res.status_code == 403

    # 9. Admin accesses Teacher2's payroll -> 200
    app.dependency_overrides[get_current_active_user] = lambda: u_admin
    res = client.get(f"/finance/payroll?teacher_id={tp2.id}")
    assert res.status_code == 200

    app.dependency_overrides.clear()
