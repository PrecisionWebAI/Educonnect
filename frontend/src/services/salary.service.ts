import type { SalaryPaymentRow } from "@/types";

// ============================================================
// Operations ▸ Salary (Staff) service.
//
// The schema currently stores only the static `staffprofile.salary`
// figure — there is no salary-payment table — so this register is
// hard-coded. Once a `salary_payment` table + payroll endpoint exist,
// swap the body for `api.get<SalaryPaymentRow[]>("/payroll/register")`.
// ============================================================

export const SALARY_MONTHS = ["Sep 2026", "Aug 2026", "Jul 2026"];

export const SALARY_DEPARTMENTS = [
    "All Departments",
    "Science",
    "Mathematics",
    "Languages",
    "Sports",
];

const REGISTER: SalaryPaymentRow[] = [
    {
        id: 1,
        staffCode: "EMP-0012",
        staffName: "Rohan Deshmukh",
        designation: "Physics Teacher",
        department: "Science",
        month: "Sep 2026",
        gross: 62000,
        deductions: 7400,
        net: 54600,
        status: "Paid",
        paidOn: "2026-09-30",
    },
    {
        id: 2,
        staffCode: "EMP-0018",
        staffName: "Sneha Kulkarni",
        designation: "Mathematics Teacher",
        department: "Mathematics",
        month: "Sep 2026",
        gross: 54000,
        deductions: 6300,
        net: 47700,
        status: "Paid",
        paidOn: "2026-09-30",
    },
    {
        id: 3,
        staffCode: "EMP-0024",
        staffName: "Priya Menon",
        designation: "English Teacher",
        department: "Languages",
        month: "Sep 2026",
        gross: 58000,
        deductions: 6900,
        net: 51100,
        status: "Processing",
        paidOn: "—",
    },
    {
        id: 4,
        staffCode: "EMP-0031",
        staffName: "Imran Sheikh",
        designation: "Lab Assistant",
        department: "Science",
        month: "Sep 2026",
        gross: 26000,
        deductions: 2800,
        net: 23200,
        status: "Pending",
        paidOn: "—",
    },
    {
        id: 5,
        staffCode: "EMP-0035",
        staffName: "Deepak Choudhary",
        designation: "Sports Coach",
        department: "Sports",
        month: "Sep 2026",
        gross: 34000,
        deductions: 3900,
        net: 30100,
        status: "Paid",
        paidOn: "2026-09-30",
    },
];

export async function getSalaryRegister(): Promise<SalaryPaymentRow[]> {
    return REGISTER;
}
