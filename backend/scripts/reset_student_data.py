"""Remove every student and guardian record - and nothing else.

Why this exists:
  The demo school's first students were written straight into `studentprofile` by
  a seed script, so they had no admission form behind them. Now that registering
  an application creates the student (see `admissions/service.py`), the demo is
  rebuilt from the forms themselves - which means the old rows have to go first.

What it removes (only people who hold *just* the student and/or guardian role -
a teacher who is also a parent keeps their login):
  studentprofile, studentparentrelationship, attendancerecord,
  attendanceauditlog, homeworksubmission, classdiary, feetransaction, the
  student/guardian `user` rows and their `user_role` rows, their chat membership,
  and any impersonation / author column that pointed at them.

What it deliberately keeps:
  teachers, admins, classes, sections, subjects, timetables, fee heads, homework
  assignments, staff, vacancies, salaries, the content library - and the
  admission applications themselves (their promotion links are cleared, so they
  can be registered again).

    docker exec eduverse-backend python scripts/reset_student_data.py
"""

import os
import sys
from collections import defaultdict

from sqlmodel import Session, select

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.db import engine

# Import every model module: SQLModel has to know all the tables a deleted row
# points at (classroom, section, subject, teacherprofile, ...), otherwise the
# delete fails with "could not find table 'classroom'".
from app.domains.academics import models as academics_models  # noqa: F401
from app.domains.admissions import models as admissions_models  # noqa: F401
from app.domains.admissions.models import AdmissionApplication
from app.domains.attendance import models as attendance_models  # noqa: F401
from app.domains.attendance.models import AttendanceAuditLog, AttendanceRecord
from app.domains.auth import models as auth_models  # noqa: F401
from app.domains.auth.models import ImpersonationLog, Role, UserRole
from app.domains.chat import models as chat_models  # noqa: F401
from app.domains.chat.models import ChatMessage, ChatThreadParticipant
from app.domains.exams import models as exams_models  # noqa: F401
from app.domains.exams.models import ExamSource, PaperDraft, QuestionUsageLog
from app.domains.finance import models as finance_models  # noqa: F401
from app.domains.finance.models import FeeTransaction
from app.domains.hiring import models as hiring_models  # noqa: F401
from app.domains.homework import models as homework_models  # noqa: F401
from app.domains.homework.models import ClassDiary, HomeworkSubmission
from app.domains.salary import models as salary_models  # noqa: F401
from app.domains.students.models import StudentParentRelationship, StudentProfile
from app.domains.teachers import models as teachers_models  # noqa: F401
from app.domains.timetable import models as timetable_models  # noqa: F401
from app.domains.users import models as user_models  # noqa: F401
from app.domains.users.models import User

#: A login is "student data" / "guardian data" only when it holds nothing else.
#: A teacher who is also a parent keeps their account untouched.
STUDENT_ROLES = {"student"}
GUARDIAN_ROLES = {"guardian"}


def _doomed_user_ids(session: Session) -> list[int]:
    rows = session.exec(
        select(User.id, Role.codename)
        .join(UserRole, UserRole.user_id == User.id)  # type: ignore[arg-type]
        .join(Role, Role.id == UserRole.role_id)  # type: ignore[arg-type]
    ).all()
    roles: dict[int, set[str]] = defaultdict(set)
    for user_id, codename in rows:
        if user_id is not None:
            roles[int(user_id)].add(str(codename))
    return [
        user_id
        for user_id, names in roles.items()
        if names and names <= (STUDENT_ROLES | GUARDIAN_ROLES)
    ]


def _delete(session: Session, statement) -> int:
    rows = session.exec(statement).all()
    for row in rows:
        session.delete(row)
    session.commit()
    return len(rows)


def reset_student_data() -> None:
    """Clear everything that belongs to students and guardians."""
    with Session(engine) as session:
        doomed = _doomed_user_ids(session)
        print(f"[reset] {len(doomed)} student/guardian login(s) to remove")

        # 1. Un-promote the applications: drop the links to the rows that are
        #    about to disappear, so the same forms can be registered again.
        applications = session.exec(select(AdmissionApplication)).all()
        for application in applications:
            application.student_id = None
            application.student_user_id = None
            application.guardian_user_id = None
            application.promoted_at = None
            session.add(application)
        session.commit()
        print(f"[reset] un-linked {len(applications)} admission application(s)")

        # 2. Rows that hang off a student profile (they go before the profiles).
        for label, statement in (
            ("attendance audit", select(AttendanceAuditLog)),
            ("attendance", select(AttendanceRecord)),
            ("homework submissions", select(HomeworkSubmission)),
            ("class diary", select(ClassDiary)),
            ("fee payments", select(FeeTransaction)),
            ("parent links", select(StudentParentRelationship)),
        ):
            print(f"[reset] removed {_delete(session, statement)} {label} row(s)")

        # 3. Rows that hang off the logins themselves.
        if doomed:
            for label, statement in (
                (
                    "impersonation logs",
                    select(ImpersonationLog).where(
                        (ImpersonationLog.actor_user_id.in_(doomed))  # type: ignore[attr-defined]
                        | (ImpersonationLog.target_user_id.in_(doomed))  # type: ignore[attr-defined]
                    ),
                ),
                (
                    "chat messages",
                    select(ChatMessage).where(
                        ChatMessage.sender_id.in_(doomed)  # type: ignore[attr-defined]
                    ),
                ),
                (
                    "chat memberships",
                    select(ChatThreadParticipant).where(
                        ChatThreadParticipant.user_id.in_(doomed)  # type: ignore[attr-defined]
                    ),
                ),
            ):
                print(f"[reset] removed {_delete(session, statement)} {label} row(s)")

            # Author columns are nullable, so they are cleared instead of throwing
            # the teacher's content library away.
            for model in (ExamSource, PaperDraft, QuestionUsageLog):
                rows = session.exec(
                    select(model).where(model.created_by.in_(doomed))  # type: ignore[attr-defined]
                ).all()
                for row in rows:
                    row.created_by = None
                    session.add(row)
                session.commit()

        # 4. The profiles, then the logins and their role rows.
        print(
            f"[reset] removed {_delete(session, select(StudentProfile))} "
            "student profile(s)"
        )
        if doomed:
            role_rows = _delete(
                session,
                select(UserRole).where(UserRole.user_id.in_(doomed)),  # type: ignore[attr-defined]
            )
            logins = _delete(
                session,
                select(User).where(User.id.in_(doomed)),  # type: ignore[attr-defined]
            )
            print(f"[reset] removed {role_rows} role row(s) and {logins} login(s)")

        remaining = len(session.exec(select(StudentProfile)).all())
        print(
            f"[reset] Students and guardians cleared "
            f"(studentprofile now holds {remaining})"
        )


if __name__ == "__main__":
    reset_student_data()
