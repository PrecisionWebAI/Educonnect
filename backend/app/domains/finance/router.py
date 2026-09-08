from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.core.db import get_session
from app.domains.auth.dependencies import RequirePermission, get_current_active_user
from app.domains.auth.service import AuthorizationService
from app.domains.users.models import RoleEnum

from . import service
from .schemas import (
    CollectionReportRowRead,
    ExpenseItemRead,
    FeeInvoiceRead,
    FeeStructureCreate,
    FeeStructureRead,
    FeeTransactionCreate,
    FeeTransactionRead,
    PayrollEntryRead,
    SalaryStructureRowRead,
    StudentDuesResponse,
)

router = APIRouter()

# Removed RoleCheckers


@router.get("/structures", response_model=list[FeeStructureRead])
def read_fee_structures(
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("fees.read")),
):
    """
    List active fee structures.
    """
    return service.get_fee_structures(session=session, skip=skip, limit=limit)


@router.post(
    "/structures", response_model=FeeStructureRead, status_code=status.HTTP_201_CREATED
)
def create_fee_structure(
    structure_in: FeeStructureCreate,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("fees.manage_structure")),
):
    """
    Admin/Accountant creates a new fee rule.
    """
    return service.create_fee_structure(session=session, structure_in=structure_in)


@router.post(
    "/transactions",
    response_model=FeeTransactionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_transaction(
    transaction_in: FeeTransactionCreate,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("fees.create")),
):
    """
    Record a student's fee payment.
    """
    return service.create_transaction(session=session, transaction_in=transaction_in)


@router.get("/students/{student_id}/dues", response_model=StudentDuesResponse)
def get_student_dues(
    student_id: int,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("fees.read")),
    # Could also allow parents/students to see their own dues
):
    """
    Calculates and returns the pending fee balance for a student.
    """
    return service.get_student_dues(session=session, student_id=student_id)


@router.get("/invoices", response_model=list[FeeInvoiceRead])
def read_invoices(
    student_id: int | None = None,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("fees.read")),
):
    from sqlmodel import select

    from app.domains.students.models import StudentProfile

    if current_user.role == RoleEnum.student:
        sp = session.exec(
            select(StudentProfile).where(StudentProfile.user_id == current_user.id)
        ).first()
        if sp:
            student_id = sp.id

    all_invoices = [
        FeeInvoiceRead(
            id=1,
            student="Aarav Mehta",
            className="10-A",
            head="Tuition Fee",
            amount=45000,
            paid=45000,
            due=0,
            status="Paid",
        ),
        FeeInvoiceRead(
            id=2,
            student="Ishita Rao",
            className="9-B",
            head="Tuition Fee",
            amount=42000,
            paid=25000,
            due=17000,
            status="Partial",
        ),
        FeeInvoiceRead(
            id=3,
            student="Kabir Singh",
            className="11-A",
            head="Tuition Fee",
            amount=50000,
            paid=0,
            due=50000,
            status="Due",
        ),
        FeeInvoiceRead(
            id=4,
            student="Ananya Das",
            className="10-B",
            head="Transport Fee",
            amount=12000,
            paid=12000,
            due=0,
            status="Paid",
        ),
        FeeInvoiceRead(
            id=5,
            student="Rohan Gupta",
            className="8-A",
            head="Tuition Fee",
            amount=38000,
            paid=20000,
            due=18000,
            status="Partial",
        ),
        FeeInvoiceRead(
            id=6,
            student="Meera Nair",
            className="12-A",
            head="Caution Deposit",
            amount=20000,
            paid=0,
            due=20000,
            status="Due",
        ),
    ]

    # Map mock IDs to names for simple filtering
    student_map = {
        1: "Aarav Mehta",
        2: "Ishita Rao",
        3: "Kabir Singh",
        4: "Ananya Das",
        5: "Rohan Gupta",
        6: "Meera Nair",
    }

    if student_id and student_id in student_map:
        target_name = student_map[student_id]
        all_invoices = [inv for inv in all_invoices if inv.student == target_name]

    return all_invoices


@router.get("/expenses", response_model=list[ExpenseItemRead])
def read_expenses(
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("payroll.read")),
):
    return [
        ExpenseItemRead(
            id=1,
            vendor="ABC Stationery",
            head="Office Supplies",
            amount=12000,
            date="2026-08-28",
            status="Approved",
        ),
        ExpenseItemRead(
            id=2,
            vendor="Solar Solutions",
            head="Utilities",
            amount=45000,
            date="2026-08-30",
            status="Pending",
        ),
        ExpenseItemRead(
            id=3,
            vendor="TechMart",
            head="IT Equipment",
            amount=80000,
            date="2026-09-01",
            status="Pending",
        ),
        ExpenseItemRead(
            id=4,
            vendor="Garden Nursery",
            head="Maintenance",
            amount=15000,
            date="2026-08-25",
            status="Approved",
        ),
    ]


@router.get("/collection-reports", response_model=list[CollectionReportRowRead])
def read_collection_reports(
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("fees.read")),
):
    return [
        CollectionReportRowRead(
            id=1,
            period="Today",
            billed="₹1,20,000",
            collected="₹98,400",
            variance="-18%",
            mode="Cash 22% / Digital 78%",
        ),
        CollectionReportRowRead(
            id=2,
            period="This week",
            billed="₹6,10,000",
            collected="₹5,42,000",
            variance="-11%",
            mode="Cash 19% / Digital 81%",
        ),
        CollectionReportRowRead(
            id=3,
            period="Term 1",
            billed="₹84,00,000",
            collected="₹77,60,000",
            variance="-7.6%",
            mode="Cash 15% / Digital 85%",
        ),
    ]


@router.get("/salary-structure", response_model=list[SalaryStructureRowRead])
def read_salary_structure(
    teacher_id: int | None = None,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_active_user),
):
    from fastapi import HTTPException

    can_read = AuthorizationService.can(
        current_user, "payroll.read", session=session, teacher_id=teacher_id
    )
    can_view_payslip = AuthorizationService.can(
        current_user, "payroll.view_payslip", session=session, teacher_id=teacher_id
    )

    if not (can_read or can_view_payslip):
        raise HTTPException(status_code=403, detail="Missing required permission")

    all_structures = [
        SalaryStructureRowRead(
            id=1,
            staffCode="T-101",
            name="P. Menon",
            basic=42000,
            hra=16800,
            da=8400,
            special=6000,
            total=73200,
        ),
        SalaryStructureRowRead(
            id=2,
            staffCode="T-102",
            name="M. Iyer",
            basic=40000,
            hra=16000,
            da=8000,
            special=5000,
            total=69000,
        ),
        SalaryStructureRowRead(
            id=3,
            staffCode="T-104",
            name="S. Kapoor",
            basic=45000,
            hra=18000,
            da=9000,
            special=7000,
            total=79000,
        ),
        SalaryStructureRowRead(
            id=4,
            staffCode="T-105",
            name="R. Verma",
            basic=38000,
            hra=15200,
            da=7600,
            special=4500,
            total=65300,
        ),
        SalaryStructureRowRead(
            id=5,
            staffCode="T-106",
            name="K. Nair",
            basic=52000,
            hra=20800,
            da=10400,
            special=8000,
            total=91200,
        ),
        SalaryStructureRowRead(
            id=6,
            staffCode="T-107",
            name="D. Singh",
            basic=35000,
            hra=14000,
            da=7000,
            special=4000,
            total=60000,
        ),
    ]

    if current_user.role == RoleEnum.teacher:
        from sqlmodel import select

        from app.domains.teachers.models import TeacherProfile

        tp = session.exec(
            select(TeacherProfile).where(TeacherProfile.user_id == current_user.id)
        ).first()
        if tp:
            teacher_id = tp.id

    # Mock mapping
    staff_map = {1: "T-101", 2: "T-102", 3: "T-104", 4: "T-105", 5: "T-106", 6: "T-107"}

    if teacher_id and teacher_id in staff_map:
        target_code = staff_map[teacher_id]
        all_structures = [s for s in all_structures if s.staffCode == target_code]

    return all_structures


@router.get("/payroll", response_model=list[PayrollEntryRead])
def read_payroll(
    teacher_id: int | None = None,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_active_user),
):
    from fastapi import HTTPException

    can_read = AuthorizationService.can(
        current_user, "payroll.read", session=session, teacher_id=teacher_id
    )
    can_view_payslip = AuthorizationService.can(
        current_user, "payroll.view_payslip", session=session, teacher_id=teacher_id
    )

    if not (can_read or can_view_payslip):
        raise HTTPException(status_code=403, detail="Missing required permission")

    all_payroll = [
        PayrollEntryRead(
            id=1,
            staffCode="T-101",
            name="P. Menon",
            basic=42000,
            allowances=31200,
            deductions=5200,
            net=68000,
            status="Paid",
        ),
        PayrollEntryRead(
            id=2,
            staffCode="T-102",
            name="M. Iyer",
            basic=40000,
            allowances=29000,
            deductions=4800,
            net=64200,
            status="Posted",
        ),
        PayrollEntryRead(
            id=3,
            staffCode="T-104",
            name="S. Kapoor",
            basic=45000,
            allowances=34000,
            deductions=5500,
            net=73500,
            status="Draft",
        ),
        PayrollEntryRead(
            id=4,
            staffCode="T-106",
            name="K. Nair",
            basic=52000,
            allowances=39200,
            deductions=6400,
            net=84800,
            status="Paid",
        ),
    ]

    if current_user.role == RoleEnum.teacher:
        from sqlmodel import select

        from app.domains.teachers.models import TeacherProfile

        tp = session.exec(
            select(TeacherProfile).where(TeacherProfile.user_id == current_user.id)
        ).first()
        if tp:
            teacher_id = tp.id

    # Mock mapping
    staff_map = {1: "T-101", 2: "T-102", 3: "T-104", 4: "T-105", 5: "T-106", 6: "T-107"}

    if teacher_id and teacher_id in staff_map:
        target_code = staff_map[teacher_id]
        all_payroll = [p for p in all_payroll if p.staffCode == target_code]

    return all_payroll
