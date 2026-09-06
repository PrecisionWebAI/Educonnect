from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.core.db import get_session
from app.domains.auth.dependencies import RoleChecker
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

AdminOrAccountant = RoleChecker(
    [RoleEnum.admin, RoleEnum.accountant, RoleEnum.director]
)


@router.get("/structures", response_model=list[FeeStructureRead])
def read_fee_structures(
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session),
    current_user=Depends(AdminOrAccountant),
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
    current_user=Depends(AdminOrAccountant),
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
    current_user=Depends(AdminOrAccountant),
):
    """
    Record a student's fee payment.
    """
    return service.create_transaction(session=session, transaction_in=transaction_in)


@router.get("/students/{student_id}/dues", response_model=StudentDuesResponse)
def get_student_dues(
    student_id: int,
    session: Session = Depends(get_session),
    current_user=Depends(
        RoleChecker(
            [RoleEnum.admin, RoleEnum.accountant, RoleEnum.director, RoleEnum.principal]
        )
    ),
    # Could also allow parents/students to see their own dues
):
    """
    Calculates and returns the pending fee balance for a student.
    """
    return service.get_student_dues(session=session, student_id=student_id)


@router.get("/invoices", response_model=list[FeeInvoiceRead])
def read_invoices(session: Session = Depends(get_session)):
    return [
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


@router.get("/expenses", response_model=list[ExpenseItemRead])
def read_expenses(session: Session = Depends(get_session)):
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
def read_collection_reports(session: Session = Depends(get_session)):
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
def read_salary_structure(session: Session = Depends(get_session)):
    return [
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


@router.get("/payroll", response_model=list[PayrollEntryRead])
def read_payroll(session: Session = Depends(get_session)):
    return [
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
