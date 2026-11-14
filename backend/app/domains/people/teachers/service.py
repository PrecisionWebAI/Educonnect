"""The read models behind the Teachers & Staff screen.

Four tabs read from here (directory, workload, leave, performance) plus the
summary tiles above them, and they all describe the same set of people: whoever
is on the teaching roll. That is why the employee list is read once by
`repository.teaching_employees` and shared - a tile that counted a different set
from the table underneath it is how the old screen ended up reporting "12 active"
over a list of nine.

Cost is bounded per request, not per row: each fact (subjects, class-sections,
timetable load, today's leave, ratings) is one statement for the whole page
instead of one per teacher.
"""

from datetime import date
from uuid import UUID

from fastapi import HTTPException
from sqlmodel import Session, select

from app.domains.academic.classroom.academics.models import (
    Classroom,
    Subject,
    SubjectTeacher,
)
from app.domains.academic.classroom.labels import labels_by_section
from app.domains.admin.users import repository as user_repository
from app.domains.admin.users.models import User
from app.domains.people.staff.models import Employee

from . import labels, repository, scope
from .models import TeacherSubject
from .profile import repository as profile_repository
from .profile import service as profile_service
from .profile.schemas import AuditRead
from .schemas import (
    StaffProfile,
    StaffSummary,
    TeacherCreate,
    TeacherRead,
    WorkloadMatrixRow,
)
from .workload import repository as workload_repository


def _reads(session: Session, teachers: list[Employee]) -> list[TeacherRead]:
    """One directory row per employee, from a fixed number of reads.

    Seven statements for the whole page (users, subjects, timetable load, the two
    assignment tables, the class-section labels, today's leave). Reading them per
    teacher was ~550 round trips on a seeded school.
    """
    if not teachers:
        return []

    teacher_ids = [teacher.id for teacher in teachers if teacher.id is not None]
    user_ids = [teacher.user_id for teacher in teachers if teacher.user_id]
    users = (
        {
            user.id: user
            for user in session.exec(select(User).where(User.id.in_(user_ids))).all()
        }
        if user_ids
        else {}
    )

    subjects: dict[UUID, list[str]] = {}
    for teacher_id, name in session.exec(
        select(TeacherSubject.teacher_id, Subject.name)
        .join(Subject, TeacherSubject.subject_id == Subject.id)
        .where(TeacherSubject.teacher_id.in_(teacher_ids))
        .order_by(Subject.name)  # type: ignore[arg-type]
    ).all():
        subjects.setdefault(teacher_id, []).append(name)

    periods = repository.period_counts(session, teacher_ids)

    # A teacher is attached to a class-section either as its class teacher or by
    # taking a subject in it; both are collected before the labels are read once.
    rooms: dict[UUID, set[UUID]] = {}
    for teacher_id, room_id in session.exec(
        select(Classroom.class_teacher_id, Classroom.id).where(
            Classroom.class_teacher_id.in_(teacher_ids)
        )
    ).all():
        rooms.setdefault(teacher_id, set()).add(room_id)
    for teacher_id, room_id in session.exec(
        select(SubjectTeacher.teacher_id, SubjectTeacher.classroom_id).where(
            SubjectTeacher.teacher_id.in_(teacher_ids)
        )
    ).all():
        rooms.setdefault(teacher_id, set()).add(room_id)
    room_labels = labels_by_section(
        session, [room for room_ids in rooms.values() for room in room_ids]
    )

    on_leave = repository.approved_leave_today(session, date.today())

    reads: list[TeacherRead] = []
    for teacher in teachers:
        user = users.get(teacher.user_id) if teacher.user_id else None
        reads.append(
            TeacherRead(
                id=teacher.id,
                user_id=teacher.user_id,
                department=teacher.department,
                qualification=teacher.qualification,
                joining_date=teacher.joining_date,
                staffCode=teacher.employee_code,
                name=user.full_name if user else "",
                # No fallback to the department: "takes no subject" and "sits in
                # the Science department" are two different facts, and the table
                # has a column for each.
                subject=", ".join(subjects.get(teacher.id, [])),
                phone=teacher.phone or "",
                email=teacher.email or (user.email if user else ""),
                status=labels.employee_status(
                    deactivated_at=teacher.deactivated_at,
                    left_on=teacher.left_on,
                    on_leave=teacher.user_id in on_leave,
                ),
                classes=sorted(
                    {
                        room_labels[room]
                        for room in rooms.get(teacher.id, set())
                        if room in room_labels
                    }
                ),
                workload=periods.get(teacher.id, 0),
            )
        )
    return reads


def get_teacher(
    session: Session, teacher_id: UUID, user: User | None = None
) -> TeacherRead:
    """One employee, if this caller may see them.

    A teacher asking for a colleague's id gets `404`, not `403`: the answer must
    not confirm that somebody else's id exists.
    """
    teacher = repository.get_teacher_by_id(session, teacher_id=teacher_id)
    visible = scope.visible_employee_ids(session, user)
    if teacher is None or (visible is not None and teacher.id not in visible):
        raise HTTPException(status_code=404, detail="Teacher not found")
    return _reads(session, [teacher])[0]


def own_employee(session: Session, user: User | None) -> Employee:
    """The employee row behind the caller - `404` when the account has none.

    A school administrator who is not on the teaching roll genuinely has no "my
    profile" to open, and saying so (`404`, with the reason) is better than an empty
    screen that looks broken.
    """
    employee = (
        repository.get_teacher_by_user_id(session, user_id=user.id) if user else None
    )
    if employee is None:
        raise HTTPException(
            status_code=404,
            detail="This account has no staff record in this school.",
        )
    return employee


def get_own(session: Session, user: User | None) -> TeacherRead:
    """The caller's own directory row, at the same scope as `get_teacher`."""
    employee = own_employee(session, user)
    return get_teacher(session=session, teacher_id=employee.id, user=user)


def get_teachers(
    session: Session,
    *,
    kind: repository.RollKind = "teacher",
    user: User | None = None,
    q: str | None = None,
    department: str | None = None,
    status: str | None = None,
    skip: int = 0,
    limit: int | None = None,
) -> list[TeacherRead]:
    """The directory: the caller's own scope of the school, filtered by the screen."""
    rows = repository.get_teachers(
        session,
        kind=kind,
        visible_ids=scope.visible_employee_ids(session, user),
        q=q,
        department=department,
        status=status,
        skip=skip,
        limit=limit,
    )
    return _reads(session, rows)


def count_teachers(
    session: Session,
    *,
    kind: repository.RollKind = "teacher",
    user: User | None = None,
    q: str | None = None,
    department: str | None = None,
    status: str | None = None,
) -> int:
    """How many rows the caller's filters match - what `X-Total-Count` carries.

    The same scope and the same filters as `get_teachers`, counted by the database:
    a page can say "3 of 41" without the 38 rows it did not load, and the number
    cannot drift from the list because both go through `teachers_statement`.
    """
    return repository.count_teachers(
        session,
        kind=kind,
        visible_ids=scope.visible_employee_ids(session, user),
        q=q,
        department=department,
        status=status,
    )


def staff_summary(
    session: Session, kind: repository.RollKind = "teacher"
) -> StaffSummary:
    """The tiles above the directory, counted over the whole teaching roll.

    Counted here rather than added up from the rows the browser happens to hold:
    a filter or a page must not change "Total staff".
    """
    teachers = repository.roll_employees(session, kind)
    on_leave = repository.approved_leave_today(session, date.today())
    periods = repository.period_counts(session, [teacher.id for teacher in teachers])

    counts = {labels.ACTIVE: 0, labels.ON_LEAVE: 0, labels.INACTIVE: 0}
    without_timetable = 0
    for teacher in teachers:
        status = labels.employee_status(
            deactivated_at=teacher.deactivated_at,
            left_on=teacher.left_on,
            on_leave=teacher.user_id in on_leave,
        )
        counts[status] += 1
        if status != labels.INACTIVE and not periods.get(teacher.id):
            without_timetable += 1

    return StaffSummary(
        total=len(teachers),
        active=counts[labels.ACTIVE],
        on_leave_today=counts[labels.ON_LEAVE],
        inactive=counts[labels.INACTIVE],
        periods_per_week=sum(periods.values()) if kind == "teacher" else 0,
        without_timetable=without_timetable if kind == "teacher" else 0,
        kind=kind,
        #: The tile is hidden for staff: no periods is the fact, not zero load.
        shows_periods=kind == "teacher",
    )


def workload_matrix(session: Session) -> list[WorkloadMatrixRow]:
    """Each teacher's real load, against the school's own definition of a week.

    Five statements for the page. Everybody on the teaching roll gets a row - a
    teacher with no subject or no period yet is a fact the principal wants to see,
    not a row to hide.

    Two things changed in Phase 4, and both were wrong numbers rather than
    missing features:

    * **the denominator is the school's rule** when one exists
      (`staffworkloadrule.weekly_periods`), the timetable's own slot count
      otherwise - and `capacity_source` says which, so the screen never implies a
      policy nobody wrote;
    * **a class teacher's section is listed** even when they teach no subject in
      it. The list used to come from `subjectteacher` alone, so the one fact that
      defines the job could be missing from the row.
    """
    teachers = repository.teaching_employees(session)
    if not teachers:
        return []

    teacher_ids = [teacher.id for teacher in teachers]
    capacity, capacity_source, week_slots = workload_repository.capacity(session)
    rule = workload_repository.rule(session)
    overload_percent = rule.overload_percent if rule is not None else 100
    underload_percent = rule.underload_percent if rule is not None else 60

    periods = repository.period_counts(session, teacher_ids)
    duties = workload_repository.duty_counts(session, teacher_ids, date.today())
    names = {
        user.id: user.full_name
        for user in session.exec(
            select(User).where(User.id.in_([teacher.user_id for teacher in teachers]))
        ).all()
    }

    subjects: dict[UUID, set[str]] = {}
    rooms: dict[UUID, set[UUID]] = {}
    for teacher_id, subject_name, room_id in session.exec(
        select(SubjectTeacher.teacher_id, Subject.name, SubjectTeacher.classroom_id)
        .join(Subject, Subject.id == SubjectTeacher.subject_id)
        .where(SubjectTeacher.teacher_id.in_(teacher_ids))
    ).all():
        subjects.setdefault(teacher_id, set()).add(subject_name)
        rooms.setdefault(teacher_id, set()).add(room_id)
    # The sections they run as class teacher: a class they hold whether or not
    # they teach a subject in it.
    for teacher_id, room_ids in workload_repository.class_teacher_rooms(
        session, teacher_ids
    ).items():
        rooms.setdefault(teacher_id, set()).update(room_ids)

    room_labels = labels_by_section(
        session, [room for room_ids in rooms.values() for room in room_ids]
    )

    rows: list[WorkloadMatrixRow] = []
    for teacher in teachers:
        load = periods.get(teacher.id, 0)
        band = labels.workload_band(
            load,
            capacity,
            overload_percent=overload_percent,
            underload_percent=underload_percent,
        )
        rows.append(
            WorkloadMatrixRow(
                id=teacher.id,
                staff=names.get(teacher.user_id, ""),
                subject=", ".join(sorted(subjects.get(teacher.id, set()))),
                classes=sorted(
                    {
                        room_labels[room]
                        for room in rooms.get(teacher.id, set())
                        if room in room_labels
                    }
                ),
                periods=load,
                capacity=capacity,
                capacity_source=capacity_source,
                week_slots=week_slots,
                duties=duties.get(teacher.id, 0),
                free_periods=max(capacity - load, 0),
                utilisation=labels.utilisation(load, capacity),
                overloaded=band == labels.OVERLOADED,
                band=band,
            )
        )
    return rows


def create_teacher(session: Session, teacher_in: TeacherCreate) -> Employee:
    """Add a teacher profile for an existing login.

    The employee row is the teaching record; the `teacher` role is what puts them
    on the roll the directory reads.
    """
    user = user_repository.get_user_by_id(session, user_id=teacher_in.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if repository.get_teacher_by_user_id(session, user_id=teacher_in.user_id):
        raise HTTPException(
            status_code=400, detail="Teacher profile already exists for this user"
        )

    return repository.create_teacher(session, teacher_in=teacher_in)


def teacher_profile(
    session: Session,
    teacher_id: UUID,
    user: User | None = None,
    *,
    reveal: bool = False,
) -> StaffProfile:
    """One person's whole profile: the directory row plus the four lists.

    The identity and roll fields come from `_reads` - the **same** function the
    table uses - so a drawer opened from the directory cannot show a different
    status, subject list or workload from the row behind it. The reporting line and
    the four lists are a few more statements; the whole answer costs a fixed number
    of reads rather than one per qualification.
    """
    employee = repository.get_teacher_by_id(session, teacher_id=teacher_id)
    visible = scope.visible_employee_ids(session, user)
    if employee is None or (visible is not None and employee.id not in visible):
        raise HTTPException(status_code=404, detail="Teacher not found")

    row = _reads(session, [employee])[0]
    capacity = repository.week_capacity(session)
    lists = profile_service.reads(session, employee.id)

    # The reporting line is a name on screen and an id in the database: resolving
    # the name here (one statement) saves the drawer a second call that turns an id
    # into something a person can read.
    manager: str | None = None
    if employee.reports_to_employee_id is not None:
        manager = session.exec(
            select(User.full_name)
            .join(Employee, Employee.user_id == User.id)
            .where(Employee.id == employee.reports_to_employee_id)
        ).first()

    return StaffProfile(
        id=employee.id,
        user_id=employee.user_id,
        staff_code=employee.employee_code,
        name=row.name,
        department=employee.department,
        designation=employee.designation,
        employment_type=employee.employment_type,
        qualification=employee.qualification,
        experience_years=employee.experience_years,
        joining_date=employee.joining_date,
        probation_end=employee.probation_end,
        reports_to=manager,
        reports_to_employee_id=employee.reports_to_employee_id,
        phone=row.phone,
        email=row.email,
        address=employee.address,
        emergency_contact=employee.emergency_contact,
        status=row.status,
        # `TeacherRead.subject` is the joined list the table prints; the profile
        # wants the same names as a list, so it splits what the row already has
        # instead of running the subject query a second time.
        subjects=[name for name in row.subject.split(", ") if name],
        classes=row.classes,
        workload=row.workload,
        capacity=capacity,
        utilisation=labels.utilisation(row.workload, capacity),
        qualifications=lists.qualifications,
        experiences=lists.experiences,
        certifications=lists.certifications,
        history=lists.history,
        documents=lists.documents,
        # Masked by default: `reveal` has to be asked for *and* allowed, and the
        # reveal itself writes an audit line (`profile.service.kyc_read`).
        kyc=profile_service.kyc_read(session, employee, user, reveal=reveal),
    )


def staff_audit(
    session: Session,
    *,
    employee_id: UUID | None = None,
    section: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[AuditRead]:
    """Who changed what, newest first - the whole school or one person.

    Two name lookups for the page, not two per row: `employee_names` resolves the
    person and `recorder_names` the login that made the change, so a feed of a
    hundred lines costs three statements. A row whose actor was deleted keeps its
    line with no name rather than disappearing - the change still happened.
    """
    rows = profile_repository.audit_rows(
        session,
        employee_id=employee_id,
        section=section,
        limit=limit,
        offset=offset,
    )
    people = profile_repository.employee_names(
        session, [row.employee_id for row in rows]
    )
    actors = profile_repository.recorder_names(
        session, [row.changed_by_user_id for row in rows]
    )
    return [
        AuditRead(
            id=row.id,
            employee_id=row.employee_id,
            employee_name=people.get(row.employee_id, ""),
            section=row.section,
            action=row.action,
            row_id=row.row_id,
            summary=row.summary,
            changed_by=(
                actors.get(row.changed_by_user_id)
                if row.changed_by_user_id is not None
                else None
            ),
            created_at=row.created_at,
        )
        for row in rows
    ]
