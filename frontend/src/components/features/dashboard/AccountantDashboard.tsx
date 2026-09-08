"use client";

import { useQueryClient } from "@tanstack/react-query";
import { getAccountantSummary, getApprovals } from "@/services";
import { useApiQuery } from "@/lib/api/use-api-query";
import type { ApprovalItem } from "@/types";
import { PageHeader, Card, Spinner, Button } from "@/components/ui";
import { useToast } from "@/components/ui/toast";
import Icon from "@/components/ui/Icon";

// Tab D.8 — Accountant Dashboard (green)
export default function AccountantDashboard() {
    const toast = useToast();
    const queryClient = useQueryClient();
    const summaryQuery = useApiQuery(["dashboard", "accountant-summary"], getAccountantSummary);
    const approvalsQuery = useApiQuery(["dashboard", "approvals"], getApprovals);
    const summary = summaryQuery.data ?? null;
    const approvals = (approvalsQuery.data ?? []).filter((x) => x.kind === "Fee waiver");

    /** Cache-backed approvals setter (approve/decline removes the item for everyone). */
    function setApprovals(action: (prev: ApprovalItem[]) => ApprovalItem[]) {
        queryClient.setQueryData<ApprovalItem[]>(["dashboard", "approvals"], (prev) =>
            action(prev ?? []),
        );
    }

    if (!summary) return <Spinner />;

    const cards = [
        { icon: "wallet" as const, label: "Collected Today", value: summary.collectedToday },
        { icon: "trending" as const, label: "Collected (Month)", value: summary.collectedMonth },
        { icon: "warning" as const, label: "Pending Dues", value: String(summary.pendingDues) },
        { icon: "money" as const, label: "Payroll Run", value: summary.payrollRun },
    ];

    return (
        <div className="page">
            <PageHeader title="Finance Overview" subtitle="Accountant dashboard" />

            <div className="kpi-grid">
                {cards.map((c) => (
                    <div key={c.label} className="stat">
                        <span className="stat-ico">
                            <Icon name={c.icon} size={20} />
                        </span>
                        <div className="stat-value">{c.value}</div>
                        <div className="stat-label">{c.label}</div>
                    </div>
                ))}
            </div>

            <div className="dash-grid" style={{ marginTop: "1rem" }}>
                <Card title="Pending Fee Waiver Approvals" className="dash-span-2">
                    {approvals.length === 0 ? (
                        <p style={{ color: "var(--muted)" }}>No pending fee waivers.</p>
                    ) : (
                        <ul className="feed">
                            {approvals.map((a) => (
                                <li key={a.id} className="feed-item">
                                    <div className="feed-body">
                                        <span className="feed-title">{a.summary}</span>
                                        <span className="feed-sub">
                                            {a.requester} · {a.time}
                                        </span>
                                    </div>
                                    <Button
                                        size="sm"
                                        variant="success"
                                        onClick={() => {
                                            setApprovals((p) => p.filter((x) => x.id !== a.id));
                                            toast.push("success", "Waiver approved");
                                        }}
                                    >
                                        Approve
                                    </Button>
                                    <Button
                                        size="sm"
                                        variant="ghost"
                                        onClick={() => {
                                            setApprovals((p) => p.filter((x) => x.id !== a.id));
                                            toast.push("info", "Waiver declined");
                                        }}
                                    >
                                        Decline
                                    </Button>
                                </li>
                            ))}
                        </ul>
                    )}
                </Card>
            </div>
        </div>
    );
}
