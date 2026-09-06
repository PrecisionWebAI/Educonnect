"use client";
import { useMemo, useState } from "react";
import { PageHeader, Tabs, Input, Select, Button, Spinner } from "@/components/ui";
import { useAuth } from "@/providers/auth-context";
import { hasAnyRole, isStudent, isParent, FINANCE_ROLES } from "@/lib/auth/rbac";
import RoleGuard from "@/components/auth/RoleGuard";
import { useFinance, type FinanceTab } from "./useFinance";
import FeeInvoicesTable from "./FeeInvoicesTable";
import ExpensesTable from "./ExpensesTable";
import FinanceReportsTab from "./FinanceReportsTab";
import { inr } from "./FeeInvoicesTable";

const ALL_TABS: FinanceTab[] = [
    "Fee Collection",
    "Dues & Recovery",
    "Expenses & Budget",
    "Reports",
];

export default function FinancePage() {
    const { user } = useAuth();
    const isStudentUser = isStudent(user?.roles);
    const isParentUser = isParent(user?.roles);
    const canManageFinance = hasAnyRole(user?.roles, FINANCE_ROLES);

    const allowedTabs = useMemo(() => {
        if (isStudentUser || isParentUser) {
            return ["Fee Collection" as FinanceTab];
        }
        return ALL_TABS;
    }, [isStudentUser, isParentUser]);

    const [tab, setTab] = useState<FinanceTab>("Fee Collection");
    const activeTab = allowedTabs.includes(tab) ? tab : allowedTabs[0];

    const f = useFinance(activeTab);

    const userFullName = user?.fullName?.toLowerCase() ?? "";

    // Scoped invoices for student / parent
    const scopedInvoices = useMemo(() => {
        if (isStudentUser && userFullName) {
            return f.invoices.filter((i) => i.student.toLowerCase().includes(userFullName));
        }
        if (isParentUser) {
            return f.invoices.filter((i) => i.student.includes("Bart"));
        }
        return f.filtered;
    }, [f.invoices, f.filtered, isStudentUser, isParentUser, userFullName]);

    const dues = scopedInvoices.filter((i) => i.due > 0);
    const totalDues = dues.reduce((a, i) => a + i.due, 0);

    const title = isStudentUser
        ? "My Fees & Receipts"
        : isParentUser
          ? "Child Fee & Payment Details"
          : "Finance & Fees";

    const subtitle =
        isStudentUser || isParentUser
            ? "View fee invoices, online receipts, and outstanding dues."
            : "Fee collection, dues & recovery, expenses and budget.";

    return (
        <RoleGuard
            allowedRoles={[
                "ACCOUNTANT",
                "DIRECTOR",
                "ADMIN",
                "PRINCIPAL",
                "GUARDIAN",
                "STUDENT",
            ]}
        >
            <div>
                <PageHeader
                    title={title}
                    subtitle={subtitle}
                    actions={
                        canManageFinance && (
                            <Button variant="primary">+ Record Payment</Button>
                        )
                    }
                />

                {f.loading ? (
                    <Spinner />
                ) : (
                    <>
                        <div className="stat-tiles">
                            {canManageFinance ? (
                                <>
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
                                </>
                            ) : (
                                <>
                                    <div className="stat-tile">
                                        <b>
                                            {inr(
                                                scopedInvoices.reduce((a, i) => a + i.amount, 0),
                                            )}
                                        </b>
                                        <span>Total Fees</span>
                                    </div>
                                    <div className="stat-tile">
                                        <b>
                                            {inr(
                                                scopedInvoices.reduce(
                                                    (a, i) => a + (i.amount - i.due),
                                                    0,
                                                ),
                                            )}
                                        </b>
                                        <span>Paid</span>
                                    </div>
                                    <div className="stat-tile">
                                        <b>{inr(totalDues)}</b>
                                        <span>Pending Dues</span>
                                    </div>
                                    <div className="stat-tile">
                                        <b>
                                            {
                                                scopedInvoices.filter((i) => i.status === "Paid")
                                                    .length
                                            }
                                        </b>
                                        <span>Receipts</span>
                                    </div>
                                </>
                            )}
                        </div>

                        <Tabs
                            tabs={allowedTabs}
                            active={activeTab}
                            onChange={(t) => setTab(t as FinanceTab)}
                        />

                        {(activeTab === "Fee Collection" || activeTab === "Dues & Recovery") && (
                            <>
                                {canManageFinance && (
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
                                )}
                                {activeTab === "Dues & Recovery" && (
                                    <p style={{ color: "var(--muted)", marginBottom: "0.6rem" }}>
                                        Outstanding dues:{" "}
                                        <b style={{ color: "#fda4af" }}>{inr(totalDues)}</b>
                                    </p>
                                )}
                                <FeeInvoicesTable
                                    rows={activeTab === "Dues & Recovery" ? dues : scopedInvoices}
                                />
                            </>
                        )}

                        {activeTab === "Expenses & Budget" && canManageFinance && (
                            <ExpensesTable rows={f.expenses} />
                        )}

                        {activeTab === "Reports" && canManageFinance && <FinanceReportsTab />}
                    </>
                )}
            </div>
        </RoleGuard>
    );
}
