"use client";
import { useState } from "react";
import { PageHeader, Tabs, Input, Select, Button, Spinner } from "@/components/ui";
import { useFinance, type FinanceTab } from "./useFinance";
import FeeInvoicesTable from "./FeeInvoicesTable";
import ExpensesTable from "./ExpensesTable";
import FinanceReportsTab from "./FinanceReportsTab";
import { inr } from "./FeeInvoicesTable";

const TABS: FinanceTab[] = ["Fee Collection", "Dues & Recovery", "Expenses & Budget", "Reports"];

export default function FinancePage() {
    const [tab, setTab] = useState<FinanceTab>("Fee Collection");
    const f = useFinance(tab);
    const dues = f.invoices.filter((i) => i.due > 0);
    const totalDues = dues.reduce((a, i) => a + i.due, 0);

    return (
        <div>
            <PageHeader
                title="Finance & Fees"
                subtitle="Fee collection, dues & recovery, expenses and budget."
                actions={<Button variant="primary">+ Record Payment</Button>}
            />

            {f.loading ? (
                <Spinner />
            ) : (
                <>
                    <div className="stat-tiles">
                        <div className="stat-tile">
                            <b>{inr(f.collected)}</b>
                            <span>Collected</span>
                        </div>
                        <div className="stat-tile">
                            <b>{f.invoicesCount}</b>
                            <span>Invoices</span>
                        </div>
                        <div className="stat-tile">
                            <b>{f.pendingDues}</b>
                            <span>In Dues</span>
                        </div>
                        <div className="stat-tile">
                            <b>{f.paidCount}</b>
                            <span>Fully Paid</span>
                        </div>
                    </div>

                    <Tabs tabs={TABS} active={tab} onChange={(t) => setTab(t as FinanceTab)} />

                    {(tab === "Fee Collection" || tab === "Dues & Recovery") && (
                        <>
                            <div className="toolbar">
                                <div className="toolbar-search">
                                    <Input
                                        placeholder="Search student, class, fee head…"
                                        value={f.query}
                                        onChange={(e) => f.setQuery(e.target.value)}
                                    />
                                </div>
                                <Select
                                    value={f.status}
                                    onChange={(e) => f.setStatus(e.target.value)}
                                >
                                    {f.statuses.map((s) => (
                                        <option key={s} value={s}>
                                            {s}
                                        </option>
                                    ))}
                                </Select>
                            </div>
                            {tab === "Dues & Recovery" && (
                                <p style={{ color: "var(--muted)", marginBottom: "0.6rem" }}>
                                    Outstanding dues:{" "}
                                    <b style={{ color: "#fda4af" }}>{inr(totalDues)}</b>
                                </p>
                            )}
                            <FeeInvoicesTable
                                rows={tab === "Dues & Recovery" ? dues : f.filtered}
                            />
                        </>
                    )}

                    {tab === "Expenses & Budget" && <ExpensesTable rows={f.expenses} />}

                    {tab === "Reports" && <FinanceReportsTab />}
                </>
            )}
        </div>
    );
}
