import type { SalaryPaymentRow } from "@/types";
import { api } from "@/lib/api/client";
import { toCamel } from "@/lib/api/case";

// ============================================================
// Operations ▸ Staff Salary service — talks to `salarypayment`.
//
//   GET  /salary/register               the register (newest month first)
//   POST /salary/payroll/run            queue a month's Pending rows
//   PUT  /salary/register/{id}/pay      mark one row Paid
//
// The month labels and the department list are derived from the rows in
// `useSalary`, and `paidOn` is stamped by the server, so nothing on this screen
// depends on a constant shipping with the frontend.
// ============================================================

export async function getSalaryRegister(): Promise<SalaryPaymentRow[]> {
    return toCamel<SalaryPaymentRow[]>(await api.get("/salary/register"));
}

export interface PayrollRunResult {
    month: string;
    queued: number;
}

export async function runSalaryPayroll(month: string): Promise<PayrollRunResult> {
    return api.post<PayrollRunResult>("/salary/payroll/run", { month });
}

export async function markSalaryPaid(id: number): Promise<SalaryPaymentRow> {
    return toCamel<SalaryPaymentRow>(await api.put(`/salary/register/${id}/pay`));
}
