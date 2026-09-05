"use client";
import { useMemo, useState } from "react";
import { PageHeader, Tabs, Input, Select, Button, Spinner } from "@/components/ui";
import { useAuth } from "@/providers/auth-context";
import { hasAnyRole } from "@/lib/auth/rbac";
import RoleGuard from "@/components/auth/RoleGuard";
import { usePayroll, type PayrollTab } from "./usePayroll";
import SalaryStructureView from "./SalaryStructureView";
import MonthProcessingTable from "./MonthProcessingTable";
import PayslipGrid from "./PayslipGrid";

const ALL_TABS: PayrollTab[] = ["Salary Structure", "Month Processing", "Payslips"];

export function currency(n: number) {
    return "₹" + n.toLocaleString("en-IN");
}

export default function PayrollPage() {
    const { user } = useAuth();
    const canManagePayroll = hasAnyRole(user?.roles, [
        "ACCOUNTANT",
        "DIRECTOR",
        "PRINCIPAL",
        "ADMIN",
    ]);

    const allowedTabs = useMemo(() => {
        if (!canManagePayroll) {
            return ["Payslips" as PayrollTab];
        }
        return ALL_TABS;
    }, [canManagePayroll]);

    const [tab, setTab] = useState<PayrollTab>(() =>
        canManagePayroll ? "Salary Structure" : "Payslips",
    );
    const activeTab = allowedTabs.includes(tab) ? tab : allowedTabs[0];

    const p = usePayroll(activeTab);

    const payrollStatusTone: Record<string, "amber" | "accent" | "green"> = {
        Draft: "amber",
        Posted: "accent",
        Paid: "green",
    };
    const payrollStatusToneFor = (s: string) => payrollStatusTone[s] ?? "muted";

    return (
        <RoleGuard
            allowedRoles={[
                "ACCOUNTANT",
                "DIRECTOR",
                "PRINCIPAL",
                "ADMIN",
                "CLASS_TEACHER",
                "SUBJECT_TEACHER",
            ]}
        >
            <div>
                <PageHeader
                    title={canManagePayroll ? "Payroll / Payslip" : "My Payslips"}
                    subtitle={
                        canManagePayroll
                            ? "Salary structures, monthly processing and payslips."
                            : "View and download your monthly salary slips."
                    }
                    actions={
                        canManagePayroll && <Button variant="primary">+ Run Payroll</Button>
                    }
                />

                {p.loading ? (
                    <Spinner />
                ) : (
                    <>
                        {canManagePayroll && (
                            <div className="stat-tiles">
                                <div className="stat-tile">
                                    <b>{p.structures.length}</b>
                                    <span>Employees</span>
                                </div>
                                <div className="stat-tile">
                                    <b>{currency(p.totalPayroll)}</b>
                                    <span>Total Net Pay</span>
                                </div>
                                <div className="stat-tile">
                                    <b>{p.paidCount}</b>
                                    <span>Paid</span>
                                </div>
                                <div className="stat-tile">
                                    <b>{p.draftCount}</b>
                                    <span>Draft</span>
                                </div>
                            </div>
                        )}

                        <Tabs
                            tabs={allowedTabs}
                            active={activeTab}
                            onChange={(t) => setTab(t as PayrollTab)}
                        />

                        {activeTab === "Salary Structure" && canManagePayroll && (
                            <SalaryStructureView structures={p.structures} />
                        )}

                        {activeTab === "Month Processing" && canManagePayroll && (
                            <>
                                <div className="toolbar">
                                    <div className="toolbar-search">
                                        <Input
                                            placeholder="Search name, ID…"
                                            value={p.query}
                                            onChange={(e) => p.setQuery(e.target.value)}
                                        />
                                    </div>
                                    <Select
                                        value={p.status}
                                        onChange={(e) => p.setStatus(e.target.value)}
                                    >
                                        {p.statuses.map((s) => (
                                            <option key={s} value={s}>
                                                {s}
                                            </option>
                                        ))}
                                    </Select>
                                </div>
                                <MonthProcessingTable
                                    rows={p.filtered}
                                    statusTone={payrollStatusToneFor}
                                />
                            </>
                        )}

                        {activeTab === "Payslips" && (
                            <PayslipGrid entries={p.entries} statusTone={payrollStatusToneFor} />
                        )}
                    </>
                )}
            </div>
        </RoleGuard>
    );
}
