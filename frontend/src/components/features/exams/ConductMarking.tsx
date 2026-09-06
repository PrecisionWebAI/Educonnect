"use client";
import { Table, Badge } from "@/components/ui";
import type { ExamMarkingRow } from "@/types";

export default function ConductMarking({ rows }: { rows: ExamMarkingRow[] }) {
    const cols = [
        { key: "student", header: "Student" },
        { key: "subject", header: "Subject" },
        { key: "max", header: "Max" },
        { key: "obtained", header: "Obtained", render: (r: ExamMarkingRow) => <b>{r.obtained}</b> },
        {
            key: "status",
            header: "Status",
            render: (r: ExamMarkingRow) => (
                <Badge tone={r.status === "Entered" ? "green" : "amber"}>{r.status}</Badge>
            ),
        },
    ];
    return <Table columns={cols} rows={rows} rowKey={(r) => r.id} empty="No marking entries." />;
}
