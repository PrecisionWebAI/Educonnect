"""Seed the Operations demo data (Admission, Staff Hiring, Fees, Staff Salary).

Why this file exists:
  The four Operations screens used to render hard-coded rows in the frontend.
  They now read real tables - `admissionapplication`, `hiringcandidate` +
  `staffvacancy`, `feestructure`, `salarypayment` - so the demo school needs
  rows in those tables or every screen would look empty.

  The rows below tell the same story the mock arrays told (Aarav Sharma's
  admission, Priya Menon's hire, the class-wise fee card, the September salary
  run); they simply live in the database now instead of in a `.service.ts`.

Idempotent: every block skips work it has already done, so this is safe on each
container start (bootstrap.py calls it) and by hand:

    docker exec eduverse-backend python scripts/seed_operations.py

It must run *after* `seed_academics.py`: the fee rows count the students that
seed creates and the salary rows are built from the staff it creates.
"""

import os
import sys
from datetime import date

from sqlmodel import Session, select

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.db import engine
from app.domains.academics.models import GradeClass
from app.domains.admissions.models import (
    STATUS_DRAFT,
    STATUS_REGISTERED,
    AdmissionApplication,
)
from app.domains.finance.models import FeeFrequency, FeeStructure
from app.domains.hiring.models import HiringCandidate, StaffVacancy
from app.domains.salary.models import (
    STATUS_PAID,
    STATUS_PENDING,
    STATUS_PROCESSING,
    SalaryPayment,
)
from app.domains.teachers.models import TeacherProfile
from app.domains.users.models import User

# ---------------------------------------------------------------------------
# 1. Admission - the applications the Admission screen lists
# ---------------------------------------------------------------------------

#: Form numbers start here, continuing the series the demo data used.
FIRST_APPLICATION_SEQUENCE = 141

#: Only the answers that differ from blank are listed; everything else stays
#: NULL, exactly like a half-filled form does.
ADMISSION_ROWS: list[dict] = [
    {
        "status": STATUS_REGISTERED,
        "created_on": date(2026, 9, 18),
        "student_first_name": "Aarav",
        "student_last_name": "Sharma",
        "date_of_birth": date(2014, 6, 12),
        "gender": "Male",
        "blood_group": "B+",
        "category": "General",
        "nationality": "Indian",
        "address": "12 Rose Villa, Kothrud, Pune 411038",
        "father_name": "Rakesh Sharma",
        "father_occupation": "Private Service",
        "father_phone": "+91 98200 11223",
        "father_email": "rakesh.sharma@example.com",
        "mother_name": "Sunita Sharma",
        "mother_phone": "+91 98200 11224",
        "applied_for_class_level": "Grade 6",
        "current_class_or_last_class": "Grade 6",
        "applied_section_preference": "A",
        "needs_transport": "Yes",
        "transport_route": "Route 4 - Kothrud",
        "previous_school_name": "Sunrise Public School",
    },
    {
        "status": STATUS_REGISTERED,
        "created_on": date(2026, 9, 19),
        "student_first_name": "Diya",
        "student_last_name": "Nair",
        "date_of_birth": date(2012, 11, 2),
        "gender": "Female",
        "category": "OBC",
        "nationality": "Indian",
        "address": "44 Palm Grove, Aundh, Pune 411007",
        "father_name": "Suresh Nair",
        "father_phone": "+91 98200 44556",
        "applied_for_class_level": "Grade 8",
        "current_class_or_last_class": "Grade 8",
        "applied_section_preference": "B",
        "previous_school_name": "St. Xavier's High School",
        "previous_class_passed": "Grade 7",
    },
    {
        # Separated mid-session - the Registered table reports this as Inactive.
        "status": STATUS_REGISTERED,
        "created_on": date(2026, 9, 21),
        "student_first_name": "Kabir",
        "student_last_name": "Verma",
        "date_of_birth": date(2011, 3, 27),
        "gender": "Male",
        "nationality": "Indian",
        "address": "7 Lake View, Baner, Pune 411045",
        "father_name": "Anil Verma",
        "father_phone": "+91 98200 77889",
        "guardian_name": "Shalini Verma",
        "guardian_relation": "Aunt",
        "guardian_phone": "+91 98200 77890",
        "applied_for_class_level": "Grade 9",
        "current_class_or_last_class": "Grade 9",
        "applied_section_preference": "A",
        "needs_hostel": "No",
        "separation_dropped_class": "Grade 9",
        "separation_reason": "Rusticated",
        "separation_session": "Incomplete Session",
        "separation_date": date(2026, 9, 30),
    },
    {
        # Separated at the end of the session (transfer certificate issued).
        "status": STATUS_REGISTERED,
        "created_on": date(2026, 9, 25),
        "student_first_name": "Anaya",
        "student_last_name": "Iyer",
        "date_of_birth": date(2010, 8, 9),
        "gender": "Female",
        "nationality": "Indian",
        "address": "21 Hill Road, Shivaji Nagar, Pune 411005",
        "father_name": "Kiran Iyer",
        "father_phone": "+91 98200 66554",
        "father_email": "kiran.iyer@example.com",
        "mother_name": "Lakshmi Iyer",
        "mother_phone": "+91 98200 66555",
        "applied_for_class_level": "Grade 10",
        "current_class_or_last_class": "Grade 10",
        "applied_section_preference": "C",
        "separation_dropped_class": "Grade 10",
        "separation_reason": "Transfer Certificate Issued",
        "separation_session": "Completed Session",
        "separation_date": date(2026, 9, 27),
    },
    {
        "status": STATUS_DRAFT,
        "created_on": date(2026, 9, 24),
        "student_first_name": "Vihaan",
        "student_last_name": "Gupta",
        "gender": "Male",
        "applied_for_class_level": "Grade 10",
        "current_class_or_last_class": "Grade 10",
        "applied_section_preference": "A",
        "guardian_name": "Neha Gupta",
        "guardian_phone": "+91 98200 99110",
    },
    {
        "status": STATUS_DRAFT,
        "created_on": date(2026, 9, 26),
        "student_first_name": "Ishita",
        "student_last_name": "Rao",
        "date_of_birth": date(2013, 1, 30),
        "gender": "Female",
        "applied_for_class_level": "Grade 7",
        "current_class_or_last_class": "Grade 7",
        "father_name": "Suresh Rao",
        "father_phone": "+91 98200 33445",
    },
    {
        "status": STATUS_DRAFT,
        "created_on": date(2026, 9, 28),
        "student_first_name": "Reyansh",
        "student_last_name": "Patil",
        "applied_for_class_level": "Grade 6",
        "current_class_or_last_class": "Grade 6",
        "needs_transport": "Yes",
    },
]


def _seed_admissions(session: Session) -> None:
    """Insert the demo applications (skipped when the table already has rows)."""
    if session.exec(select(AdmissionApplication)).first():
        print("[seed_operations] admission applications already exist. Skipping...")
        return

    for offset, row in enumerate(ADMISSION_ROWS):
        sequence = FIRST_APPLICATION_SEQUENCE + offset
        session.add(
            AdmissionApplication(
                application_no=f"ADM-{date.today().year}-{sequence:04d}",
                **row,
            )
        )
    session.commit()
    print(f"[seed_operations] {len(ADMISSION_ROWS)} admission applications inserted")


# ---------------------------------------------------------------------------
# 2. Staff Hiring - the vacancies and the candidates in the pipeline
# ---------------------------------------------------------------------------

#: (role, department, openings). Four open posts, so the screen's
#: "Open Vacancies" tile reads 4 minus the people already hired into them.
STAFF_VACANCIES: list[tuple[str, str, int]] = [
    ("Physics Teacher", "Science", 1),
    ("Mathematics Teacher", "Mathematics", 1),
    ("Lab Assistant", "Science", 1),
    ("English Teacher", "Languages", 1),
]

#: The pipeline. `emp_id` is stamped on the one person who was hired, and the
#: server hands out the next number (EMP-0037) from there.
HIRING_ROWS: list[dict] = [
    {
        "candidate_no": "CAN-2026-0031",
        "candidate_name": "Rohan Deshmukh",
        "role": "Physics Teacher",
        "department": "Science",
        "qualification": "M.Sc. Physics, B.Ed.",
        "experience": 6,
        "applied_on": date(2026, 9, 14),
        "interview_on": date(2026, 9, 28),
        "status": "Interview",
    },
    {
        "candidate_no": "CAN-2026-0032",
        "candidate_name": "Sneha Kulkarni",
        "role": "Mathematics Teacher",
        "department": "Mathematics",
        "qualification": "M.Sc. Maths, B.Ed.",
        "experience": 4,
        "applied_on": date(2026, 9, 15),
        "interview_on": date(2026, 9, 29),
        "status": "Shortlisted",
    },
    {
        "candidate_no": "CAN-2026-0033",
        "candidate_name": "Imran Sheikh",
        "role": "Lab Assistant",
        "department": "Science",
        "qualification": "B.Sc. Chemistry",
        "experience": 2,
        "applied_on": date(2026, 9, 17),
        "status": "Resume",
    },
    {
        "candidate_no": "CAN-2026-0034",
        "candidate_name": "Priya Menon",
        "role": "English Teacher",
        "department": "Languages",
        "qualification": "M.A. English, B.Ed.",
        "experience": 8,
        "applied_on": date(2026, 9, 10),
        "interview_on": date(2026, 9, 22),
        "emp_id": "EMP-0036",
        "status": "Hired",
    },
    {
        "candidate_no": "CAN-2026-0035",
        "candidate_name": "Deepak Choudhary",
        "role": "Sports Coach",
        "department": "Sports",
        "qualification": "B.P.Ed.",
        "experience": 5,
        "applied_on": date(2026, 9, 12),
        "interview_on": date(2026, 9, 24),
        "status": "Rejected",
    },
]


def _seed_hiring(session: Session) -> None:
    """Vacancies + candidates, each skipped when its table already has rows."""
    if not session.exec(select(StaffVacancy)).first():
        for role, department, openings in STAFF_VACANCIES:
            session.add(
                StaffVacancy(
                    role=role, department=department, openings=openings, status="Open"
                )
            )
        session.commit()
        print(f"[seed_operations] {len(STAFF_VACANCIES)} open vacancies inserted")

    if session.exec(select(HiringCandidate)).first():
        print("[seed_operations] hiring candidates already exist. Skipping...")
        return

    for row in HIRING_ROWS:
        session.add(HiringCandidate(**row))
    session.commit()
    print(f"[seed_operations] {len(HIRING_ROWS)} hiring candidates inserted")


# ---------------------------------------------------------------------------
# 3. Fees Structure - the class-wise fee card
# ---------------------------------------------------------------------------

#: (head, class, frequency, amount, due day, status). Tuition is per class
#: because that is how a school publishes a fee card; one head stays a Draft so
#: the screen shows both publish states.
FEE_HEADS: list[tuple[str, str, FeeFrequency, float, str, str]] = [
    ("Tuition Fee", "Grade 6", FeeFrequency.monthly, 4500, "10th of month", "Active"),
    ("Tuition Fee", "Grade 7", FeeFrequency.monthly, 4900, "10th of month", "Active"),
    ("Tuition Fee", "Grade 8", FeeFrequency.monthly, 5400, "10th of month", "Active"),
    ("Tuition Fee", "Grade 9", FeeFrequency.monthly, 5800, "10th of month", "Active"),
    ("Tuition Fee", "Grade 10", FeeFrequency.monthly, 6200, "10th of month", "Active"),
    ("Transport Fee", "Grade 6", FeeFrequency.term, 8500, "5th of term", "Active"),
    ("Lab & Activity", "Grade 9", FeeFrequency.yearly, 12000, "1st June", "Active"),
    ("Lab & Activity", "Grade 10", FeeFrequency.yearly, 12000, "1st June", "Active"),
    ("Admission Fee", "Grade 6", FeeFrequency.one_time, 25000, "At admission", "Draft"),
]


def _seed_fee_heads(session: Session) -> None:
    """Upsert the fee card by (head, class).

    The amount, frequency and wording are written on every run - this script
    owns the demo fee card. The publish state is only set on rows *this* script
    creates, so a head the office unpublished by hand stays unpublished across
    a container restart.
    """
    grades = {grade.name: grade for grade in session.exec(select(GradeClass)).all()}
    created = 0
    for head, class_name, frequency, amount, due_day, status in FEE_HEADS:
        grade = grades.get(class_name)
        if grade is None:
            continue
        existing = session.exec(
            select(FeeStructure)
            .where(FeeStructure.name == head)
            .where(FeeStructure.grade_class_id == grade.id)
        ).first()
        if existing is None:
            session.add(
                FeeStructure(
                    name=head,
                    amount=amount,
                    grade_class_id=grade.id,
                    frequency=frequency,
                    due_day=due_day,
                    status=status,
                )
            )
            created += 1
            continue
        # seed.py already created this head: keep the row, align the wording.
        existing.amount = amount
        existing.frequency = frequency
        existing.due_day = due_day
        session.add(existing)
    session.commit()
    print(f"[seed_operations] {created} fee head(s) created ({len(FEE_HEADS)} checked)")


# ---------------------------------------------------------------------------
# 4. Staff Salary - three months of the register
# ---------------------------------------------------------------------------

#: The months the register covers, newest first (the month dropdown reads them
#: in exactly this order) paired with the day the salary was paid.
SALARY_MONTHS: list[tuple[str, date]] = [
    ("Sep 2026", date(2026, 9, 30)),
    ("Aug 2026", date(2026, 8, 31)),
    ("Jul 2026", date(2026, 7, 31)),
]

#: Gross monthly salary by department (a school's pay bands), with a flat
#: deduction rate standing in for PF/tax.
SALARY_BY_DEPARTMENT: dict[str, float] = {
    "Mathematics": 62000,
    "Science": 58000,
    "English": 54000,
    "Social Studies": 51000,
}
DEFAULT_GROSS = 45000
DEDUCTION_RATE = 0.12

#: How the newest month is left mid-run, so the screen has work to do: the
#: leftover teachers (beyond this list) stay Pending.
LATEST_MONTH_STATUSES = (STATUS_PAID, STATUS_PAID, STATUS_PROCESSING, STATUS_PENDING)


def _seed_salary(session: Session) -> None:
    """One row per staff member per month, for the last three months."""
    if session.exec(select(SalaryPayment)).first():
        print("[seed_operations] salary register already exists. Skipping...")
        return

    teachers = list(
        session.exec(select(TeacherProfile).order_by(TeacherProfile.id)).all()
    )
    latest_month = SALARY_MONTHS[0][0]
    inserted = 0

    for month_label, paid_on in SALARY_MONTHS:
        for index, teacher in enumerate(teachers):
            user = session.get(User, teacher.user_id)
            gross = SALARY_BY_DEPARTMENT.get(teacher.department, DEFAULT_GROSS)
            deductions = round(gross * DEDUCTION_RATE)
            if month_label == latest_month:
                status = LATEST_MONTH_STATUSES[
                    min(index, len(LATEST_MONTH_STATUSES) - 1)
                ]
            else:
                # Earlier months are closed: everyone was paid.
                status = STATUS_PAID
            session.add(
                SalaryPayment(
                    staff_code=f"EMP-{teacher.user_id:04d}",
                    staff_name=user.full_name if user else f"Staff {teacher.id}",
                    designation=f"{teacher.department} Teacher",
                    department=teacher.department,
                    month=month_label,
                    gross=gross,
                    deductions=deductions,
                    net=gross - deductions,
                    status=status,
                    paid_on=paid_on if status == STATUS_PAID else None,
                )
            )
            inserted += 1

    session.commit()
    print(f"[seed_operations] {inserted} salary rows inserted")


def seed_operations() -> None:
    """Insert the Operations demo data (every block skips itself if done)."""
    with Session(engine) as session:
        _seed_admissions(session)
        _seed_hiring(session)
        _seed_fee_heads(session)
        _seed_salary(session)
    print("[seed_operations] Operations demo data ready")


if __name__ == "__main__":
    seed_operations()
