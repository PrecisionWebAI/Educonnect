"use client";

import { Badge, Button, Table } from "@/components/ui";
import type { Column } from "@/components/ui";
import { inr } from "@/lib/format";
import type { FeeStructureRow } from "@/types";

// Fee-head master table (class-wise amounts + frequency).

export default function FeeStructureTable({
    rows,
    onEdit,
    onToggle,
}: {
    rows: FeeStructureRow[];
    onEdit: (row: FeeStructureRow) => void;
    onToggle: (row: FeeStructureRow) => void;
}) {
    const columns: Column<FeeStructureRow>[] = [
        { key: "head", header: "Fee Head" },
        { key: "className", header: "Applies To" },
        { key: "frequency", header: "Frequency" },
        {
            key: "amount",
            header: "Amount",
            align: "right",
            render: (r) => <b>{inr(r.amount)}</b>,
        },
        { key: "dueDay", header: "Due" },
        { key: "students", header: "Students", render: (r) => (r.students > 0 ? String(r.students) : "—") },
        {
            key: "status",
            header: "Status",
            render: (r) => <Badge tone={r.status === "Active" ? "green" : "amber"}>{r.status}</Badge>,
        },
        {
            key: "actions",
            header: "Actions",
            render: (r) => (
                <div className="flex flex-wrap items-center gap-2">
                    <Button variant="outline" size="sm" onClick={() => onEdit(r)}>
                        Edit
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => onToggle(r)}>
                        {r.status === "Active" ? "Unpublish" : "Publish"}
                    </Button>
                </div>
            ),
        },
    ];

    return (
        <Table
            columns={columns}
            rows={rows}
            rowKey={(r) => r.id}
            empty="No fee heads match this filter."
        />
    );
}
