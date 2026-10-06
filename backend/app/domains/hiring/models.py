"""Staff hiring - the Operations > Staff Hiring pipeline.

Two tables:

* `staffvacancy` - a post the school is hiring for (`openings` seats). The stat
  tile "Open Vacancies" counts the unfilled seats from here, so the number is a
  query instead of a constant in the frontend.
* `hiringcandidate` - one person in the pipeline. `status` walks the same five
  stages the screen labels (Resume -> Shortlisted -> Interview -> Hired /
  Rejected). Reaching *Hired* stamps the employee id (`EMP-0037`) that then
  identifies the person in the salary register.
"""

from datetime import date

from sqlmodel import Field, SQLModel

# Pipeline stages, stored exactly as the screen labels them.
HIRING_STATUSES = ("Resume", "Shortlisted", "Interview", "Hired", "Rejected")
STATUS_RESUME = "Resume"
STATUS_HIRED = "Hired"

#: First employee number handed out when the table is still empty. The demo
#: school's staff already end at EMP-0036, so the next hire is EMP-0037.
FIRST_EMP_NUMBER = 37


class StaffVacancyBase(SQLModel):
    role: str = Field(index=True)  # e.g. "Physics Teacher"
    department: str
    openings: int = 1
    status: str = Field(default="Open")  # "Open" | "Closed"


class StaffVacancy(StaffVacancyBase, table=True):
    id: int | None = Field(default=None, primary_key=True)


class HiringCandidateBase(SQLModel):
    # Assigned by the server when absent (`CAN-2026-0036`).
    candidate_no: str | None = Field(default=None, unique=True, index=True)
    candidate_name: str
    role: str
    department: str
    qualification: str | None = None
    experience: int = 0
    applied_on: date = Field(default_factory=date.today)
    interview_on: date | None = None
    # Stamped when the candidate reaches "Hired"; NULL while still in the pipeline.
    emp_id: str | None = Field(default=None, index=True)
    status: str = Field(default=STATUS_RESUME)


class HiringCandidate(HiringCandidateBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
