"""The cover workflow: what the board says, and the three writes that change it.

Reads and writes are kept apart on purpose. The board is one `GET` that answers
"who is away, what are their periods, which are still open" from the timetable and
the leave table; it writes **nothing**. A cover is recorded by `assign`, signed by
`approve`, and withdrawn by `remove` - each of them audited, because a cover is a
fact about a person's day that payroll, the register and a parent may later ask
about.

Four rules this module enforces:

* **a cover is for a slot the person actually teaches.** Assigning a substitute to a
  period that is not the absent teacher's on that weekday is a `409`: the board was
  built from the timetable, so a mismatch means the screen and the database disagree;
* **the engine has the last word.** `assign` re-runs the candidate check rather than
  trusting the id it was sent - the office may have picked a name before the person
  was marked on leave, and a `409` that names the reason is better than a cover
  nobody can walk into;
* **one adult per room.** `UNIQUE(school, period, date)` is caught and answered as a
  `409` naming the substitute already in it, not as a 500;
* **an HOD covers their own department.** The assignment right is department-scoped
  for a head of department, the same way `may_edit_profile` is - approval stays with
  the office.
"""

from datetime import date
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from app.domains.academic.classroom import labels as classroom_labels
from app.domains.academic.classroom.academics.models import Classroom
from app.domains.academic.classroom.students.promotion.class_teacher import (
    current_class_teacher_id,
)
from app.domains.admin.settings import calendar as school_calendar
from app.domains.admin.users.models import User
from app.domains.auth.models import utcnow
from app.domains.main.notifications import events
from app.domains.people.staff.models import Employee
from app.domains.people.teachers import labels
from app.domains.people.teachers import repository as teachers_repository
from app.domains.people.teachers import scope as teachers_scope
from app.domains.people.teachers.profile.repository import employee_names
from app.domains.people.teachers.profile.service import record_audit

from . import engine, repository
from .models import ClassAttendanceAccess, SubstitutionAssignment
from .schemas import (
    AbsentClassRead,
    ClassAttendanceAccessIn,
    ClassAttendanceAccessRead,
    SubstitutionAbsenceRead,
    SubstitutionAssignmentRead,
    SubstitutionBoardRead,
    SubstitutionCandidatesRead,
    SubstitutionPeriodRead,
)

#: The reason written for somebody the staff register marks Absent with no leave filed.
REGISTER_REASON = "Absent (staff register)"

#: Roles that may arrange cover. An HOD is included, and then narrowed to their own
#: department by `_department_allows`.
ASSIGN_ROLES = frozenset(
    {"system_admin", "director", "school_admin", "principal", "vice_principal", "hod"}
)

#: Roles that may sign a cover off. Approval is the office's, never a department's.
APPROVE_ROLES = frozenset(
    {"system_admin", "director", "school_admin", "principal", "vice_principal"}
)


# --- who may do what --------------------------------------------------------


def _require_assign(session: Session, user: User | None, absent: Employee) -> None:
    """`403` unless this caller may arrange cover for this person."""
    held = teachers_scope.held_roles(session, user)
    if not held & ASSIGN_ROLES:
        raise HTTPException(
            status_code=403, detail="Your role may not arrange substitutions."
        )
    if held & APPROVE_ROLES:
        return
    _department_allows(session, user, absent)


def _department_allows(session: Session, user: User | None, absent: Employee) -> None:
    """An HOD covers their own department and nobody else's (`403`)."""
    own = teachers_repository.get_teacher_by_user_id(session, user.id) if user else None
    if (
        own is None
        or not own.department
        or not absent.department
        or own.department.strip().lower() != absent.department.strip().lower()
    ):
        raise HTTPException(
            status_code=403,
            detail=(
                "A head of department arranges cover inside their own department only."
            ),
        )


def _require_approve(session: Session, user: User | None) -> None:
    """`403` unless this caller may sign a cover off."""
    if not teachers_scope.held_roles(session, user) & APPROVE_ROLES:
        raise HTTPException(
            status_code=403,
            detail="Your role may not approve a substitution - the office signs it off.",
        )


# --- reads ------------------------------------------------------------------


def _assignment_read(
    assignment: SubstitutionAssignment,
    *,
    absent_name: str,
    substitute_name: str,
) -> SubstitutionAssignmentRead:
    """One cover in the shape both the board and the write replies use."""
    return SubstitutionAssignmentRead(
        id=assignment.id,
        period_id=assignment.period_id,
        on_date=assignment.on_date,
        absent_employee_id=assignment.absent_employee_id,
        absent_name=absent_name,
        substitute_employee_id=assignment.substitute_employee_id,
        substitute_name=substitute_name,
        status=assignment.status,
        status_label=assignment.status,
        note=assignment.note,
        assigned_at=assignment.assigned_at,
        decided_at=assignment.decided_at,
    )


def _access_read(
    row: ClassAttendanceAccess, *, class_label: str, delegate_name: str
) -> ClassAttendanceAccessRead:
    """One hand-over in the shape the board and the write replies share."""
    return ClassAttendanceAccessRead(
        id=row.id,
        classroom_id=row.classroom_id,
        class_label=class_label,
        on_date=row.on_date,
        class_teacher_id=row.class_teacher_id,
        delegate_employee_id=row.delegate_employee_id,
        delegate_name=delegate_name,
        status=row.status,
        note=row.note,
        assigned_at=row.assigned_at,
        decided_at=row.decided_at,
    )


def board(session: Session, on_date: date, user: User | None) -> SubstitutionBoardRead:
    """The day's cover sheet: the absences, their periods, what is still open.

    Absences come from **two** places and both are shown: an approved staff leave
    covering the day (the ordinary case) and any absence somebody wrote down (a
    training day, an official duty). The periods are the timetable's, so a period
    added this morning appears without anybody re-opening a screen.

    The reader's scope narrows the absences - a teacher-only account sees its own -
    and a weekday with no periods at all is reported as `timetable_empty` rather than
    as "0 open", which would read like a finished job.
    """
    context = engine.build_context(session, on_date)
    if context.closed_reason:
        # A weekly off or a holiday: no lessons, so nothing to cover and nobody to offer.
        return SubstitutionBoardRead(
            on_date=on_date,
            weekday=labels.weekday_label(on_date),
            is_open=False,
            closed_reason=context.closed_reason,
        )
    stored = {row.employee_id: row for row in repository.requests_on(session, on_date)}

    visible = teachers_scope.visible_employee_ids(session, user)
    # Away = approved leave, marked Absent on the register (only worth a line if they teach
    # that day), or an absence somebody wrote down.
    class_teachers = repository.class_teacher_ids(session)
    away = (
        set(context.on_leave)
        | set(stored)
        | (context.register_absent & (set(context.periods_by_teacher) | class_teachers))
    )
    absent_ids = [
        employee_id
        for employee_id in sorted(away)
        if visible is None or employee_id in visible
    ]

    people = repository.employees(session, absent_ids)
    names = employee_names(session, absent_ids)
    rooms_of = repository.rooms_of_class_teachers(session, absent_ids)
    room_labels = classroom_labels.labels_by_section(
        session, [room for rooms in rooms_of.values() for room in rooms]
    )

    periods = [
        period
        for employee_id in absent_ids
        for period in context.periods_by_teacher.get(employee_id, [])
    ]
    subjects = repository.subject_names(
        session, [period.classroom_subject_id for period in periods]
    )
    class_labels = classroom_labels.labels_by_section(
        session, [period.classroom_id for period in periods]
    )
    substitute_names = employee_names(
        session,
        [
            assignment.substitute_employee_id
            for assignment in context.assignments.values()
        ],
    )

    rows: list[SubstitutionPeriodRead] = []
    absences: list[SubstitutionAbsenceRead] = []
    covered = 0
    for employee_id in absent_ids:
        employee = people.get(employee_id)
        if employee is None:
            continue
        leave_type = context.on_leave.get(employee_id)
        request = stored.get(employee_id)
        own_periods = sorted(
            context.periods_by_teacher.get(employee_id, []),
            key=lambda period: period.start_time,
        )

        open_periods = 0
        for period in own_periods:
            assignment = context.assignments.get(period.id)
            if assignment is None:
                open_periods += 1
            else:
                covered += 1
            rows.append(
                SubstitutionPeriodRead(
                    period_id=period.id,
                    classroom_id=period.classroom_id,
                    slot=labels.period_label(period.start_time, period.end_time),
                    start_time=period.start_time,
                    end_time=period.end_time,
                    classroom_subject_id=period.classroom_subject_id,
                    subject=subjects.get(period.classroom_subject_id, ""),
                    class_label=class_labels.get(period.classroom_id, ""),
                    room=period.room,
                    absent_employee_id=employee.id,
                    absent_name=names.get(employee.id) or employee.employee_code,
                    assignment=(
                        None
                        if assignment is None
                        else _assignment_read(
                            assignment,
                            absent_name=names.get(employee.id)
                            or employee.employee_code,
                            substitute_name=substitute_names.get(
                                assignment.substitute_employee_id, ""
                            ),
                        )
                    ),
                )
            )

        if leave_type:
            source, reason = "leave", leave_type
        elif employee_id in context.register_absent:
            source = "register"
            reason = (request.reason if request else None) or REGISTER_REASON
        else:
            source, reason = "written", (request.reason if request else "Absent")

        absences.append(
            SubstitutionAbsenceRead(
                employee_id=employee.id,
                name=names.get(employee.id) or employee.employee_code,
                employee_code=employee.employee_code,
                department=employee.department,
                reason=reason,
                class_teacher_of=[
                    room_labels.get(room, "") for room in rooms_of.get(employee_id, [])
                ],
                source=source,
                leave_type=leave_type,
                note=request.note if request else None,
                open_periods=open_periods,
                total_periods=len(own_periods),
            )
        )

    # The class-sections an away teacher runs (as class teacher) or has a period in: each
    # needs somebody to take its attendance. The "same teacher" choice is whoever already
    # covers one of its periods. A class teacher comes first when both are away.
    all_labels = {**room_labels, **class_labels}
    accesses = {row.classroom_id: row for row in repository.accesses_on(session, on_date)}
    delegate_names = employee_names(
        session, [row.delegate_employee_id for row in accesses.values()]
    )
    behalf: dict[UUID, tuple[UUID, bool]] = {}  # room -> (away teacher, is class teacher)
    for employee_id in absent_ids:
        for room_id in rooms_of.get(employee_id, []):
            behalf[room_id] = (employee_id, True)
    for employee_id in absent_ids:
        for period in context.periods_by_teacher.get(employee_id, []):
            behalf.setdefault(period.classroom_id, (employee_id, False))

    classes: list[AbsentClassRead] = []
    for room_id, (employee_id, is_class_teacher) in behalf.items():
        suggested = next(
            (
                context.assignments[period.id]
                for other_id in absent_ids
                for period in sorted(
                    context.periods_by_teacher.get(other_id, []),
                    key=lambda item: item.start_time,
                )
                if period.classroom_id == room_id and period.id in context.assignments
            ),
            None,
        )
        row = accesses.get(room_id)
        classes.append(
            AbsentClassRead(
                classroom_id=room_id,
                class_label=all_labels.get(room_id, ""),
                away_teacher_id=employee_id,
                away_teacher_name=names.get(employee_id, ""),
                is_class_teacher=is_class_teacher,
                suggested_employee_id=(
                    suggested.substitute_employee_id if suggested else None
                ),
                suggested_name=(
                    substitute_names.get(suggested.substitute_employee_id)
                    if suggested
                    else None
                ),
                access=(
                    None
                    if row is None
                    else _access_read(
                        row,
                        class_label=all_labels.get(room_id, ""),
                        delegate_name=delegate_names.get(row.delegate_employee_id, ""),
                    )
                ),
            )
        )
    classes.sort(key=lambda item: (item.class_label, item.away_teacher_name))

    return SubstitutionBoardRead(
        on_date=on_date,
        weekday=labels.weekday_label(on_date),
        classes=classes,
        absences=absences,
        periods=rows,
        total=len(rows),
        covered=covered,
        open=len(rows) - covered,
        # "Nobody is away" and "this school has no timetable on Mondays" are
        # different answers, and a screen that printed "0 open" for both would hide
        # a missing timetable behind a quiet day.
        timetable_empty=not context.periods_by_teacher,
    )


def _require_school_open(session: Session, on_date: date) -> None:
    """`409` on a day the school is closed: there is no lesson to cover."""
    reason = school_calendar.closed_reason(session, on_date)
    if reason:
        raise HTTPException(
            status_code=409,
            detail=(
                f"The school is closed on {on_date} ({reason}), so there is "
                "no period to cover that day."
            ),
        )


def _period_and_absent(
    session: Session, period_id: UUID, on_date: date, user: User | None
) -> tuple:
    """The slot, and the person who teaches it - `404` when either is out of scope."""
    _require_school_open(session, on_date)
    period = repository.period(session, period_id)
    if period is None:
        raise HTTPException(status_code=404, detail="Timetable period not found")
    if repository.weekday_key(on_date) != period.day_of_week:
        raise HTTPException(
            status_code=409,
            detail=(
                f"That period is not taught on a {labels.weekday_label(on_date)} - "
                "the cover is for a weekday the timetable actually has."
            ),
        )
    absent = repository.employees(session, [period.teacher_id]).get(period.teacher_id)
    if absent is None:
        raise HTTPException(status_code=404, detail="Teacher not found")
    visible = teachers_scope.visible_employee_ids(session, user)
    if visible is not None and absent.id not in visible:
        raise HTTPException(status_code=404, detail="Teacher not found")
    return period, absent


def candidates_for(
    session: Session, period_id: UUID, on_date: date, user: User | None
) -> SubstitutionCandidatesRead:
    """Who can cover this period - with the reason for every yes and every no."""
    period, absent = _period_and_absent(session, period_id, on_date, user)
    context = engine.build_context(session, on_date)

    subject_name = repository.subject_names(session, [period.classroom_subject_id]).get(
        period.classroom_subject_id, ""
    )
    class_labels = classroom_labels.labels_by_section(session, [period.classroom_id])
    existing = context.assignments.get(period.id)
    names = employee_names(
        session,
        [absent.id, existing.substitute_employee_id]
        if existing is not None
        else [absent.id],
    )
    absent_name = names.get(absent.id) or absent.employee_code

    eligible, blocked = (
        ([], [])
        if existing is not None
        else engine.candidates(session, period=period, absent=absent, context=context)
    )
    return SubstitutionCandidatesRead(
        period_id=period.id,
        on_date=on_date,
        slot=labels.period_label(period.start_time, period.end_time),
        subject=subject_name,
        class_label=class_labels.get(period.classroom_id, ""),
        candidates=eligible,
        blocked=blocked,
        assignment=(
            None
            if existing is None
            else _assignment_read(
                existing,
                absent_name=absent_name,
                substitute_name=names.get(existing.substitute_employee_id, ""),
            )
        ),
    )


def _notify(
    session: Session,
    *,
    user_id: UUID | None,
    title: str,
    body: str,
    event: str = events.EVENT_SUBSTITUTION_ASSIGNED,
    dedupe_key: str | None = None,
) -> None:
    """Tell the person who has to walk into that room.

    A cover nobody told the substitute about is worse than no cover: the class is
    still empty *and* the office believes it is not. The message goes through
    `notifications.events.notify` like every other message (Phase 3), and it stays in
    the caller's transaction (`commit=False`), so there is no state where the cover
    exists without the person being told.
    """
    if user_id is None:
        return
    events.notify(
        session,
        event=event,
        recipients=[user_id],
        title=title,
        body=body,
        entity_type="substitution_assignment",
        dedupe_key=dedupe_key,
        commit=False,
    )


def _write_read(
    session: Session, assignment: SubstitutionAssignment
) -> SubstitutionAssignmentRead:
    """The reply shape for a write: both names resolved, status as stored."""
    names = employee_names(
        session, [assignment.absent_employee_id, assignment.substitute_employee_id]
    )
    return _assignment_read(
        assignment,
        absent_name=names.get(assignment.absent_employee_id, ""),
        substitute_name=names.get(assignment.substitute_employee_id, ""),
    )


def assign(session: Session, payload, user: User | None) -> SubstitutionAssignmentRead:
    """Arrange cover for one period, and tell the substitute.

    The candidate check is re-run here rather than trusted from the screen: the
    office may have had the dialog open since before the colleague was marked on
    leave, and `409` naming that is better than a cover that cannot happen.
    """
    period, absent = _period_and_absent(
        session, payload.period_id, payload.on_date, user
    )
    if period.teacher_id != payload.absent_employee_id:
        raise HTTPException(
            status_code=409,
            detail=(
                "That period is not this person's on that weekday, so there is "
                "nothing of theirs to cover."
            ),
        )
    _require_assign(session, user, absent)

    context = engine.build_context(session, payload.on_date)
    stored = repository.request_on(
        session, employee_id=absent.id, on_date=payload.on_date
    )
    leave_type = context.on_leave.get(absent.id)
    if (
        leave_type is None
        and stored is None
        and absent.id not in context.register_absent
    ):
        raise HTTPException(
            status_code=404,
            detail=(
                "That person has no absence recorded on that date - an approved leave, "
                "an Absent mark on the staff register or an absence the office wrote "
                "down is what needs covering."
            ),
        )

    substitute = repository.employees(session, [payload.substitute_employee_id]).get(
        payload.substitute_employee_id
    )
    if substitute is None:
        raise HTTPException(status_code=404, detail="Teacher not found")

    existing = context.assignments.get(period.id)
    if existing is not None:
        names = employee_names(session, [existing.substitute_employee_id])
        raise HTTPException(
            status_code=409,
            detail=(
                f"That period is already covered by "
                f"{names.get(existing.substitute_employee_id, 'a colleague')} on "
                f"{payload.on_date}. Withdraw that cover first."
            ),
        )

    eligible, blocked = engine.candidates(
        session, period=period, absent=absent, context=context
    )
    if not any(row.employee_id == substitute.id for row in eligible):
        why = next(
            (row.reason for row in blocked if row.employee_id == substitute.id),
            None,
        )
        subject_name = repository.subject_names(
            session, [period.classroom_subject_id]
        ).get(period.classroom_subject_id, "this subject")
        raise HTTPException(
            status_code=409,
            detail=(
                f"{substitute.employee_code} cannot take this period: "
                f"{why or f'{substitute.employee_code} is not available for {subject_name}'}."
            ),
        )

    request = repository.ensure_request(
        session,
        employee_id=absent.id,
        on_date=payload.on_date,
        reason=leave_type or (stored.reason if stored else REGISTER_REASON),
        note=payload.note,
        leave_request_id=None,
        user_id=user.id if user is not None else None,
    )
    session.add(request)
    session.flush()

    assignment = SubstitutionAssignment(
        request_id=request.id,
        period_id=period.id,
        on_date=payload.on_date,
        absent_employee_id=absent.id,
        substitute_employee_id=substitute.id,
        status=labels.ASSIGNED,
        note=payload.note,
        assigned_by_user_id=user.id if user is not None else None,
    )
    session.add(assignment)
    try:
        session.flush()
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=409,
            detail="That period already has a substitute on that date.",
        ) from None

    names = employee_names(session, [absent.id, substitute.id])
    record_audit(
        session,
        employee_id=absent.id,
        section="substitution",
        action="created",
        row_id=assignment.id,
        summary=(
            f"{payload.on_date}: "
            f"{labels.period_label(period.start_time, period.end_time)} covered by "
            f"{names.get(substitute.id, substitute.employee_code)}"
        ),
        user=user,
        commit=False,
    )
    _notify(
        session,
        user_id=substitute.user_id,
        title="Substitution assigned",
        body=(
            f"You are covering {names.get(absent.id, absent.employee_code)}'s period "
            f"{labels.period_label(period.start_time, period.end_time)} on "
            f"{payload.on_date}. The office will confirm it."
        ),
        event=events.EVENT_SUBSTITUTION_ASSIGNED,
        dedupe_key=f"substitution:{assignment.id}:assigned",
    )
    session.commit()
    session.refresh(assignment)
    return _write_read(session, assignment)


def _visible_assignment(
    session: Session, assignment_id: UUID, user: User | None
) -> SubstitutionAssignment:
    """The cover, if this caller may see the person it is for (`404` otherwise)."""
    assignment = repository.assignment(session, assignment_id)
    if assignment is None:
        raise HTTPException(status_code=404, detail="Substitution not found")
    visible = teachers_scope.visible_employee_ids(session, user)
    if visible is not None and assignment.absent_employee_id not in visible:
        raise HTTPException(status_code=404, detail="Substitution not found")
    return assignment


def approve(
    session: Session, assignment_id: UUID, note: str | None, user: User | None
) -> SubstitutionAssignmentRead:
    """Sign a cover off. Approving one that is already approved is a no-op.

    Idempotent for the same reason a leave decision is (Phase 6): a double click, or
    two clerks with the same screen open, must not write a second audit line or move
    `decided_at`. The substitute is told on assignment, not here - a second message
    saying "still true" is noise, and the audit trail already records who signed it.
    """
    assignment = _visible_assignment(session, assignment_id, user)
    _require_approve(session, user)

    if assignment.status == labels.APPROVED:
        return _write_read(session, assignment)

    period = repository.period(session, assignment.period_id)
    assignment.status = labels.APPROVED
    assignment.decided_by_user_id = user.id if user is not None else None
    assignment.decided_at = utcnow()
    if note is not None:
        assignment.note = note
    session.add(assignment)
    record_audit(
        session,
        employee_id=assignment.absent_employee_id,
        section="substitution",
        action="updated",
        row_id=assignment.id,
        summary=(
            f"{assignment.on_date}: cover approved"
            + (
                f" ({labels.period_label(period.start_time, period.end_time)})"
                if period is not None
                else ""
            )
        ),
        user=user,
        commit=False,
    )
    session.commit()
    session.refresh(assignment)
    return _write_read(session, assignment)


def remove(
    session: Session, assignment_id: UUID, note: str | None, user: User | None
) -> None:
    """Withdraw a cover, freeing the slot for somebody else.

    Deleted rather than marked `Cancelled`: `UNIQUE(school, period, date)` is what
    stops two adults being sent to one room, and a cancelled row would hold that key
    and block the replacement the office is trying to record. The audit row is the
    history; the substitute is told, because they may already have planned around it.
    """
    assignment = _visible_assignment(session, assignment_id, user)
    absent = repository.employees(session, [assignment.absent_employee_id]).get(
        assignment.absent_employee_id
    )
    if absent is None:
        raise HTTPException(status_code=404, detail="Teacher not found")
    _require_assign(session, user, absent)

    period = repository.period(session, assignment.period_id)
    names = employee_names(
        session, [assignment.absent_employee_id, assignment.substitute_employee_id]
    )
    record_audit(
        session,
        employee_id=assignment.absent_employee_id,
        section="substitution",
        action="deleted",
        row_id=assignment.id,
        summary=(
            f"{assignment.on_date}: cover by "
            f"{names.get(assignment.substitute_employee_id, 'a colleague')} withdrawn"
            + (
                f" ({labels.period_label(period.start_time, period.end_time)})"
                if period is not None
                else ""
            )
            + (f" - {note}" if note else "")
        ),
        user=user,
        commit=False,
    )
    substitute = repository.employees(session, [assignment.substitute_employee_id]).get(
        assignment.substitute_employee_id
    )
    _notify(
        session,
        user_id=substitute.user_id if substitute is not None else None,
        title="Substitution withdrawn",
        body=(
            f"The cover for {names.get(assignment.absent_employee_id, 'a colleague')}"
            f" on {assignment.on_date}"
            + (
                f" at {labels.period_label(period.start_time, period.end_time)}"
                if period is not None
                else ""
            )
            + " has been withdrawn. You are not expected in that period."
        ),
        event=events.EVENT_SUBSTITUTION_WITHDRAWN,
        dedupe_key=f"substitution:{assignment.id}:withdrawn",
    )
    session.delete(assignment)
    session.commit()


# --- who takes a class's attendance while its class teacher is away -----------


def _write_access_read(session: Session, row: ClassAttendanceAccess) -> ClassAttendanceAccessRead:
    labels_by_room = classroom_labels.labels_by_section(session, [row.classroom_id])
    names = employee_names(session, [row.delegate_employee_id])
    return _access_read(
        row,
        class_label=labels_by_room.get(row.classroom_id, ""),
        delegate_name=names.get(row.delegate_employee_id, ""),
    )


def set_attendance_access(
    session: Session, payload: ClassAttendanceAccessIn, user: User | None
) -> ClassAttendanceAccessRead:
    """Hand one class-section's attendance on one day to a teacher (or change who has it).

    Only for a class that an **away teacher runs or has a period in** that day (approved
    leave, or marked Absent on the attendance register): while its teachers are in school the
    register is theirs. The class teacher, when they are the one away, is who the hand-over is
    for; otherwise it is the away teacher whose period in that class is being covered.
    The chosen teacher must be an active teacher who is in school themselves - somebody on
    leave or marked Absent cannot take a register. Choosing again replaces the person and
    **resets the approval**: the new teacher has no access until the office signs them.
    Nothing here widens what the teacher can do in any other class.
    """
    _require_school_open(session, payload.on_date)

    room = session.get(Classroom, payload.classroom_id)
    if room is None:
        raise HTTPException(status_code=404, detail="Class-section not found")
    context = engine.build_context(session, payload.on_date)
    stored = {row.employee_id for row in repository.requests_on(session, payload.on_date)}
    away_ids = set(context.on_leave) | context.register_absent | stored
    class_teacher_id = current_class_teacher_id(session, room.id)
    if class_teacher_id is not None and class_teacher_id in away_ids:
        behalf_id: UUID | None = class_teacher_id
    else:
        behalf_id = next(
            (
                employee_id
                for employee_id in sorted(away_ids)
                if any(
                    period.classroom_id == room.id
                    for period in context.periods_by_teacher.get(employee_id, [])
                )
            ),
            None,
        )
    if behalf_id is None:
        raise HTTPException(
            status_code=409,
            detail=(
                "Nobody who runs or teaches this class is away on that date, so its "
                "register is still taken as usual."
            ),
        )
    absent = repository.employees(session, [behalf_id]).get(behalf_id)
    if absent is None:
        raise HTTPException(status_code=404, detail="Teacher not found")
    visible = teachers_scope.visible_employee_ids(session, user)
    if visible is not None and absent.id not in visible:
        raise HTTPException(status_code=404, detail="Teacher not found")
    _require_assign(session, user, absent)

    delegate = repository.employees(session, [payload.delegate_employee_id]).get(
        payload.delegate_employee_id
    )
    if delegate is None:
        raise HTTPException(status_code=404, detail="Teacher not found")
    if delegate.id == absent.id:
        raise HTTPException(
            status_code=409, detail="Choose a colleague, not the teacher who is away."
        )
    if delegate.id not in set(repository.teacher_pool(session)):
        raise HTTPException(
            status_code=409, detail="That person is not an active teacher."
        )
    leave_type = context.on_leave.get(delegate.id)
    if leave_type:
        raise HTTPException(
            status_code=409,
            detail=f"{delegate.employee_code} is on approved {leave_type} leave that day.",
        )
    if delegate.id in context.register_absent:
        raise HTTPException(
            status_code=409,
            detail=f"{delegate.employee_code} is marked absent that day.",
        )

    row = repository.access_for(session, room.id, payload.on_date)
    created = row is None
    if row is None:
        row = ClassAttendanceAccess(
            classroom_id=room.id,
            on_date=payload.on_date,
            class_teacher_id=absent.id,
            delegate_employee_id=delegate.id,
            status=labels.ASSIGNED,
            note=payload.note,
            assigned_by_user_id=user.id if user is not None else None,
        )
    else:
        row.class_teacher_id = absent.id
        row.delegate_employee_id = delegate.id
        row.status = labels.ASSIGNED
        row.note = payload.note
        row.assigned_by_user_id = user.id if user is not None else None
        row.assigned_at = utcnow()
        row.decided_by_user_id = None
        row.decided_at = None
    session.add(row)
    try:
        session.flush()
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=409,
            detail="That class-section already has its attendance handed over for that date.",
        ) from None

    room_label = classroom_labels.labels_by_section(session, [room.id]).get(room.id, "")
    names = employee_names(session, [absent.id, delegate.id])
    record_audit(
        session,
        employee_id=absent.id,
        section="substitution",
        action="created" if created else "updated",
        row_id=row.id,
        summary=(
            f"{payload.on_date}: {room_label} attendance handed to "
            f"{names.get(delegate.id, delegate.employee_code)}"
        ),
        user=user,
        commit=False,
    )
    _notify(
        session,
        user_id=delegate.user_id,
        title="Class attendance assigned",
        body=(
            f"You are to take {room_label} attendance on {payload.on_date} while "
            f"{names.get(absent.id, absent.employee_code)} is away. The office will "
            "confirm it; you can open the class once it is approved."
        ),
        event=events.EVENT_SUBSTITUTION_ASSIGNED,
        dedupe_key=f"attendance-access:{row.id}:{delegate.id}:assigned",
    )
    session.commit()
    session.refresh(row)
    return _write_access_read(session, row)


def _visible_access(
    session: Session, access_id: UUID, user: User | None
) -> ClassAttendanceAccess:
    """The hand-over, if this caller may see the class teacher it is for (`404` otherwise)."""
    row = repository.access(session, access_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Attendance hand-over not found")
    visible = teachers_scope.visible_employee_ids(session, user)
    if visible is not None and row.class_teacher_id not in visible:
        raise HTTPException(status_code=404, detail="Attendance hand-over not found")
    return row


def approve_attendance_access(
    session: Session, access_id: UUID, user: User | None
) -> ClassAttendanceAccessRead:
    """Sign a hand-over off: from now the teacher may open that class and save its register.

    The office's decision (the same right that signs a cover off). Approving one that is
    already approved is a no-op - no second audit line, no second message.
    """
    row = _visible_access(session, access_id, user)
    _require_approve(session, user)
    if row.status == labels.APPROVED:
        return _write_access_read(session, row)

    row.status = labels.APPROVED
    row.decided_by_user_id = user.id if user is not None else None
    row.decided_at = utcnow()
    session.add(row)
    room_label = classroom_labels.labels_by_section(session, [row.classroom_id]).get(
        row.classroom_id, ""
    )
    delegate = repository.employees(session, [row.delegate_employee_id]).get(
        row.delegate_employee_id
    )
    record_audit(
        session,
        employee_id=row.class_teacher_id,
        section="substitution",
        action="updated",
        row_id=row.id,
        summary=f"{row.on_date}: {room_label} attendance hand-over approved",
        user=user,
        commit=False,
    )
    _notify(
        session,
        user_id=delegate.user_id if delegate is not None else None,
        title="Class attendance approved",
        body=(
            f"You can now take {room_label} attendance on {row.on_date}. It is in "
            "your Classroom list for the day."
        ),
        event=events.EVENT_SUBSTITUTION_ASSIGNED,
        dedupe_key=f"attendance-access:{row.id}:approved",
    )
    session.commit()
    session.refresh(row)
    return _write_access_read(session, row)


def remove_attendance_access(
    session: Session, access_id: UUID, user: User | None
) -> None:
    """Take the hand-over back: the teacher loses that class's register at once."""
    row = _visible_access(session, access_id, user)
    absent = repository.employees(session, [row.class_teacher_id]).get(
        row.class_teacher_id
    )
    if absent is None:
        raise HTTPException(status_code=404, detail="Teacher not found")
    _require_assign(session, user, absent)

    room_label = classroom_labels.labels_by_section(session, [row.classroom_id]).get(
        row.classroom_id, ""
    )
    delegate = repository.employees(session, [row.delegate_employee_id]).get(
        row.delegate_employee_id
    )
    record_audit(
        session,
        employee_id=row.class_teacher_id,
        section="substitution",
        action="deleted",
        row_id=row.id,
        summary=f"{row.on_date}: {room_label} attendance hand-over withdrawn",
        user=user,
        commit=False,
    )
    _notify(
        session,
        user_id=delegate.user_id if delegate is not None else None,
        title="Class attendance withdrawn",
        body=(
            f"You are no longer to take {room_label} attendance on {row.on_date}."
        ),
        event=events.EVENT_SUBSTITUTION_WITHDRAWN,
        dedupe_key=f"attendance-access:{row.id}:withdrawn",
    )
    session.delete(row)
    session.commit()
