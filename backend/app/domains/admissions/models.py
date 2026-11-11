"""The admission workflow's view of a student - an **alias**, not a table.

One learner is one row (`student`, see `app/domains/students/models.py`). The
admission form used to be its own table (`student_admission_form`) and registering
an application copied it into `Student`; the two rows then held the same child
under two ids, and a form edited afterwards could disagree with the directory.

Now the row the office types **is** the student row. An application was never a
*stage* of a student either, so there is no draft and no workflow vocabulary left
here: what the admission screen saves is a student the school has admitted, with
their admission number, their guardian link and the logins the form's own emails
make. Which is why this module is thin on purpose:

* `AdmissionApplication` is an alias for `Student`, so the admission code reads and
  writes the real table (`select(AdmissionApplication)` is `select(Student)`);
* `AdmissionApplicationBase` is the student's columns - what the form fills in (the
  **guardian block** the form also asks for is not a student column: it belongs to
  the `guardian` row, and `admissions/schemas.py` declares it);
* the `separation` block ("why/when the child left") is a property of the model -
  it is derived from the student's own four separation columns.

Nothing here declares a table, so there is nothing to drift: a column added to the
student is a column the admission form sees.
"""

from app.domains.students.models import (  # noqa: F401  (re-exported on purpose)
    Student,
    StudentBase,
)

#: The form schema the admission request models inherit (`AdmissionApplicationCreate`
#: and friends): the student's columns, which is what the form fills in.
AdmissionApplicationBase = StudentBase

#: The row the admission screens read and write - the student itself.
AdmissionApplication = Student

__all__ = [
    "AdmissionApplication",
    "AdmissionApplicationBase",
    "Student",
    "StudentBase",
]
