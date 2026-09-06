"use client";
import { Table, Badge, type BadgeTone } from "@/components/ui";
import type { StaffLeaveRows } from "./useStaff";

export default function StaffLeaveTable({ rows }: { rows: StaffLeaveRows }) {
    const tone: Record<StaffLeaveRows[number]["status"], BadgeTone> = {
        Approved: "green",
        Pending: "amber",
        Rejected: "red",
    };
    const columns = [
        { key: "staff", header: "Teacher" },
        { key: "from", header: "From" },
        { key: "to", header: "To" },
        { key: "reason", header: "Reason" },
        { key: "substitute", header: "Substitute" },
        {
            key: "status",
            header: "Status",
            render: (r: (typeof rows)[0]) => <Badge tone={tone[r.status]}>{r.status}</Badge>,
        },
    ];

    return (
        <Table columns={columns} rows={rows} rowKey={(r) => r.id} empty="No leave applications." />
    );
}
