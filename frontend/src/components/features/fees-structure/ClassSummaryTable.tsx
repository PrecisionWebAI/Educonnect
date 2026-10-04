"use client";

import { Table } from "@/components/ui";
import type { Column } from "@/components/ui";
import { inr } from "@/lib/format";

// Class-wise fee rollup shown on the "Class Summary" tab.

export interface ClassSummaryRow {
    className: string;
    heads: number;
    students: number;
    value: number;
}

export default function ClassSummaryTable({ rows }: { rows: ClassSummaryRow[] }) {
    const columns: Column<ClassSummaryRow>[] = [
        { key: "className", header: "Class" },
        { key: "heads", header: "Fee Heads", render: (r) => String(r.heads) },
        { key: "students", header: "Students Covered", render: (r) => String(r.students) },
        {
            key: "value",
            header: "Estimated Value",
            align: "right",
            render: (r) => <b>{inr(r.value)}</b>,
        },
    ];

    return (
        <Table
            columns={columns}
            rows={rows}
            rowKey={(r) => r.className}
            empty="No classes configured yet."
        />
    );
}
