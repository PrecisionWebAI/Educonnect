"""What the school says after a register is saved.

Two events, two audiences, and they are deliberately different:

* **`attendance.absent`** -> the child's guardians. A family that is not told is the
  one thing a register exists to prevent.
* **`attendance.consecutive`** -> the class teacher and the principals. Three open days
  in a row is a pattern the office acts on, not a note to the parent.

Both are keyed by the day (`attendance:<student>:<date>:absent`,
`consecutive:<student>:<date>`), so saving the same register again says nothing new.
"""

import logging
from datetime import date
from uuid import UUID

from sqlmodel import Session, select

from app.domains.academic.classroom.students.models import Student
from app.domains.main.notifications import events

logger = logging.getLogger("eduverse.notifications")

ABSENT_TITLE = "Marked absent today"
CONSECUTIVE_TITLE = "Absent several days in a row"


def announce(
    session: Session,
    *,
    classroom_id: UUID,
    on_date: date,
    absent_student_ids: list[UUID],
    streaks: dict[UUID, int],
    run_limit: int,
) -> int:
    """Tell the families, then the office. Returns how many rows were written.

    Everything is inside one `try`: the register is already saved and committed, and a
    bell that cannot ring must not turn a successful save into a 500 (rule 9).
    """
    if not absent_student_ids:
        return 0

    try:
        students = {
            student.id: student
            for student in session.exec(
                select(Student).where(Student.id.in_(absent_student_ids))
            ).all()
        }
        written = 0
        day = on_date.isoformat()

        for student_id in absent_student_ids:
            student = students.get(student_id)
            name = (student.full_name if student is not None else "") or "The student"

            written += events.notify(
                session,
                event=events.EVENT_ATTENDANCE_ABSENT,
                recipients=events.audience(
                    session, roles={events.GUARDIANS}, student_id=student_id
                ),
                title=ABSENT_TITLE,
                body=(
                    f"{name} was marked absent on {day}. "
                    "If this is a mistake, please contact the class teacher."
                ),
                entity_type="student",
                entity_id=student_id,
                dedupe_key=f"attendance:{student_id}:{day}:absent",
            )

            streak = streaks.get(student_id, 0)
            if streak < run_limit:
                continue
            written += events.notify(
                session,
                event=events.EVENT_ATTENDANCE_CONSECUTIVE,
                recipients=events.audience(
                    session,
                    roles={events.CLASS_TEACHER, events.PRINCIPALS},
                    classroom_id=classroom_id,
                ),
                title=CONSECUTIVE_TITLE,
                body=(
                    f"{name} has been absent {streak} open days in a row "
                    f"(to {day}). A call home may be needed."
                ),
                entity_type="student",
                entity_id=student_id,
                dedupe_key=f"consecutive:{student_id}:{day}",
            )

        return written
    except Exception as error:
        logger.warning("attendance notifications were not written: %s", error)
        return 0
