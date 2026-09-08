from datetime import date

from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.core.db import get_session
from app.domains.auth.dependencies import RequirePermission

from . import service
from .schemas import (
    ClassDiaryCreate,
    ClassDiaryRead,
    DiaryEntryRead,
    HomeworkAssignmentCreate,
    HomeworkAssignmentRead,
    HomeworkSubmissionCreate,
    HomeworkSubmissionRead,
    SubmissionItemRead,
)

router = APIRouter()

# Removed StaffRoles


@router.post(
    "", response_model=HomeworkAssignmentRead, status_code=status.HTTP_201_CREATED
)
def create_homework(
    homework_in: HomeworkAssignmentCreate,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("homework.create")),
):
    """
    Teacher assigns homework.
    """
    from fastapi import HTTPException

    from app.domains.auth.service import AuthorizationService

    # Verify Teacher is assigned to the subject/class
    if not AuthorizationService.can(
        current_user,
        "homework.create",
        session=session,
        class_id=homework_in.grade_class_id,
        subject_id=homework_in.subject_id,
    ):
        raise HTTPException(
            status_code=403,
            detail="Not authorized to create homework for this class/subject.",
        )

    return service.create_homework(session=session, homework_in=homework_in)


@router.get("/class/{class_id}", response_model=list[HomeworkAssignmentRead])
def read_homework_by_class(
    class_id: int,
    section_id: int | None = None,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("homework.read")),
):
    """
    Fetch homework for a class board.
    """
    return service.get_homework_by_class(
        session=session, class_id=class_id, section_id=section_id
    )


@router.post(
    "/submit",
    response_model=HomeworkSubmissionRead,
    status_code=status.HTTP_201_CREATED,
)
def submit_homework(
    submission_in: HomeworkSubmissionCreate,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("homework.submit")),
):
    """
    Student submits homework or marks it as done.
    """
    from fastapi import HTTPException

    from app.domains.auth.service import AuthorizationService

    if not AuthorizationService.can(
        current_user,
        "homework.submit",
        session=session,
        student_id=submission_in.student_id,
    ):
        raise HTTPException(
            status_code=403,
            detail="Not authorized to submit homework for this student.",
        )

    return service.submit_homework(session=session, submission_in=submission_in)


@router.post(
    "/diary", response_model=ClassDiaryRead, status_code=status.HTTP_201_CREATED
)
def create_diary_note(
    diary_in: ClassDiaryCreate,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("diary.create")),
):
    """
    Add a diary note for a class.
    """
    from fastapi import HTTPException

    from app.domains.auth.service import AuthorizationService

    if not AuthorizationService.can(
        current_user,
        "diary.create",
        session=session,
        class_id=diary_in.grade_class_id,
        subject_id=diary_in.subject_id,
    ):
        raise HTTPException(
            status_code=403,
            detail="Not authorized to create diary entry for this class/subject.",
        )

    return service.create_diary_note(session=session, diary_in=diary_in)


@router.get("/diary/student/{student_id}", response_model=list[ClassDiaryRead])
def read_diary_notes(
    student_id: int,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("diary.read")),
):
    """
    Fetch diary notes for a student.
    """
    return service.get_diary_by_student(session=session, student_id=student_id)


@router.get("", response_model=list[HomeworkAssignmentRead])
def read_all_homework(
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("homework.read")),
):
    return [
        HomeworkAssignmentRead(
            id=1,
            title="Trigonometry worksheet",
            description="Solve questions 1-15 from the Trigonometry chapter.",
            grade_class_id=1,
            section_id=1,
            subject_id=1,
            teacher_id=1,
            due_date=date.today(),
            subject="Mathematics",
            className="10-A",
            due="Tomorrow",
            assignedBy="M. Iyer",
        ),
        HomeworkAssignmentRead(
            id=2,
            title="Electricity circuit lab",
            description="Build a series circuit and record observations.",
            grade_class_id=1,
            section_id=1,
            subject_id=1,
            teacher_id=1,
            due_date=date.today(),
            subject="Physics",
            className="10-A",
            due="Fri",
            assignedBy="P. Menon",
        ),
        HomeworkAssignmentRead(
            id=3,
            title="Essay - My School",
            description="Write a 300-word essay about your school.",
            grade_class_id=1,
            section_id=1,
            subject_id=1,
            teacher_id=1,
            due_date=date.today(),
            subject="English",
            className="10-A",
            due="Mon",
            assignedBy="S. Das",
        ),
    ]


@router.get("/submissions", response_model=list[SubmissionItemRead])
def read_submissions(
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("homework.read")),
):
    return [
        SubmissionItemRead(
            id=1,
            homeworkTitle="Trigonometry worksheet",
            student="Aarav Mehta",
            status="Submitted",
            submittedAt="Yesterday",
        ),
        SubmissionItemRead(
            id=2,
            homeworkTitle="Trigonometry worksheet",
            student="Diya Sharma",
            status="Submitted",
            submittedAt="Today",
        ),
        SubmissionItemRead(
            id=3,
            homeworkTitle="Electricity circuit lab",
            student="Vivaan Patel",
            status="Pending",
            submittedAt="-",
        ),
        SubmissionItemRead(
            id=4,
            homeworkTitle="Essay - My School",
            student="Rohan Gupta",
            status="Late",
            submittedAt="2 days late",
        ),
    ]


@router.get("/diary", response_model=list[DiaryEntryRead])
def read_diary(
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("diary.read")),
):
    return [
        DiaryEntryRead(
            id=1,
            className="10-A",
            day="Mon",
            subject="Mathematics",
            topic="Trigonometry basics",
            homework="Worksheet 1-15",
            activity="Group quiz",
        ),
        DiaryEntryRead(
            id=2,
            className="10-A",
            day="Tue",
            subject="Physics",
            topic="Ohm law",
            homework="Numericals",
            activity="Lab demo",
        ),
        DiaryEntryRead(
            id=3,
            className="10-A",
            day="Wed",
            subject="English",
            topic="Essay writing",
            homework="Essay on school",
            activity="Peer review",
        ),
    ]
