"use client";
import { useState } from "react";
import Link from "next/link";
import { Badge, Spinner, Table, Tabs } from "@/components/ui";
import { errorMessage } from "@/lib/api/client";
import { useApiQuery } from "@/lib/api/use-api-query";
import { getLeaveTabRows, getVisibleLeaveKinds } from "@/services";
import type { LeaveTabRow } from "@/types";

/**
 * The Staff / Student leave tabs (0.10) - one table, two filtered views.
 *
 * Which tabs are drawn is the **server's** answer (`/leave/visible-kinds`), not a
 * role list copied here: a teacher has `leave.read` but nothing to see on the
 * Student tab, and `kind=student` would not widen their rows anyway. The rows are
 * read-only - filing and deciding belong to Leave & Applications, which the footer
 * links to.
 */
export default function LeaveTabsPanel() {
    const kindsQuery = useApiQuery(["leave", "visible-kinds"], getVisibleLeaveKinds);
    const kinds = kindsQuery.data?.kinds ?? [];
    const [kind, setKind] = useState<"staff" | "student" | null>(null);
    const active: "staff" | "student" = kind ?? kinds[0] ?? "staff";

    const rowsQuery = useApiQuery(["leave", "tab", active], () => getLeaveTabRows(active), {
        enabled: kinds.length > 0,
    });

    const columns = [
        { key: "person", header: "Name" },
        {
            key: "code",
            header: "Code",
            render: (row: LeaveTabRow) => row.code ?? "â€”",
        },
        { key: "leaveType", header: "Type" },
        {
            key: "window",
            header: "Dates",
            render: (row: LeaveTabRow) => `${row.fromDate} â†’ ${row.toDate}`,
        },
        { key: "days", header: "Days" },
        {
            key: "status",
            header: "Status",
            render: (row: LeaveTabRow) => (
                <Badge
                    tone={
                        row.status === "Approved"
                            ? "green"
                            : row.status === "Rejected"
                              ? "red"
                              : row.status === "Cancelled"
                                ? "muted"
                                : "amber"
                    }
                >
                    {row.status}
                </Badge>
            ),
        },
    ];

    if (kindsQuery.isPending) return <Spinner />;
    if (kinds.length === 0) return null;

    return (
        <section style={{ marginTop: "1.25rem" }}>
            <div
                style={{
                    display: "flex",
                    alignItems: "baseline",
                    justifyContent: "space-between",
                    gap: "0.75rem",
                }}
            >
                <h3 style={{ margin: 0 }}>All requests</h3>
                {/* Read-only here by design: the module shows the record, the
                    workflow lives on its own screen. */}
                <Link href="/dashboard/leave" style={{ fontSize: "0.85rem" }}>
                    Open Leave &amp; Applications â†’
                </Link>
            </div>

            {kinds.length > 1 && (
                <Tabs
                    tabs={["Staff leave", "Student leave"]}
                    active={active === "staff" ? "Staff leave" : "Student leave"}
                    onChange={(next) => setKind(next === "Staff leave" ? "staff" : "student")}
                />
            )}

            {rowsQuery.error !== null ? (
                <p style={{ color: "var(--danger, #b42318)" }}>
                    {errorMessage(rowsQuery.error, "The leave list could not be loaded.")}
                </p>
            ) : (
                <Table
                    columns={columns}
                    rows={rowsQuery.data ?? []}
                    rowKey={(row) => row.id}
                    empty={
                        active === "staff"
                            ? "No staff leave filed yet."
                            : "No student leave filed yet."
                    }
                />
            )}
        </section>
    );
}
