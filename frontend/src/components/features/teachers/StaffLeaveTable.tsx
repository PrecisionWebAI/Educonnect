"use client";
import { Table, Badge, type BadgeTone } from "@/components/ui";
import type { StaffLeaveRows } from "./useStaff";

/**
 * Staff leave requests.
 *
 * Substitution and leave balance are **not** tracked yet, so the API sends
 * `null` and this table prints "—". An empty cell there used to look like a
 * rendering bug, and a `0` would have looked like "no days left".
 */
export default function StaffLeaveTable({ rows }: { rows: StaffLeaveRows }) {
    const tone: Record<StaffLeaveRows[number]["status"], BadgeTone> = {
        Approved: "green",
        Pending: "amber",
        Rejected: "red",
    };
    const columns = [
        {
            key: "staffName",
            header: "Teacher",
            render: (r: StaffLeaveRows[number]) => (
                <div style={{ lineHeight: 1.2 }}>
                    <div>{r.staffName || "—"}</div>
                    <div style={{ color: "var(--muted)", fontSize: "0.74rem" }}>
                        {r.staffCode || r.role}
                    </div>
                </div>
            ),
        },
        { key: "role", header: "Role" },
        { key: "leaveType", header: "Leave type" },
        {
            key: "range",
            header: "Dates",
            render: (r: StaffLeaveRows[number]) => `${r.fromDate} → ${r.toDate}`,
        },
        { key: "days", header: "Days" },
        { key: "reason", header: "Reason" },
        {
            key: "substitute",
            header: "Substitute",
            render: (r: StaffLeaveRows[number]) => r.substitute ?? "—",
        },
        {
            key: "balance",
            header: "Balance",
            render: (r: StaffLeaveRows[number]) => r.balance ?? "—",
        },
        {
            key: "status",
            header: "Status",
            render: (r: StaffLeaveRows[number]) => (
                <Badge tone={tone[r.status] ?? "muted"}>{r.status}</Badge>
            ),
        },
    ];

    return (
        <Table columns={columns} rows={rows} rowKey={(r) => r.id} empty="No leave applications." />
    );
}
