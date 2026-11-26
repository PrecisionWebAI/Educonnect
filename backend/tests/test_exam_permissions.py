"""Exam module, Phase 9: who may do what - every operation against every kind of caller.

The callers are the ones the spec names:

* `system_admin`     - the platform administrator (everything, in the school they are in);
* `office`           - the school admin (everything);
* `principal`        - leadership (everything);
* `vice_principal`   - leadership (everything: the user asked for them to be included);
* `hod`              - a head of department: a teacher with no link to 9-A (nothing);
* `class_teacher`    - Meera: class teacher of 9-A, and the teacher of its Mathematics;
* `subject_teacher`  - Bose: teaches 9-A's Science, nothing else, class teacher of nothing;
* `outsider`         - a teacher with no link to 9-A at all;
* `guardian`         - a parent of a child in 9-A;
* `student`          - a child in 9-A, with a login of their own.

Each row of `MATRIX` says which of them may do one thing, and the test runs **every** caller
against it: allowed means the call goes through, denied means a `403`/`404` (a `404` where the
server must not confirm the id exists). Anything else (a `409`/`422`) means the scenario was
set up wrongly, and fails loudly rather than counting as "denied".

The rules being pinned (D13 in `phase3.md`):

* **Class test** - the subject teacher, the class teacher, leadership.
* **Date sheet** (create / edit / publish / delete) - the class teacher and leadership; the
  subject teacher never.
* **Syllabus** - the subject's teacher for their own subject, the class teacher and
  leadership for any; readers only once the date sheet is published.
* **Marks** (enter / publish / correct / history) - the subject's teacher, leadership, and the
  class teacher **on a class test only** (never on a School Exam of a subject they don't teach).
* **Results** - a section's class view to leadership and the section's teachers; a family only
  its own children, with no section.

Runs under pytest.
"""

from datetime import date
from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.domains.academic.classroom.exams.plan import class_test, school_exam, service
from app.domains.academic.classroom.exams.plan.overview import result_overview
from app.domains.academic.classroom.exams.plan.schemas import (
    ClassTestUpdateIn,
    MarkChangeIn,
    SchoolExamCreateIn,
    SchoolExamRowIn,
    SchoolExamUpdateIn,
    SyllabusIn,
)
from app.domains.auth.models import UserRole
from tests.test_classroom_exams import _role, _user
from tests.test_exam_class_test import world
from tests.test_exam_marks_entry import entry, make_test, save
from tests.test_exam_school_exam import make, rows, with_science_teacher

D = Decimal
DAY = date(2027, 1, 12)

ACTORS = [
    "system_admin",
    "office",
    "principal",
    "vice_principal",
    "class_teacher",
    "subject_teacher",
    "hod",
    "outsider",
    "guardian",
    "student",
]
LEADERS = {"system_admin", "office", "principal", "vice_principal"}


class Scene:
    """One school with every caller in it."""

    def __init__(self):
        self.session, self.data = world()
        _, self.bose = with_science_teacher(self.session, self.data)
        self.login = _user(self.session, "aarav.login9@test")
        self.data["aarav"].user_id = self.login.id
        self.session.add(self.data["aarav"])
        self.session.commit()
        self.users = {
            "system_admin": self._with_role("system_admin"),
            "office": self.data["office"],
            "principal": self.data["principal"],
            "vice_principal": self._with_role("vice_principal"),
            "hod": self._with_role("hod"),
            "class_teacher": self.data["meera"],
            "subject_teacher": self.bose,
            "outsider": self.data["outsider"],
            "guardian": self.data["aarav_parent"],
            "student": self.login,
        }

    def _with_role(self, role: str):
        user = _user(self.session, f"{role}@matrix.test")
        self.session.add(UserRole(user_id=user.id, role_id=_role(self.session, role).id))
        self.session.commit()
        return user

    # -- things set up by the school's own office, so every caller starts from the same state
    def test_of(self, subject="maths", **over):
        extra = {}
        if subject == "science":
            extra = dict(taken_by_employee_id=self.data["employee"].id)
        return make_test(
            self.session,
            self.data,
            user=self.data["office"],
            classroom_subject_id=self.data[subject].id,
            **extra,
            **over,
        )

    def sheet(self, publish=False):
        exam = make(self.session, self.data, user=self.data["office"])
        if publish:
            school_exam.publish_date_sheet(self.session, exam.id, self.data["office"])
        return exam

    def paper(self, exam, subject):
        course = self.data[subject]
        return next(p for p in exam.papers if p.classroom_subject_id == course.id)

    def marked(self, exam, subject="maths", publish=False):
        paper = self.paper(exam, subject)
        # everyone has a score or an absence, or the paper could not be published
        rest = [
            entry(student, absent=True)
            for student in service._section_students(
                self.session, self.session.get(service.ExamPaper, paper.id)
            ).values()
            if student.id != self.data["aarav"].id
        ]
        save(
            self.session,
            paper.id,
            [entry(self.data["aarav"], 40), *rest],
            self.data["office"],
        )
        if publish:
            service.publish_paper(self.session, paper.id, self.data["office"])
        return paper


# ------------------------------------------------------------------ the operations
# Each takes (scene, user) and either succeeds or raises HTTPException.


def schedule_test(subject):
    def run(s: Scene, user):
        make_test(
            s.session, s.data, user=user, classroom_subject_id=s.data[subject].id,
            **(
                dict(taken_by_employee_id=s.data["employee"].id)
                if subject == "science"
                else {}
            ),
        )

    return run


def edit_test(s: Scene, user):
    exam = s.test_of()
    class_test.update_class_test(
        s.session, exam.id, ClassTestUpdateIn(total_marks=D("40")), user
    )


def cancel_test(s: Scene, user):
    class_test.cancel_class_test(s.session, s.test_of().id, user)


def delete_test(s: Scene, user):
    class_test.delete_class_test(s.session, s.test_of().id, user)


def create_sheet(s: Scene, user):
    school_exam.create_school_exam(
        s.session,
        SchoolExamCreateIn(
            classroom_id=s.data["room"].id, exam_type="unit_test", rows=rows(s.data)
        ),
        user,
    )


def edit_sheet(s: Scene, user):
    exam = s.sheet()
    school_exam.update_school_exam(
        s.session, exam.id, SchoolExamUpdateIn(family_note="Bring a pen"), user
    )


def publish_sheet(s: Scene, user):
    school_exam.publish_date_sheet(s.session, s.sheet().id, user)


def delete_sheet(s: Scene, user):
    school_exam.delete_school_exam(s.session, s.sheet().id, user)


def write_syllabus(subject):
    def run(s: Scene, user):
        paper = s.paper(s.sheet(), subject)
        school_exam.set_syllabus(s.session, paper.id, SyllabusIn(syllabus_text="Chapter 1"), user)

    return run


def read_syllabus_draft(s: Scene, user):
    paper = s.paper(s.sheet(), "maths")
    school_exam.set_syllabus(
        s.session, paper.id, SyllabusIn(syllabus_text="Chapter 1"), s.data["office"]
    )
    school_exam.get_syllabus(s.session, paper.id, user)


def read_syllabus_published(s: Scene, user):
    exam = s.sheet(publish=True)
    paper = s.paper(exam, "maths")
    school_exam.set_syllabus(
        s.session, paper.id, SyllabusIn(syllabus_text="Chapter 1"), s.data["office"]
    )
    school_exam.get_syllabus(s.session, paper.id, user)


def see_draft_sheet(s: Scene, user):
    exam = s.sheet()
    if exam.id not in [e.id for e in service.list_exams(s.session, user)]:
        raise HTTPException(status_code=404, detail="not listed")
    service.read_exam(s.session, exam.id, user)


def marks_save(kind, subject):
    def run(s: Scene, user):
        exam = s.test_of(subject) if kind == "test" else s.sheet()
        paper = s.paper(exam, subject)
        save(s.session, paper.id, [entry(s.data["aarav"], 40)], user)

    return run


def marks_publish(s: Scene, user):
    exam = s.test_of()
    paper = s.marked(exam)
    service.publish_paper(s.session, paper.id, user)


def marks_change(s: Scene, user):
    exam = s.test_of()
    paper = s.marked(exam, publish=True)
    service.change_mark(
        s.session, paper.id, s.data["aarav"].id, MarkChangeIn(marks_obtained=D("30")), user
    )


def marks_history(s: Scene, user):
    exam = s.test_of()
    paper = s.marked(exam, publish=True)
    service.mark_history(s.session, paper.id, user)


def marks_sheet(s: Scene, user):
    exam = s.test_of()
    service.paper_marks(s.session, s.paper(exam, "maths").id, user)


def overview_section(s: Scene, user):
    exam = s.test_of()
    s.marked(exam, publish=True)
    result_overview(s.session, user, "class_test", s.data["room"].id)


def overview_family(s: Scene, user):
    exam = s.test_of()
    s.marked(exam, publish=True)
    result_overview(s.session, user, "class_test", None)


STAFF = LEADERS | {"class_teacher"}
WITH_SUBJECT = STAFF | {"subject_teacher"}
FAMILY = {"guardian", "student"}

# name -> (operation, who may, which codes mean "denied")
MATRIX = {
    # Class test: the subject teacher, the class teacher, leadership.
    "schedule_test_maths": (schedule_test("maths"), STAFF),
    "schedule_test_science": (schedule_test("science"), WITH_SUBJECT),
    "edit_test": (edit_test, STAFF),
    "cancel_test": (cancel_test, STAFF),
    "delete_test": (delete_test, STAFF),
    # Date sheet: the class teacher and leadership - never the subject teacher.
    "create_sheet": (create_sheet, STAFF),
    "edit_sheet": (edit_sheet, STAFF),
    "publish_sheet": (publish_sheet, STAFF),
    "delete_sheet": (delete_sheet, STAFF),
    # Syllabus.
    "write_syllabus_maths": (write_syllabus("maths"), STAFF),
    "write_syllabus_science": (write_syllabus("science"), WITH_SUBJECT),
    "read_syllabus_draft": (read_syllabus_draft, STAFF),
    "read_syllabus_published": (
        read_syllabus_published,
        WITH_SUBJECT | FAMILY,
    ),
    "see_draft_sheet": (see_draft_sheet, WITH_SUBJECT),
    # Marks on a class test.
    "marks_save_test_maths": (marks_save("test", "maths"), STAFF),
    "marks_save_test_science": (marks_save("test", "science"), WITH_SUBJECT),
    "marks_publish_test": (marks_publish, STAFF),
    "marks_change_test": (marks_change, STAFF),
    "marks_history_test": (marks_history, STAFF),
    "marks_sheet_test": (marks_sheet, STAFF),
    # Marks on a School Exam: the subject teacher, the class teacher (any subject of their
    # section) and leadership - the same as on a class test.
    "marks_save_sheet_maths": (marks_save("sheet", "maths"), STAFF),
    "marks_save_sheet_science": (marks_save("sheet", "science"), WITH_SUBJECT),
    # Results.
    "overview_section": (overview_section, WITH_SUBJECT),
    "overview_family": (overview_family, FAMILY),
}


def allowed(run, scene: Scene, who: str, deny=(403, 404, 422)) -> bool:
    try:
        run(scene, scene.users[who])
    except HTTPException as exc:
        if exc.status_code in deny:
            return False
        raise AssertionError(f"{exc.status_code}: {exc.detail}") from exc
    return True


@pytest.mark.parametrize("name", sorted(MATRIX))
@pytest.mark.parametrize("who", ACTORS)
def test_who_may_do_what(name, who):
    run, may = MATRIX[name]
    # A staff member calling the family-only view gets a 422 ("choose a section"); a
    # family calling a write gets a 403/404. All of those are a "no".
    got = allowed(run, Scene(), who)
    assert got == (who in may), (
        f"{who} {'was refused' if not got else 'was allowed'} on {name}; "
        f"expected {'allowed' if who in may else 'refused'}"
    )
