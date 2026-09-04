from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.core.db import get_session
from app.domains.auth.dependencies import RoleChecker
from app.domains.users.models import RoleEnum

from . import service
from .schemas import (
    BulkExamResultCreate,
    DisputeRowRead,
    ExamMarkingRowRead,
    ExamPaperCreate,
    ExamPaperRead,
    ExamResultRead,
    ExamScheduleItemRead,
    ExamTermCreate,
    ExamTermRead,
    MarksEntryRead,
    MarksRowRead,
    PaperDraftFullRead,
    PaperReviewItemRead,
    QuestionItemRead,
    ResultRowRead,
)

router = APIRouter()

AdminPrincipalDirector = RoleChecker(
    [RoleEnum.admin, RoleEnum.principal, RoleEnum.director]
)
StaffRoles = RoleChecker(
    [
        RoleEnum.admin,
        RoleEnum.principal,
        RoleEnum.director,
        RoleEnum.teacher,
        RoleEnum.hod,
    ]
)


@router.post("/terms", response_model=ExamTermRead, status_code=status.HTTP_201_CREATED)
def create_exam_term(
    term_in: ExamTermCreate,
    session: Session = Depends(get_session),
    current_user=Depends(AdminPrincipalDirector),
):
    """
    Create an exam term.
    """
    return service.create_term(session=session, term_in=term_in)


@router.get("/terms/class/{class_id}", response_model=list[ExamTermRead])
def read_exam_terms(class_id: int, session: Session = Depends(get_session)):
    """
    Fetch exam terms for a specific class.
    """
    return service.get_terms_by_class(session=session, class_id=class_id)


@router.post(
    "/papers", response_model=ExamPaperRead, status_code=status.HTTP_201_CREATED
)
def create_exam_paper(
    paper_in: ExamPaperCreate,
    session: Session = Depends(get_session),
    current_user=Depends(StaffRoles),
):
    """
    Save an Exam Paper draft (AI generated JSON content).
    """
    return service.create_or_update_paper(session=session, paper_in=paper_in)


@router.post(
    "/results/bulk",
    response_model=list[ExamResultRead],
    status_code=status.HTTP_201_CREATED,
)
def bulk_upload_results(
    bulk_data: BulkExamResultCreate,
    session: Session = Depends(get_session),
    current_user=Depends(StaffRoles),
):
    """
    Upload student marks for a specific paper.
    """
    return service.bulk_upload_results(session=session, bulk_data=bulk_data)


@router.get("/results/student/{student_id}", response_model=list[ExamResultRead])
def read_student_results(student_id: int, session: Session = Depends(get_session)):
    """
    Fetch a student's report card data.
    """
    return service.get_results_by_student(session=session, student_id=student_id)


@router.get("/question-bank", response_model=list[QuestionItemRead])
def read_question_bank(session: Session = Depends(get_session)):
    return [
        QuestionItemRead(
            id=1,
            subject="Physics",
            chapter="Electricity",
            type="MCQ",
            difficulty="Easy",
            text="Which unit measures electric current?",
            marks=1,
        ),
        QuestionItemRead(
            id=2,
            subject="Physics",
            chapter="Electricity",
            type="Theory",
            difficulty="Medium",
            text="Explain Ohm law with a circuit diagram.",
            marks=5,
        ),
        QuestionItemRead(
            id=3,
            subject="Physics",
            chapter="Motion",
            type="Short",
            difficulty="Hard",
            text="Differentiate distance and displacement.",
            marks=3,
        ),
        QuestionItemRead(
            id=4,
            subject="Chemistry",
            chapter="Organic",
            type="MCQ",
            difficulty="Easy",
            text="Which is a hydrocarbon?",
            marks=1,
        ),
        QuestionItemRead(
            id=5,
            subject="Chemistry",
            chapter="Organic",
            type="Theory",
            difficulty="Hard",
            text="Explain aromaticity with examples.",
            marks=5,
        ),
        QuestionItemRead(
            id=6,
            subject="Mathematics",
            chapter="Trigonometry",
            type="Short",
            difficulty="Medium",
            text="Prove the identity sin^2 + cos^2 = 1.",
            marks=3,
        ),
    ]


@router.get("/paper-drafts-full", response_model=list[PaperDraftFullRead])
def read_paper_drafts_full(session: Session = Depends(get_session)):
    return [
        PaperDraftFullRead(
            id=1,
            title="Term-2 Physics Unit Test",
            subject="Physics",
            status="Approved",
            questions=20,
            totalMarks=40,
            updated="2 days ago",
        ),
        PaperDraftFullRead(
            id=2,
            title="Chemistry Mid-Term Paper",
            subject="Chemistry",
            status="Submitted",
            questions=25,
            totalMarks=50,
            updated="1 day ago",
        ),
        PaperDraftFullRead(
            id=3,
            title="Mathematics Weekly Quiz",
            subject="Mathematics",
            status="Draft",
            questions=10,
            totalMarks=20,
            updated="Just now",
        ),
    ]


@router.get("/schedule", response_model=list[ExamScheduleItemRead])
def read_exam_schedule(session: Session = Depends(get_session)):
    return [
        ExamScheduleItemRead(
            id=1,
            subject="Mathematics",
            date="22 Aug 2026",
            time="9:00-12:00",
            rooms=["Hall A", "Rm-201"],
            invigilator="M. Iyer",
        ),
        ExamScheduleItemRead(
            id=2,
            subject="Physics",
            date="24 Aug 2026",
            time="9:00-12:00",
            rooms=["Lab-3", "Hall B"],
            invigilator="P. Menon",
        ),
        ExamScheduleItemRead(
            id=3,
            subject="Chemistry",
            date="26 Aug 2026",
            time="9:00-12:00",
            rooms=["Hall A"],
            invigilator="R. Khanna",
        ),
    ]


@router.get("/markings", response_model=list[ExamMarkingRowRead])
def read_exam_markings(session: Session = Depends(get_session)):
    return [
        ExamMarkingRowRead(
            id=1,
            student="Aarav Mehta",
            subject="Physics",
            obtained=42,
            max=50,
            status="Entered",
        ),
        ExamMarkingRowRead(
            id=2,
            student="Diya Sharma",
            subject="Physics",
            obtained=46,
            max=50,
            status="Entered",
        ),
        ExamMarkingRowRead(
            id=3,
            student="Vivaan Patel",
            subject="Physics",
            obtained=0,
            max=50,
            status="Pending",
        ),
    ]


@router.get("/paper-reviews", response_model=list[PaperReviewItemRead])
def read_paper_reviews(session: Session = Depends(get_session)):
    return [
        PaperReviewItemRead(
            id=1,
            title="Term-2 Physics draft",
            subject="Physics",
            author="P. Menon",
            due="Today",
        ),
        PaperReviewItemRead(
            id=2,
            title="Chemistry MCQs",
            subject="Chemistry",
            author="R. Khanna",
            due="Tomorrow",
        ),
    ]


@router.get("/results", response_model=list[ResultRowRead])
def read_results(session: Session = Depends(get_session)):
    return [
        ResultRowRead(
            id=1,
            exam="Unit Test 2",
            className="8A",
            passRate=94,
            avgScore=72,
            topper="N. Joshi",
        ),
        ResultRowRead(
            id=2,
            exam="Unit Test 2",
            className="9C",
            passRate=88,
            avgScore=68,
            topper="S. Mehta",
        ),
        ResultRowRead(
            id=3,
            exam="Half Yearly",
            className="10B",
            passRate=91,
            avgScore=75,
            topper="R. Malhotra",
        ),
    ]


@router.get("/disputes", response_model=list[DisputeRowRead])
def read_disputes(session: Session = Depends(get_session)):
    return [
        DisputeRowRead(
            id=1,
            student="K. Shah",
            exam="Unit Test 2",
            subject="Maths",
            reason="Total mismatch on Q4",
            status="Open",
        ),
        DisputeRowRead(
            id=2,
            student="D. Pillai",
            exam="Half Yearly",
            subject="Science",
            reason="Answer not evaluated",
            status="Under Review",
        ),
        DisputeRowRead(
            id=3,
            student="V. Iyer",
            exam="Unit Test 1",
            subject="English",
            reason="Recheck requested",
            status="Resolved",
        ),
    ]


@router.get("/marks", response_model=list[MarksEntryRead])
def read_marks(session: Session = Depends(get_session)):
    return [
        MarksEntryRead(
            studentId=1,
            studentName="Aarav Mehta",
            className="10-A",
            exam="Term 1",
            rows=[
                MarksRowRead(subject="Mathematics", max=100, obtained=88),
                MarksRowRead(subject="Science", max=100, obtained=82),
                MarksRowRead(subject="English", max=100, obtained=79),
            ],
        ),
        MarksEntryRead(
            studentId=2,
            studentName="Diya Sharma",
            className="10-A",
            exam="Term 1",
            rows=[
                MarksRowRead(subject="Mathematics", max=100, obtained=91),
                MarksRowRead(subject="Science", max=100, obtained=95),
                MarksRowRead(subject="English", max=100, obtained=86),
            ],
        ),
        MarksEntryRead(
            studentId=4,
            studentName="Ananya Singh",
            className="10-A",
            exam="Term 1",
            rows=[
                MarksRowRead(subject="Mathematics", max=100, obtained=74),
                MarksRowRead(subject="Science", max=100, obtained=70),
                MarksRowRead(subject="English", max=100, obtained=90),
            ],
        ),
    ]
