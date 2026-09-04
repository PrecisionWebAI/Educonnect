"use client";
import { useState } from "react";
import { PageHeader, Tabs, Input, Select, Button, Spinner } from "@/components/ui";
import { usePayroll, type PayrollTab } from "./usePayroll";
import SalaryStructureView from "./SalaryStructureView";
import MonthProcessingTable from "./MonthProcessingTable";
import PayslipGrid from "./PayslipGrid";

const TABS: PayrollTab[] = ["Salary Structure", "Month Processing", "Payslips"];

export function currency(n: number) {
    return "₹" + n.toLocaleString("en-IN");
}

export default function PayrollPage() {
    const [tab, setTab] = useState<PayrollTab>("Salary Structure");
    const p = usePayroll(tab);

    const payrollStatusTone: Record<string, "amber" | "accent" | "green"> = {
        Draft: "amber",
        Posted: "accent",
        Paid: "green",
    };
    const payrollStatusToneFor = (s: string) => payrollStatusTone[s] ?? "muted";

    return (
        <div>
            <PageHeader
                title="Payroll / Payslip"
                subtitle="Salary structures, monthly processing and payslips."
                actions={<Button variant="primary">+ Run Payroll</Button>}
            />

            {p.loading ? (
                <Spinner />
            ) : (
                <>
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

                    <Tabs tabs={TABS} active={tab} onChange={(t) => setTab(t as PayrollTab)} />

                    {tab === "Salary Structure" && (
                        <SalaryStructureView structures={p.structures} />
                    )}

                    {tab === "Month Processing" && (
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

                    {tab === "Payslips" && (
                        <PayslipGrid entries={p.entries} statusTone={payrollStatusToneFor} />
                    )}
                </>
            )}
        </div>
    );
}
