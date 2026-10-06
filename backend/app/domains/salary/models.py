"""Staff salary register - the Operations > Staff Salary screen.

One row is one salary payment: a staff member, a month, and the money. It is a
**register**, not a payslip header, so:

* `staff_code` / `staff_name` / `designation` / `department` are snapshots taken
  when the row is created. A teacher who changes department next year must not
  rewrite last year's register.
* `month` is stored as the label the register shows ("Sep 2026") because the
  screen groups and filters by exactly that string.
* `status` walks Pending -> Processing -> Paid; `paid_on` is stamped when the
  row is marked Paid, which is what makes "Paid" trustworthy.
"""

from datetime import date

from sqlmodel import Field, SQLModel

# Register states, stored exactly as the screen labels them.
STATUS_PENDING = "Pending"
STATUS_PROCESSING = "Processing"
STATUS_PAID = "Paid"


class SalaryPaymentBase(SQLModel):
    staff_code: str = Field(index=True)  # EMP-0037
    staff_name: str
    designation: str
    department: str
    month: str = Field(index=True)  # "Sep 2026"
    gross: float = 0.0
    deductions: float = 0.0
    net: float = 0.0
    status: str = Field(default=STATUS_PENDING)
    paid_on: date | None = None


class SalaryPayment(SalaryPaymentBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
