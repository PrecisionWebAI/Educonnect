"""The Exams plan's HTTP surface, mounted on `/exams` beside the AI-paper routes.

Paths (deliberately **not** under `/exams/papers/{id}` bare, which the question-paper
stack already owns):

* `GET /exams/marking-defaults?total=` - the pre-filled pass line for a paper (33% of the
  total, the school's ladder, how results are shown);
* `POST /exams/class-tests` - schedule a class test for one or several sections;
* `PATCH /exams/class-tests/{exam_id}` - edit it (a new date is a reschedule);
* `POST /exams/class-tests/{exam_id}/cancel` - call it off (marks, if any, stay);
* `DELETE /exams/class-tests/{exam_id}` - remove it (only while no marks exist);
* `POST /exams/school-exams` - set a section's date sheet (a draft, invisible to families);
* `PATCH /exams/school-exams/{exam_id}` - change it (after publishing, families are told);
* `POST /exams/school-exams/{exam_id}/publish` - publish it: the only moment families first hear;
* `DELETE /exams/school-exams/{exam_id}` - throw away an unpublished sheet with no marks;
* `GET|PUT /exams/papers/{paper_id}/syllabus` - one subject's syllabus (free text);
* `POST /exams` - plan an exam with its date sheet;
* `GET /exams` - the exams this caller may see;
* `PATCH /exams/{exam_id}` - move the dates, replace the syllabus (families are told);
* `GET /exams/{exam_id}/papers` - the exam and its date sheet;
* `GET /exams/papers/{paper_id}/marks` - the sheet to fill in;
* `POST /exams/papers/{paper_id}/marks` - save a draft;
* `POST /exams/papers/{paper_id}/publish` - publish that sitting;
* `PATCH /exams/papers/{paper_id}/marks/{student_id}` - correct a published mark (audited);
* `GET /exams/papers/{paper_id}/marks/history` - the corrections made to a paper's published marks;
* `GET /exams/results/overview?kind=` - Class Test **or** School Exam results for the year:
  per test, subject-wise so far, overall; narrowed to the caller;
* `GET /exams/{exam_id}/results` - marks, grades and ranks, narrowed to the caller;
* `PATCH /exams/paper-groups/{group_id}` - edit a shared question paper (409 once locked);
* `POST /exams/paper-groups/{group_id}/papers/{paper_id}/detach` - give one section its
  own paper.

Reading needs `marks.read`, writing needs `marks.update`; the **service** then narrows
further (a teacher only acts on a subject they hold, a family only sees its own child).
"""

from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

from app.core.db import get_session
from app.domains.auth.dependencies import RequirePermission

from . import class_test, overview, school_exam, service, setup
from .schemas import (
    ClassTestCreateIn,
    ClassTestUpdateIn,
    ExamCreateIn,
    ExamPaperRead,
    ExamRead,
    ExamUpdateIn,
    GradeModeIn,
    MarkAuditRead,
    MarkChangeIn,
    MarkingDefaultsRead,
    MarksSavedRead,
    MarksSaveIn,
    PaperGroupRead,
    PaperGroupUpdateIn,
    PaperMarkRowRead,
    ResultOverviewRead,
    ResultsRead,
    SchoolExamCreateIn,
    SchoolExamUpdateIn,
    SectionChoiceRead,
    SyllabusIn,
    SyllabusRead,
)

router = APIRouter()


@router.get("/marking-defaults", response_model=MarkingDefaultsRead)
def read_marking_defaults(
    total: Decimal = Query(gt=0, le=Decimal("9999.99")),
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("marks.read")),
):
    """What a new paper out of `total` marks starts from: 33% pass marks, the passing
    grade that earns, the school's ladder, and how results are shown. Starting values
    only - the teacher changes any of them for that one paper."""
    return setup.marking_defaults(session, total)


@router.get("/sections", response_model=list[SectionChoiceRead])
def read_sections_of_class(
    classroom_id: UUID,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("marks.update")),
):
    """The class-sections of this section's class (with their subjects) for the
    "Sections" pickers of the class test and the date sheet."""
    return school_exam.sections_of_class(session, classroom_id)


@router.post(
    "/class-tests", response_model=ExamRead, status_code=status.HTTP_201_CREATED
)
def create_class_test(
    payload: ClassTestCreateIn,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("marks.update")),
):
    """Schedule a class test for one or several sections of one class.

    The subject teacher, the class teacher or the school's leadership may schedule it.
    `409 DUPLICATE_EXAM` carries the tests that already exist for the same section,
    subject and date; resend with `confirm_duplicate: true` to create it anyway.
    """
    return class_test.create_class_test(session, payload, current_user)


@router.patch("/class-tests/{exam_id}", response_model=ExamRead)
def update_class_test(
    exam_id: UUID,
    payload: ClassTestUpdateIn,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("marks.update")),
):
    """Change a class test. A new date is a reschedule; any other change tells the
    families what changed; a changed family note only says the note changed."""
    return class_test.update_class_test(session, exam_id, payload, current_user)


@router.post("/class-tests/{exam_id}/archive", response_model=ExamRead)
def archive_class_test(
    exam_id: UUID,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("marks.update")),
):
    """Hide a cancelled class test from the list (nothing is deleted)."""
    return class_test.archive_class_test(session, exam_id, current_user, archive=True)


@router.post("/class-tests/{exam_id}/unarchive", response_model=ExamRead)
def unarchive_class_test(
    exam_id: UUID,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("marks.update")),
):
    """Bring an archived class test back to the list."""
    return class_test.archive_class_test(session, exam_id, current_user, archive=False)


@router.post("/class-tests/{exam_id}/cancel", response_model=ExamRead)
def cancel_class_test(
    exam_id: UUID,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("marks.update")),
):
    """Call the test off. The record and any marks stay; the families are told."""
    return class_test.cancel_class_test(session, exam_id, current_user)


@router.delete("/class-tests/{exam_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_class_test(
    exam_id: UUID,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("marks.update")),
):
    """Delete a test nobody has marks for (`409` otherwise - cancel it instead)."""
    class_test.delete_class_test(session, exam_id, current_user)


@router.post(
    "/school-exams", response_model=ExamRead, status_code=status.HTTP_201_CREATED
)
def create_school_exam(
    payload: SchoolExamCreateIn,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("marks.update")),
):
    """Set a section's date sheet for a school exam (Unit Test ... Custom).

    The class teacher of that section or leadership may. It starts as a **draft**: no
    family sees it and nobody is notified until it is published."""
    return school_exam.create_school_exam(session, payload, current_user)


@router.patch("/school-exams/{exam_id}", response_model=ExamRead)
def update_school_exam(
    exam_id: UUID,
    payload: SchoolExamUpdateIn,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("marks.update")),
):
    """Change the date sheet. Silent while it is a draft; once published the families
    are told what changed."""
    return school_exam.update_school_exam(session, exam_id, payload, current_user)


@router.post("/school-exams/{exam_id}/cancel", response_model=ExamRead)
def cancel_school_exam(
    exam_id: UUID,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("marks.update")),
):
    """Call a school exam off (the families are told if its date sheet was published)."""
    return school_exam.cancel_school_exam(session, exam_id, current_user)


@router.post("/school-exams/{exam_id}/archive", response_model=ExamRead)
def archive_school_exam(
    exam_id: UUID,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("marks.update")),
):
    """Hide a date sheet from the list. Nothing is deleted and nobody is told."""
    return school_exam.archive_school_exam(session, exam_id, current_user, archive=True)


@router.post("/school-exams/{exam_id}/unarchive", response_model=ExamRead)
def unarchive_school_exam(
    exam_id: UUID,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("marks.update")),
):
    """Bring an archived date sheet back to the list."""
    return school_exam.archive_school_exam(session, exam_id, current_user, archive=False)


@router.post("/school-exams/{exam_id}/publish", response_model=ExamRead)
def publish_date_sheet(
    exam_id: UUID,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("marks.update")),
):
    """Publish the date sheet and its syllabus (class teacher or leadership)."""
    return school_exam.publish_date_sheet(session, exam_id, current_user)


@router.delete("/school-exams/{exam_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_school_exam(
    exam_id: UUID,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("marks.update")),
):
    """Delete a date sheet that was never published and has no marks."""
    school_exam.delete_school_exam(session, exam_id, current_user)


@router.get("/papers/{paper_id}/syllabus", response_model=SyllabusRead)
def read_syllabus(
    paper_id: UUID,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("marks.read")),
):
    """One subject's syllabus. Its writers always read it; everyone else only once the
    date sheet is published."""
    return school_exam.get_syllabus(session, paper_id, current_user)


@router.put("/papers/{paper_id}/syllabus", response_model=SyllabusRead)
def write_syllabus(
    paper_id: UUID,
    payload: SyllabusIn,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("marks.update")),
):
    """Write a subject's syllabus (its teacher, the class teacher, or leadership)."""
    return school_exam.set_syllabus(session, paper_id, payload, current_user)


@router.post("", response_model=ExamRead, status_code=status.HTTP_201_CREATED)
def create_exam(
    payload: ExamCreateIn,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("marks.update")),
):
    """Plan an exam (class exam: its teacher or the office; school exam: the office)."""
    return service.create_exam(session=session, payload=payload, user=current_user)


@router.get("", response_model=list[ExamRead])
def list_exams(
    classroom_id: UUID | None = Query(default=None),
    class_id: UUID | None = Query(default=None),
    exam_status: str | None = Query(default=None, alias="status"),
    academic_year_id: UUID | None = Query(default=None),
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("marks.read")),
):
    """The exams this caller may see (current year by default)."""
    return service.list_exams(
        session,
        current_user,
        classroom_id=classroom_id,
        class_id=class_id,
        status=exam_status,
        academic_year_id=academic_year_id,
    )


@router.get("/{exam_id}/papers", response_model=ExamRead)
def read_exam(
    exam_id: UUID,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("marks.read")),
):
    """One exam with its date sheet, each paper saying whether this caller may edit it."""
    return service.read_exam(session=session, exam_id=exam_id, user=current_user)


@router.patch("/{exam_id}", response_model=ExamRead)
def update_exam(
    exam_id: UUID,
    payload: ExamUpdateIn,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("marks.update")),
):
    """Change the dates or the syllabus. A published paper is never silently re-cut."""
    return service.update_exam(
        session=session, exam_id=exam_id, payload=payload, user=current_user
    )


@router.get("/papers/{paper_id}/marks", response_model=list[PaperMarkRowRead])
def read_paper_marks(
    paper_id: UUID,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("marks.read")),
):
    """The sheet for one paper: every child in its class, marked or not."""
    return service.paper_marks(session, paper_id, current_user)


@router.post("/papers/{paper_id}/marks", response_model=MarksSavedRead)
def save_paper_marks(
    paper_id: UUID,
    payload: MarksSaveIn,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("marks.update")),
):
    """Save a draft of one paper's scores (refused with `409` once published)."""
    return service.save_marks(
        session=session, paper_id=paper_id, payload=payload, user=current_user
    )


@router.post("/papers/{paper_id}/publish", response_model=ExamPaperRead)
def publish_paper_marks(
    paper_id: UUID,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("marks.update")),
):
    """Publish one sitting's marks - the moment families may see them."""
    return service.publish_paper(session=session, paper_id=paper_id, user=current_user)


@router.post("/papers/{paper_id}/grade-mode", response_model=list[PaperMarkRowRead])
def change_grade_mode(
    paper_id: UUID,
    payload: GradeModeIn,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("marks.update")),
):
    """Switch the Grade column between NA, Auto and Manual - also after publishing."""
    return service.set_grade_mode(session, paper_id, payload, current_user)


@router.get("/papers/{paper_id}/marks/history", response_model=list[MarkAuditRead])
def read_mark_history(
    paper_id: UUID,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("marks.read")),
):
    """Every correction made to this paper's published marks: who, when, from what to
    what. For the people who run the paper - never for a family."""
    return service.mark_history(session, paper_id, current_user)


@router.patch("/papers/{paper_id}/marks/{student_id}", response_model=PaperMarkRowRead)
def change_published_mark(
    paper_id: UUID,
    student_id: UUID,
    payload: MarkChangeIn,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("marks.update")),
):
    """Correct one published mark. Writes `marks_audit` and tells the family."""
    return service.change_mark(
        session=session,
        paper_id=paper_id,
        student_id=student_id,
        payload=payload,
        user=current_user,
    )


@router.get("/results/overview", response_model=ResultOverviewRead)
def read_result_overview(
    kind: str = Query(pattern="^(class_test|school_exam)$"),
    classroom_id: UUID | None = Query(default=None),
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("marks.read")),
):
    """The results of one **kind** for the year on screen: each test, the subject-wise
    percentage so far, and the overall percentage.

    Staff name a `classroom_id` (leadership: any section; a teacher: a section they teach
    in or are the class teacher of) and get the class view with class average, highest,
    lowest and passed/failed per test. A student or guardian gets only their own children,
    only for published tests, with no class figures."""
    return overview.result_overview(session, current_user, kind, classroom_id)


@router.get("/{exam_id}/results", response_model=ResultsRead)
def read_results(
    exam_id: UUID,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("marks.read")),
):
    """Marks, grades and ranks - narrowed to the caller (a family sees its own child)."""
    return service.results(session=session, exam_id=exam_id, user=current_user)


@router.patch("/paper-groups/{group_id}", response_model=PaperGroupRead)
def update_paper_group(
    group_id: UUID,
    payload: PaperGroupUpdateIn,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("marks.update")),
):
    """Edit a shared paper's title, chapters or maximum. `409` once marks or publication exist."""
    return service.update_group(
        session=session, group_id=group_id, payload=payload, user=current_user
    )


@router.post(
    "/paper-groups/{group_id}/papers/{paper_id}/detach", response_model=ExamPaperRead
)
def detach_paper_from_group(
    group_id: UUID,
    paper_id: UUID,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("marks.update")),
):
    """Give one section its own paper; the others keep sharing. `409` names missing chapters."""
    return service.detach_paper(
        session=session, group_id=group_id, paper_id=paper_id, user=current_user
    )
