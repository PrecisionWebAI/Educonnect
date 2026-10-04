"use client";

import { Button, Input, PageHeader, Select, Spinner, Tabs } from "@/components/ui";
import { useToast } from "@/components/ui/toast";
import RoleGuard from "@/components/auth/RoleGuard";
import { errorMessage } from "@/lib/api/client";
import { inr } from "@/lib/format";
import DepartmentSummaryTable from "./DepartmentSummaryTable";
import SalaryRegisterTable from "./SalaryRegisterTable";
import { SALARY_STATUS_OPTIONS, useSalary } from "./useSalary";
import type { SalaryPaymentRow, SalaryPaymentStatus } from "@/types";

// Operations ▸ Salary (Staff) (container).
// Monthly payouts for teachers and support staff, sitting on top of the
// same staff records the Payroll / Payslip module uses.

const TABS = ["Salary Register", "Department Summary"];

export default function SalaryPage() {
    const toast = useToast();
    const s = useSalary();

    async function runPayroll() {
        try {
            const queued = await s.runPayroll();
            if (queued === 0) {
                toast.push("info", `Payroll for ${s.month} is already settled`);
                return;
            }
            toast.push("success", `${queued} salary row(s) queued for ${s.month}`);
        } catch (error) {
            toast.push("error", errorMessage(error, "Could not run payroll"));
        }
    }

    async function markPaid(row: SalaryPaymentRow) {
        try {
            await s.markPaid(row);
            toast.push("success", `${row.staffName} marked paid — ${inr(row.net)}`);
        } catch (error) {
            toast.push("error", errorMessage(error, "Could not mark the salary as paid"));
        }
    }

    function payslip(row: SalaryPaymentRow) {
        toast.push("info", `Payslip for ${row.staffName} (${row.month}) queued for email`);
    }

    return (
        <RoleGuard allowedRoles={["SYSTEM_ADMIN", "OWNER", "PRINCIPAL", "ACCOUNTANT"]}>
            <div className="page">
                <PageHeader
                    title="Staff Salary"
                    subtitle="Monthly salary register, deductions and payouts for teachers and support staff."
                    actions={
                        <Button variant="primary" onClick={runPayroll}>
                            Run Payroll — {s.month}
                        </Button>
                    }
                />

                {s.loading ? (
                    <Spinner />
                ) : (
                    <>
                        <div className="stat-tiles">
                            <div className="stat-tile">
                                <b>{inr(s.counts.netPayable)}</b>
                                <span>Net Payable</span>
                            </div>
                            <div className="stat-tile">
                                <b>{s.counts.paid}</b>
                                <span>Paid</span>
                            </div>
                            <div className="stat-tile">
                                <b>{s.counts.processing}</b>
                                <span>Processing</span>
                            </div>
                            <div className="stat-tile">
                                <b>{s.counts.pending}</b>
                                <span>Pending</span>
                            </div>
                            <div className="stat-tile">
                                <b>{inr(s.counts.outstanding)}</b>
                                <span>Outstanding</span>
                            </div>
                        </div>

                        <Tabs
                            tabs={TABS}
                            active={s.tab}
                            onChange={(t) => s.setTab(t as typeof s.tab)}
                        />

                        {s.tab === "Salary Register" ? (
                            <>
                                <div className="toolbar">
                                    <div className="toolbar-search">
                                        <Input
                                            placeholder="Search staff, ID, designation…"
                                            value={s.query}
                                            onChange={(e) => s.setQuery(e.target.value)}
                                        />
                                    </div>
                                    <Select
                                        value={s.month}
                                        onChange={(e) => s.setMonth(e.target.value)}
                                    >
                                        {s.months.map((m) => (
                                            <option key={m} value={m}>
                                                {m}
                                            </option>
                                        ))}
                                    </Select>
                                    <Select
                                        value={s.department}
                                        onChange={(e) => s.setDepartment(e.target.value)}
                                    >
                                        {s.departments.map((d) => (
                                            <option key={d} value={d}>
                                                {d}
                                            </option>
                                        ))}
                                    </Select>
                                    <Select
                                        value={s.status}
                                        onChange={(e) =>
                                            s.setStatus(
                                                e.target.value as SalaryPaymentStatus | "All",
                                            )
                                        }
                                    >
                                        {SALARY_STATUS_OPTIONS.map((o) => (
                                            <option key={o} value={o}>
                                                {o}
                                            </option>
                                        ))}
                                    </Select>
                                </div>

                                <SalaryRegisterTable
                                    rows={s.filtered}
                                    onMarkPaid={markPaid}
                                    onPayslip={payslip}
                                />

                                <p className="text-muted-foreground mt-3 text-sm">
                                    Showing {s.filtered.length} of {s.monthRows.length} salary
                                    rows for {s.month}
                                </p>
                            </>
                        ) : (
                            <DepartmentSummaryTable rows={s.departmentSummary} />
                        )}
                    </>
                )}
            </div>
        </RoleGuard>
    );
}

