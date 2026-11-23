"""Draft, decide and apply a promotion batch; keep class-teacher history per year."""

from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.core.tenancy import tenant_of
from app.domains.academic.classroom.students.models import Enrollment, Student
from app.domains.academic.classroom.students.placement import place_student
from app.domains.admin.settings.models import AcademicYear

from .models import ClassTeacherAssignment, PromotionBatch, PromotionDecision
from .schemas import (
    ClassTeacherAssignmentRead,
    ClassTeacherAssignmentWrite,
    PromotionBatchCreate,
    PromotionBatchRead,
    PromotionDecisionRead,
    PromotionDecisionWrite,
)

DECISION_STATUS = {
    "promote": "promoted",
    "repeat": "repeated",
    "transfer": "transferred",
    "leave": "left",
    "graduate": "graduated",
}


def _year(session: Session, year_id: UUID) -> AcademicYear:
    year = session.get(AcademicYear, year_id)
    if year is None or year.school_id != tenant_of(session):
        raise HTTPException(status_code=404, detail="Academic year not found")
    return year


def _batch(session: Session, batch_id: UUID) -> PromotionBatch:
    batch = session.get(PromotionBatch, batch_id)
    if batch is None or batch.school_id != tenant_of(session):
        raise HTTPException(status_code=404, detail="Promotion batch not found")
    return batch


def _decision_read(row: PromotionDecision) -> PromotionDecisionRead:
    return PromotionDecisionRead.model_validate(row, from_attributes=True)


def _batch_read(session: Session, batch: PromotionBatch) -> PromotionBatchRead:
    decisions = session.exec(
        select(PromotionDecision)
        .where(PromotionDecision.batch_id == batch.id)
        .order_by(PromotionDecision.student_id)
    ).all()
    return PromotionBatchRead(
        id=batch.id,
        from_academic_year_id=batch.from_academic_year_id,
        to_academic_year_id=batch.to_academic_year_id,
        status=batch.status,
        note=batch.note,
        applied_at=batch.applied_at,
        created_at=batch.created_at,
        decisions=[_decision_read(row) for row in decisions],
    )


def list_batches(session: Session) -> list[PromotionBatchRead]:
    rows = session.exec(
        select(PromotionBatch).order_by(PromotionBatch.created_at.desc())
    ).all()
    return [_batch_read(session, row) for row in rows]


def get_batch(session: Session, batch_id: UUID) -> PromotionBatchRead:
    return _batch_read(session, _batch(session, batch_id))


def create_batch(
    session: Session, payload: PromotionBatchCreate, user_id: UUID | None
) -> PromotionBatchRead:
    from_year = _year(session, payload.from_academic_year_id)
    to_year = _year(session, payload.to_academic_year_id)
    if from_year.id == to_year.id:
        raise HTTPException(
            status_code=422, detail="From and to academic years must be different"
        )
    batch = PromotionBatch(
        from_academic_year_id=from_year.id,
        to_academic_year_id=to_year.id,
        note=payload.note,
        created_by_user_id=user_id,
        school_id=tenant_of(session),
    )
    session.add(batch)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A promotion batch already exists for these academic years",
        ) from None
    session.refresh(batch)
    return _batch_read(session, batch)


def put_decisions(
    session: Session,
    batch_id: UUID,
    decisions: list[PromotionDecisionWrite],
    user_id: UUID | None,
) -> PromotionBatchRead:
    batch = _batch(session, batch_id)
    if batch.status != "draft":
        raise HTTPException(status_code=409, detail="Only a draft batch can be edited")

    from app.domains.academic.classroom.academics.models import Classroom

    for item in decisions:
        if item.decision not in DECISION_STATUS:
            raise HTTPException(
                status_code=422, detail=f"Unknown decision {item.decision!r}"
            )
        student = session.get(Student, item.student_id)
        if student is None or student.school_id != tenant_of(session):
            raise HTTPException(status_code=404, detail="Student not found")
        source = session.exec(
            select(Enrollment).where(
                Enrollment.student_id == student.id,
                Enrollment.academic_year_id == batch.from_academic_year_id,
            )
        ).first()
        if source is None:
            raise HTTPException(
                status_code=422,
                detail=f"{student.admission_number} has no enrollment in the from year",
            )
        if item.decision in {"promote", "repeat"}:
            target = (
                session.get(Classroom, item.to_classroom_id)
                if item.to_classroom_id
                else None
            )
            if target is None or target.school_id != tenant_of(session):
                raise HTTPException(
                    status_code=422,
                    detail="A promoted/repeated student needs a target section",
                )
        elif item.to_classroom_id is not None:
            raise HTTPException(
                status_code=422, detail="Only promote/repeat can carry a target section"
            )

        row = session.exec(
            select(PromotionDecision).where(
                PromotionDecision.batch_id == batch.id,
                PromotionDecision.student_id == student.id,
            )
        ).first()
        if row is None:
            row = PromotionDecision(
                batch_id=batch.id,
                student_id=student.id,
                from_enrollment_id=source.id,
                school_id=tenant_of(session),
            )
        row.decision = item.decision
        row.to_classroom_id = item.to_classroom_id
        row.roll_no = item.roll_no
        row.reason = item.reason
        row.decided_by_user_id = user_id
        row.decided_at = datetime.now(UTC)
        session.add(row)

    session.commit()
    return _batch_read(session, batch)


def apply_batch(
    session: Session, batch_id: UUID, user_id: UUID | None
) -> PromotionBatchRead:
    batch = _batch(session, batch_id)
    if batch.status != "draft":
        raise HTTPException(status_code=409, detail="This batch is no longer a draft")

    to_year = _year(session, batch.to_academic_year_id)
    decisions = session.exec(
        select(PromotionDecision).where(PromotionDecision.batch_id == batch.id)
    ).all()
    if not decisions:
        raise HTTPException(status_code=422, detail="The batch has no decisions")

    for row in decisions:
        student = session.get(Student, row.student_id)
        if student is None:
            raise HTTPException(
                status_code=422, detail="A student in this batch is missing"
            )
        source = session.get(Enrollment, row.from_enrollment_id)
        if source is None:
            raise HTTPException(
                status_code=422, detail="A source enrollment is missing"
            )

        if row.decision in {"promote", "repeat"}:
            enrollment = place_student(
                session,
                student,
                row.to_classroom_id,
                year=to_year,
                update_current=to_year.is_current,
                commit=False,
            )
            if enrollment is None:  # pragma: no cover - validated before apply
                raise HTTPException(
                    status_code=422, detail="Target section is required"
                )
            enrollment.previous_enrollment_id = source.id
            enrollment.roll_no = row.roll_no or enrollment.roll_no
            session.add(enrollment)
            row.to_enrollment_id = enrollment.id
        elif to_year.is_current:
            place_student(
                session,
                student,
                None,
                year=to_year,
                update_current=True,
                commit=False,
            )

        source.status = DECISION_STATUS[row.decision]
        source.left_on = date.today()
        row.applied_at = datetime.now(UTC)
        session.add(source)
        session.add(row)

    batch.status = "applied"
    batch.applied_by_user_id = user_id
    batch.applied_at = datetime.now(UTC)
    session.add(batch)
    session.commit()
    return _batch_read(session, batch)


def list_class_teachers(
    session: Session, academic_year_id: UUID | None = None
) -> list[ClassTeacherAssignmentRead]:
    statement = select(ClassTeacherAssignment)
    if academic_year_id is not None:
        statement = statement.where(
            ClassTeacherAssignment.academic_year_id == academic_year_id
        )
    rows = session.exec(
        statement.order_by(
            ClassTeacherAssignment.classroom_id,
            ClassTeacherAssignment.effective_from.desc(),
        )
    ).all()
    return [
        ClassTeacherAssignmentRead.model_validate(row, from_attributes=True)
        for row in rows
    ]


def assign_class_teacher(
    session: Session,
    payload: ClassTeacherAssignmentWrite,
    user_id: UUID | None,
) -> ClassTeacherAssignmentRead:
    year = _year(session, payload.academic_year_id)
    from app.domains.academic.classroom.academics.models import Classroom

    classroom = session.get(Classroom, payload.classroom_id)
    if classroom is None or classroom.school_id != tenant_of(session):
        raise HTTPException(status_code=404, detail="Class-section not found")

    effective_from = payload.effective_from or date.today()
    open_rows = session.exec(
        select(ClassTeacherAssignment).where(
            ClassTeacherAssignment.classroom_id == classroom.id,
            ClassTeacherAssignment.academic_year_id == year.id,
            ClassTeacherAssignment.effective_to.is_(None),
        )
    ).all()
    for old in open_rows:
        # A same-day re-assignment cannot close yesterday: keep the row's start date
        # as its end rather than violating the dates check.
        old.effective_to = max(old.effective_from, effective_from - timedelta(days=1))
        session.add(old)
    # Flush the close before opening the new row: the partial unique index allows
    # only one `effective_to IS NULL` row per class-section/year.
    session.flush()

    row = ClassTeacherAssignment(
        classroom_id=classroom.id,
        academic_year_id=year.id,
        teacher_id=payload.teacher_id,
        effective_from=effective_from,
        note=payload.note,
        assigned_by_user_id=user_id,
        school_id=tenant_of(session),
    )
    session.add(row)
    if year.is_current:
        classroom.class_teacher_id = payload.teacher_id
        session.add(classroom)
    session.commit()
    session.refresh(row)
    return ClassTeacherAssignmentRead.model_validate(row, from_attributes=True)
