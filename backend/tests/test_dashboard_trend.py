"""The dashboard's attendance chart is the register's real percentages, not a fixed picture."""

from datetime import date, timedelta

from app.domains.academic.classroom.attendance.models import AttendanceRecord, AttendanceStatus
from app.domains.main.dashboard import service
from tests.test_exam_class_test import world


def test_the_trend_is_the_percent_present_per_marked_day_and_skips_unmarked_days():
    session, data = world()
    today = date.today()
    for day, absent in ((today, data["kabir"]), (today - timedelta(days=2), None)):
        for child in (data["aarav"], data["kabir"]):
            status = AttendanceStatus.absent if child is absent else AttendanceStatus.present
            session.add(
                AttendanceRecord(
                    student_id=child.id,
                    classroom_id=data["room"].id,
                    date=day,
                    status=status,
                    school_id=data["school"].id,
                )
            )
    session.commit()

    trend = service._attendance_trend(session, today)

    assert [point.value for point in trend] == [100.0, 50.0], "two marked days, oldest first"
    assert service._attendance_trend(session, today - timedelta(days=30)) == []
