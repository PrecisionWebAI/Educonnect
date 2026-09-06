"use client";
import { Table, Badge, type BadgeTone } from "@/components/ui";
import type { SubmissionItem } from "@/types";

export default function SubmissionsReview({ rows }: { rows: SubmissionItem[] }) {
    const tone: Record<SubmissionItem["status"], BadgeTone> = {
        Submitted: "green",
        Pending: "amber",
        Late: "red",
    };
    const cols = [
        { key: "homeworkTitle", header: "Homework" },
        { key: "student", header: "Student" },
        { key: "submittedAt", header: "Submitted" },
        {
            key: "status",
            header: "Status",
            render: (r: SubmissionItem) => <Badge tone={tone[r.status]}>{r.status}</Badge>,
        },
    ];
    return <Table columns={cols} rows={rows} rowKey={(r) => r.id} empty="No submissions." />;
}
