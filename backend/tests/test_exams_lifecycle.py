from datetime import date

import pytest
from fastapi import HTTPException
from sqlmodel import Session, SQLModel, create_engine

from app.domains.academics.models import GradeClass, Subject
from app.domains.auth.service import AuthorizationService
from app.domains.exams import service as exam_service
from app.domains.exams.models import (
    ExamPaper,
    ExamPaperStatus,
    ExamTerm,
    ResultStatus,
)
from app.domains.exams.schemas import BulkExamResultCreate
from app.domains.students.models import StudentParentRelationship, StudentProfile
from app.domains.teachers.models import (
    ClassTeacherAssignment,
    TeacherAssignment,
    TeacherProfile,
)
from app.domains.users.models import RoleEnum, User


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_marks_approve_and_publish_base_permissions():
    teacher = User(
        id=1,
        email="teacher@test.com",
        full_name="Teacher",
        role=RoleEnum.teacher,
        hashed_password="pw",
    )
    principal = User(
        id=2,
        email="principal@test.com",
        full_name="Principal",
        role=RoleEnum.principal,
        hashed_password="pw",
    )
    admin = User(
        id=3,
        email="admin@test.com",
        full_name="Admin",
        role=RoleEnum.admin,
        hashed_password="pw",
    )
    student = User(
        id=4,
        email="student@test.com",
        full_name="Student",
        role=RoleEnum.student,
        hashed_password="pw",
    )
    guardian = User(
        id=5,
        email="parent@test.com",
        full_name="Parent",
        role=RoleEnum.guardian,
        hashed_password="pw",
    )

    # Teacher has marks.approve but NOT marks.publish
    assert AuthorizationService.has_permission(teacher, "marks.approve") is True
    assert AuthorizationService.has_permission(teacher, "marks.publish") is False

    # Principal and Admin have both marks.approve and marks.publish
    assert AuthorizationService.has_permission(principal, "marks.approve") is True
    assert AuthorizationService.has_permission(principal, "marks.publish") is True
    assert AuthorizationService.has_permission(admin, "marks.approve") is True
    assert AuthorizationService.has_permission(admin, "marks.publish") is True

    # Student and Guardian have neither
    assert AuthorizationService.has_permission(student, "marks.approve") is False
    assert AuthorizationService.has_permission(student, "marks.publish") is False
    assert AuthorizationService.has_permission(guardian, "marks.approve") is False
    assert AuthorizationService.has_permission(guardian, "marks.publish") is False


def test_class_teacher_scope_for_marks_approve(session: Session):
    # Setup users
    u_ct = User(
        id=10,
        email="ct@test.com",
        full_name="Class Teacher",
        role=RoleEnum.teacher,
        hashed_password="pw",
    )
    u_st = User(
        id=11,
        email="st@test.com",
        full_name="Subject Teacher",
        role=RoleEnum.teacher,
        hashed_password="pw",
    )
    u_other = User(
        id=12,
        email="other@test.com",
        full_name="Other Teacher",
        role=RoleEnum.teacher,
        hashed_password="pw",
    )
    u_principal = User(
        id=13,
        email="principal@test.com",
        full_name="Principal",
        role=RoleEnum.principal,
        hashed_password="pw",
    )
    session.add_all([u_ct, u_st, u_other, u_principal])
    session.commit()

    # Setup profiles
    tp_ct = TeacherProfile(
        id=100,
        user_id=u_ct.id,
        department="Science",
        qualification="M.Sc",
        joining_date=date(2020, 1, 1),
    )
    tp_st = TeacherProfile(
        id=101,
        user_id=u_st.id,
        department="Science",
        qualification="B.Ed",
        joining_date=date(2021, 1, 1),
    )
    tp_other = TeacherProfile(
        id=102,
        user_id=u_other.id,
        department="Arts",
        qualification="M.A",
        joining_date=date(2022, 1, 1),
    )
    session.add_all([tp_ct, tp_st, tp_other])
    session.commit()

    # Setup class and subject
    grade_class = GradeClass(id=1, name="Class 10-A", level=10)
    subject = Subject(id=1, name="Physics", code="PHY101")
    session.add_all([grade_class, subject])
    session.commit()

    # Assign tp_ct as Class Teacher for grade_class 1
    ct_assign = ClassTeacherAssignment(
        id=1, teacher_id=tp_ct.id, grade_class_id=grade_class.id
    )
    # Assign tp_st as Subject Teacher (not Class Teacher) for grade_class 1
    st_assign = TeacherAssignment(
        id=1, teacher_id=tp_st.id, grade_class_id=grade_class.id, subject_id=subject.id
    )
    session.add_all([ct_assign, st_assign])
    session.commit()

    # 1. Class Teacher can approve marks for class 1
    assert (
        AuthorizationService.can(u_ct, "marks.approve", session=session, class_id=1)
        is True
    )

    # 2. Subject Teacher CANNOT approve marks for class 1 (only class teacher can approve)
    assert (
        AuthorizationService.can(u_st, "marks.approve", session=session, class_id=1)
        is False
    )

    # 3. Unassigned Teacher CANNOT approve marks for class 1
    assert (
        AuthorizationService.can(u_other, "marks.approve", session=session, class_id=1)
        is False
    )

    # 4. Principal CAN approve marks
    assert (
        AuthorizationService.can(
            u_principal, "marks.approve", session=session, class_id=1
        )
        is True
    )


def test_exam_results_lifecycle_success(session: Session):
    # Setup users
    teacher = User(
        id=20,
        email="teacher@test.com",
        full_name="Subject Teacher",
        role=RoleEnum.teacher,
        hashed_password="pw",
    )
    ct = User(
        id=21,
        email="ct@test.com",
        full_name="Class Teacher",
        role=RoleEnum.teacher,
        hashed_password="pw",
    )
    principal = User(
        id=22,
        email="principal@test.com",
        full_name="Principal",
        role=RoleEnum.principal,
        hashed_password="pw",
    )
    session.add_all([teacher, ct, principal])
    session.commit()

    # Setup Student
    student = StudentProfile(
        id=1,
        user_id=30,
        admission_number="ADM-001",
        date_of_birth=date(2010, 5, 1),
        guardian_name="Guardian 1",
        grade_class_id=1,
    )
    session.add(student)
    session.commit()

    # Setup Exam Term and Paper
    term = ExamTerm(
        id=1,
        name="Term 1",
        grade_class_id=1,
        start_date=date(2026, 9, 1),
        end_date=date(2026, 9, 10),
    )
    paper = ExamPaper(
        id=1,
        exam_term_id=1,
        subject_id=1,
        status=ExamPaperStatus.approved,
        content_json={},
    )
    session.add_all([term, paper])
    session.commit()

    # 1. Bulk upload marks by Subject Teacher -> entered
    bulk_data = BulkExamResultCreate(
        exam_paper_id=paper.id,
        results=[
            {"student_id": 1, "marks_obtained": 88.5, "ai_feedback": "Great work"}
        ],
    )
    entered_results = exam_service.bulk_upload_results(
        session, bulk_data, current_user=teacher
    )
    assert len(entered_results) == 1
    assert entered_results[0].status == ResultStatus.entered
    assert entered_results[0].entered_by_id == teacher.id
    assert entered_results[0].approved_by_id is None
    assert entered_results[0].published_by_id is None

    # 2. Class Teacher approves marks -> approved
    approved_results = exam_service.approve_paper_results(
        session, paper.id, current_user=ct
    )
    assert len(approved_results) == 1
    assert approved_results[0].status == ResultStatus.approved
    assert approved_results[0].entered_by_id == teacher.id
    assert approved_results[0].approved_by_id == ct.id
    assert approved_results[0].published_by_id is None

    # 3. Principal publishes marks -> published
    published_results = exam_service.publish_paper_results(
        session, paper.id, current_user=principal
    )
    assert len(published_results) == 1
    assert published_results[0].status == ResultStatus.published
    assert published_results[0].entered_by_id == teacher.id
    assert published_results[0].approved_by_id == ct.id
    assert published_results[0].published_by_id == principal.id


def test_cannot_publish_unapproved_results(session: Session):
    principal = User(
        id=40,
        email="principal@test.com",
        full_name="Principal",
        role=RoleEnum.principal,
        hashed_password="pw",
    )
    session.add(principal)

    student = StudentProfile(
        id=2,
        user_id=41,
        admission_number="ADM-002",
        date_of_birth=date(2010, 6, 1),
        guardian_name="Guardian 2",
        grade_class_id=1,
    )
    session.add(student)

    term = ExamTerm(
        id=2,
        name="Term 2",
        grade_class_id=1,
        start_date=date(2026, 9, 1),
        end_date=date(2026, 9, 10),
    )
    paper = ExamPaper(
        id=2,
        exam_term_id=2,
        subject_id=1,
        status=ExamPaperStatus.approved,
        content_json={},
    )
    session.add_all([term, paper])
    session.commit()

    # Upload entered marks (not approved)
    bulk_data = BulkExamResultCreate(
        exam_paper_id=paper.id,
        results=[{"student_id": 2, "marks_obtained": 75.0}],
    )
    exam_service.bulk_upload_results(session, bulk_data)

    # Attempt to publish directly without approval -> should raise 400 Bad Request
    with pytest.raises(HTTPException) as exc_info:
        exam_service.publish_paper_results(session, paper.id, current_user=principal)
    assert exc_info.value.status_code == 400
    assert "must be approved" in exc_info.value.detail.lower()


def test_cannot_approve_already_published_results(session: Session):
    ct = User(
        id=50,
        email="ct@test.com",
        full_name="Class Teacher",
        role=RoleEnum.teacher,
        hashed_password="pw",
    )
    principal = User(
        id=51,
        email="principal@test.com",
        full_name="Principal",
        role=RoleEnum.principal,
        hashed_password="pw",
    )
    session.add_all([ct, principal])

    student = StudentProfile(
        id=3,
        user_id=52,
        admission_number="ADM-003",
        date_of_birth=date(2010, 7, 1),
        guardian_name="Guardian 3",
        grade_class_id=1,
    )
    session.add(student)

    term = ExamTerm(
        id=3,
        name="Term 3",
        grade_class_id=1,
        start_date=date(2026, 9, 1),
        end_date=date(2026, 9, 10),
    )
    paper = ExamPaper(
        id=3,
        exam_term_id=3,
        subject_id=1,
        status=ExamPaperStatus.approved,
        content_json={},
    )
    session.add_all([term, paper])
    session.commit()

    bulk_data = BulkExamResultCreate(
        exam_paper_id=paper.id,
        results=[{"student_id": 3, "marks_obtained": 90.0}],
    )
    exam_service.bulk_upload_results(session, bulk_data)
    exam_service.approve_paper_results(session, paper.id, current_user=ct)
    exam_service.publish_paper_results(session, paper.id, current_user=principal)

    # Attempt to re-approve already published results
    with pytest.raises(HTTPException) as exc_info:
        exam_service.approve_paper_results(session, paper.id, current_user=ct)
    assert exc_info.value.status_code == 400
    assert "already been published" in exc_info.value.detail.lower()


def test_empty_results_validation(session: Session):
    principal = User(
        id=60,
        email="principal@test.com",
        full_name="Principal",
        role=RoleEnum.principal,
        hashed_password="pw",
    )
    session.add(principal)

    term = ExamTerm(
        id=4,
        name="Term 4",
        grade_class_id=1,
        start_date=date(2026, 9, 1),
        end_date=date(2026, 9, 10),
    )
    paper = ExamPaper(
        id=4,
        exam_term_id=4,
        subject_id=1,
        status=ExamPaperStatus.approved,
        content_json={},
    )
    session.add_all([term, paper])
    session.commit()

    with pytest.raises(HTTPException) as exc_approve:
        exam_service.approve_paper_results(session, paper.id, current_user=principal)
    assert exc_approve.value.status_code == 400

    with pytest.raises(HTTPException) as exc_publish:
        exam_service.publish_paper_results(session, paper.id, current_user=principal)
    assert exc_publish.value.status_code == 400


def test_student_and_parent_visibility_filtering(session: Session):
    student_user = User(
        id=70,
        email="s@test.com",
        full_name="Student",
        role=RoleEnum.student,
        hashed_password="pw",
    )
    parent_user = User(
        id=71,
        email="p@test.com",
        full_name="Parent",
        role=RoleEnum.guardian,
        hashed_password="pw",
    )
    teacher_user = User(
        id=72,
        email="t@test.com",
        full_name="Teacher",
        role=RoleEnum.teacher,
        hashed_password="pw",
    )
    session.add_all([student_user, parent_user, teacher_user])

    student = StudentProfile(
        id=10,
        user_id=student_user.id,
        admission_number="ADM-010",
        date_of_birth=date(2010, 8, 1),
        guardian_name="Guardian P",
        grade_class_id=1,
    )
    session.add(student)
    session.commit()

    # Link parent to student
    relationship = StudentParentRelationship(
        id=1, student_id=student.id, parent_user_id=parent_user.id
    )
    session.add(relationship)

    term = ExamTerm(
        id=5,
        name="Term 5",
        grade_class_id=1,
        start_date=date(2026, 9, 1),
        end_date=date(2026, 9, 10),
    )
    paper = ExamPaper(
        id=5,
        exam_term_id=5,
        subject_id=1,
        status=ExamPaperStatus.approved,
        content_json={},
    )
    session.add_all([term, paper])
    session.commit()

    # 1. Result is entered (draft)
    bulk_data = BulkExamResultCreate(
        exam_paper_id=paper.id,
        results=[{"student_id": student.id, "marks_obtained": 92.0}],
    )
    exam_service.bulk_upload_results(session, bulk_data)

    # Teacher sees it
    assert (
        len(
            exam_service.get_results_by_student(
                session, student.id, current_user=teacher_user
            )
        )
        == 1
    )
    # Student and Parent do NOT see draft marks
    assert (
        len(
            exam_service.get_results_by_student(
                session, student.id, current_user=student_user
            )
        )
        == 0
    )
    assert (
        len(
            exam_service.get_results_by_student(
                session, student.id, current_user=parent_user
            )
        )
        == 0
    )

    # 2. Result is approved by Class Teacher
    exam_service.approve_paper_results(session, paper.id, current_user=teacher_user)
    # Student and Parent STILL do not see marks until published
    assert (
        len(
            exam_service.get_results_by_student(
                session, student.id, current_user=student_user
            )
        )
        == 0
    )
    assert (
        len(
            exam_service.get_results_by_student(
                session, student.id, current_user=parent_user
            )
        )
        == 0
    )

    # 3. Result is published by Principal
    exam_service.publish_paper_results(session, paper.id, current_user=teacher_user)
    # Now Student and Parent CAN see marks
    assert (
        len(
            exam_service.get_results_by_student(
                session, student.id, current_user=student_user
            )
        )
        == 1
    )
    assert (
        len(
            exam_service.get_results_by_student(
                session, student.id, current_user=parent_user
            )
        )
        == 1
    )


def test_student_and_parent_scope_isolation(session: Session):
    s1_user = User(
        id=80,
        email="s1@test.com",
        full_name="Student 1",
        role=RoleEnum.student,
        hashed_password="pw",
    )
    s2_user = User(
        id=81,
        email="s2@test.com",
        full_name="Student 2",
        role=RoleEnum.student,
        hashed_password="pw",
    )
    p1_user = User(
        id=82,
        email="p1@test.com",
        full_name="Parent 1",
        role=RoleEnum.guardian,
        hashed_password="pw",
    )
    session.add_all([s1_user, s2_user, p1_user])
    session.commit()

    sp1 = StudentProfile(
        id=20,
        user_id=s1_user.id,
        admission_number="ADM-020",
        date_of_birth=date(2010, 1, 1),
        guardian_name="Guardian 1",
        grade_class_id=1,
    )
    sp2 = StudentProfile(
        id=21,
        user_id=s2_user.id,
        admission_number="ADM-021",
        date_of_birth=date(2010, 2, 1),
        guardian_name="Guardian 2",
        grade_class_id=1,
    )
    session.add_all([sp1, sp2])
    session.commit()

    rel = StudentParentRelationship(id=2, student_id=sp1.id, parent_user_id=p1_user.id)
    session.add(rel)
    session.commit()

    # Student 1 can read own marks
    assert (
        AuthorizationService.can(
            s1_user, "marks.read", session=session, student_id=sp1.id
        )
        is True
    )
    # Student 1 cannot read Student 2 marks
    assert (
        AuthorizationService.can(
            s1_user, "marks.read", session=session, student_id=sp2.id
        )
        is False
    )

    # Parent 1 can read child (Student 1) marks
    assert (
        AuthorizationService.can(
            p1_user, "marks.read", session=session, student_id=sp1.id
        )
        is True
    )
    # Parent 1 cannot read other student (Student 2) marks
    assert (
        AuthorizationService.can(
            p1_user, "marks.read", session=session, student_id=sp2.id
        )
        is False
    )
