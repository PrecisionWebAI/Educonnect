"use client";
import { Table } from "@/components/ui";
import { currency } from "./PayrollPage";
import type { SalaryStructureRow } from "@/types";

export default function SalaryStructureView({ structures }: { structures: SalaryStructureRow[] }) {
    const columns = [
        {
            key: "staffCode",
            header: "ID",
            render: (r: SalaryStructureRow) => (
                <span style={{ color: "var(--muted)", fontSize: "0.8rem" }}>{r.staffCode}</span>
            ),
        },
        { key: "name", header: "Name" },
        { key: "basic", header: "Basic", render: (r: SalaryStructureRow) => currency(r.basic) },
        { key: "hra", header: "HRA", render: (r: SalaryStructureRow) => currency(r.hra) },
        { key: "da", header: "DA", render: (r: SalaryStructureRow) => currency(r.da) },
        {
            key: "special",
            header: "Special",
            render: (r: SalaryStructureRow) => currency(r.special),
        },
        {
            key: "total",
            header: "Total",
            render: (r: SalaryStructureRow) => <b>{currency(r.total)}</b>,
        },
    ];
    return (
        <Table
            columns={columns}
            rows={structures}
            rowKey={(r) => r.id}
            empty="No salary structures yet."
        />
    );
}
