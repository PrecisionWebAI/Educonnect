"use client";

import { Table } from "@/components/ui";
import type { Column } from "@/components/ui";
import { inr } from "@/lib/format";

// Department-wise salary rollup shown on the "Department Summary" tab.

export interface DepartmentSummaryRow {
    department: string;
    staff: number;
    gross: number;
    net: number;
}

export default function DepartmentSummaryTable({ rows }: { rows: DepartmentSummaryRow[] }) {
    const columns: Column<DepartmentSummaryRow>[] = [
        { key: "department", header: "Department" },
        { key: "staff", header: "Staff", render: (r) => String(r.staff) },
        { key: "gross", header: "Gross", align: "right", render: (r) => inr(r.gross) },
        {
            key: "net",
            header: "Net Payable",
            align: "right",
            render: (r) => <b>{inr(r.net)}</b>,
        },
    ];

    return (
        <Table
            columns={columns}
            rows={rows}
            rowKey={(r) => r.department}
            empty="No department salary data yet."
        />
    );
}
