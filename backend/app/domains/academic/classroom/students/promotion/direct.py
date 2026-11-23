"""Promote, retain, complete and de-promote students straight from the Students tab.

A student has **one enrollment per session year**. Promoting never edits last year's
record: it writes a new one in the next year and leaves a note ("Promoted to Class 4")
on the old one. Everything a request does runs in one transaction - the whole request
succeeds or none of it is saved.

* `promote`  - new record in the next year, a class the admin chose (default: the next
  class), `promotion_status = PROMOTED`.
* `retain`   - new record in the next year, the same class-section, `RETAINED`.
* `complete` - the highest class only: no new record; the current record becomes
  `COMPLETED`, so the student is in no class next year.
* `depromote` - undoes one of the three. It deletes the next-year record **and what
  hangs from it** (attendance, fees, marks) - only after the caller confirmed the
  counts that `preview_depromote` returned.

A student who already has a record in the target year is skipped and reported, never
promoted twice.
"""

from datetime import timedelta
from uuid import UUID

from fastapi import HTTPException
from sqlmodel import Session, select

from app.domains.academic.classroom.academics.models import (
    ClassName,
    Classroom,
    Section,
)
from app.domains.academic.classroom.academics.repository import ensure_room
from app.domains.academic.classroom.attendance.models import AttendanceRecord
from app.domains.academic.classroom.exams.models import (
    Exam,
    ExamPaper,
    Mark,
    MarksAudit,
)
from app.domains.academic.classroom.students.models import (
    PROMOTION_COMPLETED,
    PROMOTION_NEW_ADMISSION,
    PROMOTION_PROMOTED,
    PROMOTION_RETAINED,
    Enrollment,
    Student,
)
from app.domains.academic.classroom.students.placement import (
    place_student,
    sync_placements_to_year,
)
from app.domains.admin.settings import year_scope
from app.domains.admin.settings.academic_year_context import (
    academic_year_label,
    require_current_academic_year,
)
from app.domains.admin.settings.models import AcademicYear
from app.domains.finance.fees.models import FeeTransaction
from app.domains.operations.fees_structure.models import FeeStructure

from .models import PromotionDecision
from .schemas import (
    DepromotePreviewRead,
    DepromoteStudentRead,
    PromotionResultRead,
    PromotionSkippedRead,
)


def _years(session: Session) -> tuple[AcademicYear, AcademicYear]:
    """(the year on screen, the year that follows it). `409` when the next is not open."""
    current = require_current_academic_year(session)
    target = session.exec(
        select(AcademicYear).where(
            AcademicYear.start_date == current.end_date + timedelta(days=1)
        )
    ).first()
    if target is None:
        running = year_scope.todays_year(session)
        if running is not None and running.id == current.id:
            label = academic_year_label(current.start_date.year + 1)
            raise HTTPException(
                status_code=409,
                detail=(
                    f"The next session ({label}) is not created yet, so students cannot "
                    f"be promoted or retained. Create {label} from the year menu first."
                ),
            )
        raise HTTPException(
            status_code=409,
            detail=(
                f"The session after {current.name} cannot be created yet: only one year "
                "after the running year can be opened, so students cannot be promoted "
                "or retained from here."
            ),
        )
    return current, target


def _classes(session: Session) -> list[ClassName]:
    return list(session.exec(select(ClassName).order_by(ClassName.level)).all())


def _room(session: Session, room_id: UUID) -> tuple[Classroom, ClassName, Section]:
    room = session.get(Classroom, room_id)
    klass = session.get(ClassName, room.class_id) if room else None
    section = session.get(Section, room.section_id) if room else None
    if room is None or klass is None or section is None:
        raise HTTPException(status_code=409, detail="A student's class is missing.")
    return room, klass, section


def _room_in_class(
    session: Session, class_id: UUID, preferred_section_id: UUID
) -> Classroom | None:
    """The same section letter in `class_id` when it exists, else its first section."""
    rooms = list(session.exec(select(Classroom).where(Classroom.class_id == class_id)))
    if not rooms:
        return None
    for room in rooms:
        if room.section_id == preferred_section_id:
            return room
    names = {
        row.section_id: row.section_name for row in session.exec(select(Section)).all()
    }
    return sorted(rooms, key=lambda room: names.get(room.section_id, ""))[0]


def _names(session: Session, student_ids: list[UUID]) -> dict[UUID, str]:
    if not student_ids:
        return {}
    rows = session.exec(
        select(Student.id, Student.full_name).where(Student.id.in_(student_ids))
    ).all()
    return {sid: (name or "Student") for sid, name in rows}


def _enrollments(
    session: Session, year_id: UUID, student_ids: list[UUID]
) -> dict[UUID, Enrollment]:
    rows = session.exec(
        select(Enrollment).where(
            Enrollment.academic_year_id == year_id,
            Enrollment.student_id.in_(student_ids),
        )
    ).all()
    return {row.student_id: row for row in rows}


def _dedupe(student_ids: list[UUID]) -> list[UUID]:
    return list(dict.fromkeys(student_ids))


def _skip(skipped: list, names: dict, student_id: UUID, reason: str) -> None:
    skipped.append(
        PromotionSkippedRead(
            student_id=student_id, name=names.get(student_id, "Student"), reason=reason
        )
    )


def _move(
    session: Session,
    student_ids: list[UUID],
    *,
    keep_class: bool,
    target_class_id: UUID | None,
    target_section: str | None = None,
) -> PromotionResultRead:
    """Promote (`keep_class=False`) or retain (`keep_class=True`) a set of students."""
    student_ids = _dedupe(student_ids)
    current, target = _years(session)
    names = _names(session, student_ids)
    sources = _enrollments(session, current.id, student_ids)
    existing = _enrollments(session, target.id, student_ids)
    classes = _classes(session)
    by_level = {klass.class_id: index for index, klass in enumerate(classes)}

    chosen: ClassName | None = None
    if not keep_class and target_class_id is not None:
        chosen = next((k for k in classes if k.class_id == target_class_id), None)
        if chosen is None:
            raise HTTPException(status_code=404, detail="Class not found")

    # A section the admin picked (A-J): every student goes to that section of the class.
    # The class-section row is created the first time it is used, like at admission.
    chosen_section: Section | None = None
    if not keep_class and target_section:
        wanted = target_section.strip().lower()
        chosen_section = next(
            (
                row
                for row in session.exec(select(Section)).all()
                if row.section_name.lower() == wanted
            ),
            None,
        )
        if chosen_section is None:
            raise HTTPException(status_code=404, detail="Section not found")

    done = 0
    skipped: list[PromotionSkippedRead] = []
    try:
        for student_id in student_ids:
            source = sources.get(student_id)
            if source is None:
                _skip(skipped, names, student_id, f"Not enrolled in {current.name}.")
                continue
            if source.status != "active":
                _skip(skipped, names, student_id, "Is no longer on the roll.")
                continue
            if student_id in existing:
                _skip(
                    skipped,
                    names,
                    student_id,
                    f"Already has a record in {target.name}.",
                )
                continue
            if source.next_year_outcome is not None:
                _skip(skipped, names, student_id, "Already has a next-year outcome.")
                continue

            room, klass, section = _room(session, source.classroom_id)
            if keep_class:
                new_room, new_class = room, klass
            else:
                if chosen is not None:
                    if chosen.level <= klass.level:
                        _skip(
                            skipped,
                            names,
                            student_id,
                            f"{chosen.classname} is not above {klass.classname}; "
                            "a student can only be promoted to a higher class.",
                        )
                        continue
                    new_class = chosen
                else:
                    position = by_level.get(klass.class_id, -1)
                    if position < 0 or position + 1 >= len(classes):
                        _skip(
                            skipped,
                            names,
                            student_id,
                            "Is in the highest class - use Completed.",
                        )
                        continue
                    new_class = classes[position + 1]
                if chosen_section is not None:
                    new_room = ensure_room(
                        session, new_class.class_id, chosen_section.section_id
                    )
                else:
                    new_room = _room_in_class(
                        session, new_class.class_id, section.section_id
                    )
                if new_room is None:
                    _skip(
                        skipped,
                        names,
                        student_id,
                        f"{new_class.classname} has no section to move into.",
                    )
                    continue

            student = session.get(Student, student_id)
            enrollment = place_student(
                session,
                student,
                new_room.id,
                year=target,
                update_current=False,
                commit=False,
            )
            enrollment.promotion_status = (
                PROMOTION_RETAINED if keep_class else PROMOTION_PROMOTED
            )
            enrollment.previous_enrollment_id = source.id
            source.next_year_outcome = (
                f"Retained in {new_class.classname}"
                if keep_class
                else f"Promoted to {new_class.classname}"
            )
            session.add(enrollment)
            session.add(source)
            done += 1
        session.commit()
    except Exception:
        session.rollback()
        raise
    return PromotionResultRead(done=done, skipped=skipped)


def promote(
    session: Session,
    student_ids: list[UUID],
    target_class_id: UUID | None,
    target_section: str | None = None,
) -> PromotionResultRead:
    return _move(
        session,
        student_ids,
        keep_class=False,
        target_class_id=target_class_id,
        target_section=target_section,
    )


def retain(session: Session, student_ids: list[UUID]) -> PromotionResultRead:
    return _move(session, student_ids, keep_class=True, target_class_id=None)


def complete(session: Session, student_ids: list[UUID]) -> PromotionResultRead:
    """The highest class only: mark the current record COMPLETED, create nothing."""
    student_ids = _dedupe(student_ids)
    current = require_current_academic_year(session)
    names = _names(session, student_ids)
    sources = _enrollments(session, current.id, student_ids)
    classes = _classes(session)
    highest = classes[-1].class_id if classes else None

    done = 0
    skipped: list[PromotionSkippedRead] = []
    try:
        for student_id in student_ids:
            source = sources.get(student_id)
            if source is None:
                _skip(skipped, names, student_id, f"Not enrolled in {current.name}.")
                continue
            room = session.get(Classroom, source.classroom_id)
            if room is None or room.class_id != highest:
                _skip(
                    skipped,
                    names,
                    student_id,
                    "Only the highest class can be marked Completed.",
                )
                continue
            if source.next_year_outcome is not None:
                _skip(skipped, names, student_id, "Already has a next-year outcome.")
                continue
            source.promotion_status = PROMOTION_COMPLETED
            source.next_year_outcome = "Completed"
            session.add(source)
            done += 1
        session.commit()
    except Exception:
        session.rollback()
        raise
    return PromotionResultRead(done=done, skipped=skipped)


# ------------------------------------------------------------------------ de-promote


def _resolve(
    session: Session, current: AcademicYear, student_id: UUID
) -> tuple[Enrollment, Enrollment | None] | None:
    """(the record that carries the outcome, the next-year record it created, if any).

    The caller can stand in either year: on the old class (which holds the outcome) or
    on the new one (which holds `previous_enrollment_id`).
    """
    here = session.exec(
        select(Enrollment).where(
            Enrollment.student_id == student_id,
            Enrollment.academic_year_id == current.id,
        )
    ).first()
    if here is None:
        return None
    if here.next_year_outcome is not None:
        created = session.exec(
            select(Enrollment).where(Enrollment.previous_enrollment_id == here.id)
        ).first()
        return here, created
    if here.previous_enrollment_id is not None and here.promotion_status in (
        PROMOTION_PROMOTED,
        PROMOTION_RETAINED,
    ):
        source = session.get(Enrollment, here.previous_enrollment_id)
        if source is not None:
            return source, here
    return None


def _chain(session: Session, start: Enrollment) -> list[Enrollment]:
    """`start` and every later record promoted / retained out of it, nearest first.

    A student promoted in year 1 and retained in year 2 has a year-2 record whose
    `previous_enrollment_id` is the year-1 record, and a year-3 record linked to that.
    Taking the first promotion back has to take the whole chain with it.
    """
    chain = [start]
    seen = {start.id}
    while True:
        child = session.exec(
            select(Enrollment).where(Enrollment.previous_enrollment_id == chain[-1].id)
        ).first()
        if child is None or child.id in seen:
            return chain
        chain.append(child)
        seen.add(child.id)


def _hanging_data(
    session: Session, enrollment: Enrollment
) -> tuple[list[AttendanceRecord], list[FeeTransaction], list[Mark]]:
    """Everything the student has in `enrollment`'s year that dies with the record."""
    year = session.get(AcademicYear, enrollment.academic_year_id)
    attendance = list(
        session.exec(
            select(AttendanceRecord).where(
                AttendanceRecord.student_id == enrollment.student_id,
                AttendanceRecord.date >= year.start_date,
                AttendanceRecord.date <= year.end_date,
            )
        )
    )
    fees = list(
        session.exec(
            select(FeeTransaction)
            .join(FeeStructure, FeeStructure.id == FeeTransaction.fee_structure_id)
            .where(
                FeeTransaction.student_id == enrollment.student_id,
                FeeStructure.academic_year_id == enrollment.academic_year_id,
            )
        )
    )
    marks = list(
        session.exec(
            select(Mark)
            .join(ExamPaper, ExamPaper.id == Mark.exam_paper_id)
            .join(Exam, Exam.id == ExamPaper.exam_id)
            .where(
                Mark.student_id == enrollment.student_id,
                Exam.academic_year_id == enrollment.academic_year_id,
            )
        )
    )
    return attendance, fees, marks


def preview_depromote(
    session: Session, student_ids: list[UUID]
) -> DepromotePreviewRead:
    """What de-promoting would delete - nothing is changed."""
    student_ids = _dedupe(student_ids)
    current = require_current_academic_year(session)
    names = _names(session, student_ids)
    rows: list[DepromoteStudentRead] = []
    skipped: list[PromotionSkippedRead] = []
    for student_id in student_ids:
        found = _resolve(session, current, student_id)
        if found is None:
            _skip(skipped, names, student_id, "Nothing to undo.")
            continue
        source, created = found
        attendance = fees = marks = 0
        if created is not None:
            # Everything that grew out of the promotion goes with it, later years included.
            for record in _chain(session, created):
                a, f, m = _hanging_data(session, record)
                attendance += len(a)
                fees += len(f)
                marks += len(m)
        rows.append(
            DepromoteStudentRead(
                student_id=student_id,
                name=names.get(student_id, "Student"),
                attendance=attendance,
                fees=fees,
                marks=marks,
            )
        )
    return DepromotePreviewRead(
        students=rows,
        attendance=sum(row.attendance for row in rows),
        fees=sum(row.fees for row in rows),
        marks=sum(row.marks for row in rows),
        skipped=skipped,
    )


def _restored_status(session: Session, source: Enrollment) -> str:
    """The promotion status a COMPLETED record had before it was completed."""
    if source.previous_enrollment_id is None:
        return PROMOTION_NEW_ADMISSION
    earlier = session.get(Enrollment, source.previous_enrollment_id)
    here = session.get(Classroom, source.classroom_id)
    before = session.get(Classroom, earlier.classroom_id) if earlier else None
    if before is not None and here is not None and before.class_id == here.class_id:
        return PROMOTION_RETAINED
    return PROMOTION_PROMOTED


def depromote(
    session: Session, student_ids: list[UUID], confirmed: bool
) -> PromotionResultRead:
    """Undo promote / retain / complete. Deletes only after the counts were confirmed."""
    preview = preview_depromote(session, student_ids)
    if (preview.attendance or preview.fees or preview.marks) and not confirmed:
        raise HTTPException(
            status_code=409,
            detail=(
                f"This will permanently delete {preview.attendance} attendance "
                f"entries, {preview.fees} fee records and {preview.marks} marks. "
                "Confirm to continue."
            ),
        )

    current = require_current_academic_year(session)
    skipped = list(preview.skipped)
    done = 0
    try:
        for row in preview.students:
            source, created = _resolve(session, current, row.student_id)
            running_years: list[AcademicYear] = []
            if created is not None:
                # The farthest record first, so no record is deleted while another still
                # points at it.
                for record in reversed(_chain(session, created)):
                    attendance, fees, marks = _hanging_data(session, record)
                    mark_ids = [mark.id for mark in marks]
                    if mark_ids:
                        for audit in session.exec(
                            select(MarksAudit).where(MarksAudit.marks_id.in_(mark_ids))
                        ):
                            session.delete(audit)
                    for item in [*marks, *fees, *attendance]:
                        session.delete(item)
                    for decision in session.exec(
                        select(PromotionDecision).where(
                            (PromotionDecision.to_enrollment_id == record.id)
                            | (PromotionDecision.from_enrollment_id == record.id)
                        )
                    ):
                        if decision.to_enrollment_id == record.id:
                            decision.to_enrollment_id = None
                            session.add(decision)
                    session.flush()
                    year_row = session.get(AcademicYear, record.academic_year_id)
                    if year_row is not None and year_row.is_current:
                        running_years.append(year_row)
                    session.delete(record)
                    session.flush()
            if source.promotion_status == PROMOTION_COMPLETED:
                source.promotion_status = _restored_status(session, source)
            source.next_year_outcome = None
            session.add(source)
            session.flush()
            for year_row in running_years:
                sync_placements_to_year(session, year_row)
            done += 1
        session.commit()
    except Exception:
        session.rollback()
        raise
    return PromotionResultRead(done=done, skipped=skipped)


# --------------------------------------------------------------------------- demote


def demote(
    session: Session, student_ids: list[UUID], target_section: str
) -> PromotionResultRead:
    """Move students one class **down** in the year on screen, into a section the admin picks.

    The class is not chosen: it is the class right below the student's own (the one they
    came from). Only a New admission or Promoted record can be moved down - a retained or
    completed one already says what happened. The year's own enrollment is updated in
    place (one record per student per year), nothing is deleted.
    """
    student_ids = _dedupe(student_ids)
    year = require_current_academic_year(session)
    names = _names(session, student_ids)
    enrollments = _enrollments(session, year.id, student_ids)
    classes = _classes(session)
    position = {klass.class_id: index for index, klass in enumerate(classes)}

    wanted = target_section.strip().lower()
    section = next(
        (
            row
            for row in session.exec(select(Section)).all()
            if row.section_name.lower() == wanted
        ),
        None,
    )
    if section is None:
        raise HTTPException(status_code=404, detail="Section not found")

    real = year_scope.todays_year(session)
    done = 0
    skipped: list[PromotionSkippedRead] = []
    try:
        for student_id in student_ids:
            enrollment = enrollments.get(student_id)
            if enrollment is None or enrollment.status != "active":
                _skip(skipped, names, student_id, f"Not enrolled in {year.name}.")
                continue
            if enrollment.promotion_status not in (
                PROMOTION_NEW_ADMISSION,
                PROMOTION_PROMOTED,
            ):
                _skip(
                    skipped,
                    names,
                    student_id,
                    "Only a new admission or a promoted student can be moved down.",
                )
                continue
            if enrollment.next_year_outcome is not None:
                _skip(
                    skipped,
                    names,
                    student_id,
                    "Already has a next-year outcome; undo it first.",
                )
                continue
            room, klass, _section = _room(session, enrollment.classroom_id)
            index = position.get(klass.class_id, -1)
            if index <= 0:
                _skip(skipped, names, student_id, f"No class below {klass.classname}.")
                continue
            lower = classes[index - 1]
            new_room = ensure_room(session, lower.class_id, section.section_id)
            # Remember the first place the child sat, so Undo can put them back there.
            enrollment.moved_from_classroom_id = (
                enrollment.moved_from_classroom_id or enrollment.classroom_id
            )
            session.add(enrollment)
            student = session.get(Student, student_id)
            place_student(
                session,
                student,
                new_room.id,
                year=year,
                update_current=bool(real is not None and real.id == year.id),
                commit=False,
            )
            done += 1
        session.commit()
    except Exception:
        session.rollback()
        raise
    return PromotionResultRead(done=done, skipped=skipped)


# ------------------------------------------------------------------------------- undo


def _split_undo(
    session: Session, student_ids: list[UUID]
) -> tuple[list[UUID], list[UUID], list[UUID]]:
    """(moved down, promote/retain, nothing to undo) for the year on screen."""
    year = require_current_academic_year(session)
    enrollments = _enrollments(session, year.id, student_ids)
    moved: list[UUID] = []
    next_year: list[UUID] = []
    nothing: list[UUID] = []
    for student_id in student_ids:
        row = enrollments.get(student_id)
        if row is not None and row.moved_from_classroom_id is not None:
            moved.append(student_id)
        elif _resolve(session, year, student_id) is not None:
            next_year.append(student_id)
        else:
            nothing.append(student_id)
    return moved, next_year, nothing


def preview_undo(session: Session, student_ids: list[UUID]) -> DepromotePreviewRead:
    """What undoing would delete (nothing is changed); a move back deletes nothing."""
    student_ids = _dedupe(student_ids)
    moved, next_year, nothing = _split_undo(session, student_ids)
    preview = preview_depromote(session, next_year)
    names = _names(session, nothing)
    skipped = list(preview.skipped)
    for student_id in nothing:
        _skip(skipped, names, student_id, "Nothing to undo.")
    preview.skipped = skipped
    return preview


def undo(
    session: Session, student_ids: list[UUID], confirmed: bool
) -> PromotionResultRead:
    """Undo the last thing done to each student: a promotion, a retain or a move down.

    A promote / retain is taken back by removing the next-year record it created (after
    the admin confirmed what hangs from it); a move down puts the child back in the class-
    section they sat in. The whole request is one transaction.
    """
    student_ids = _dedupe(student_ids)
    moved, next_year, nothing = _split_undo(session, student_ids)
    # Refuse (409) before anything changes when data would be deleted unconfirmed.
    preview = preview_depromote(session, next_year)
    if (preview.attendance or preview.fees or preview.marks) and not confirmed:
        raise HTTPException(
            status_code=409,
            detail=(
                f"This will permanently delete {preview.attendance} attendance "
                f"entries, {preview.fees} fee records and {preview.marks} marks. "
                "Confirm to continue."
            ),
        )

    year = require_current_academic_year(session)
    real = year_scope.todays_year(session)
    names = _names(session, student_ids)
    enrollments = _enrollments(session, year.id, moved)
    skipped: list[PromotionSkippedRead] = []
    for student_id in nothing:
        _skip(skipped, names, student_id, "Nothing to undo.")

    done = 0
    try:
        for student_id in moved:
            row = enrollments[student_id]
            room = session.get(Classroom, row.moved_from_classroom_id)
            if room is None:
                _skip(
                    skipped,
                    names,
                    student_id,
                    "The class it came from no longer exists.",
                )
                continue
            student = session.get(Student, student_id)
            place_student(
                session,
                student,
                room.id,
                year=year,
                update_current=bool(real is not None and real.id == year.id),
                commit=False,
            )
            row.moved_from_classroom_id = None
            session.add(row)
            done += 1
        if next_year:
            result = depromote(
                session, next_year, confirmed
            )  # commits the whole request
            done += result.done
            skipped.extend(result.skipped)
        else:
            session.commit()
    except Exception:
        session.rollback()
        raise
    return PromotionResultRead(done=done, skipped=skipped)
