"use client";
import { Table, Badge } from "@/components/ui";
import type { FeeInvoice } from "@/types";

export function inr(n: number) {
    return "₹" + n.toLocaleString("en-IN");
}

export function feeStatusTone(s: FeeInvoice["status"]): "green" | "amber" | "red" {
    return s === "Paid" ? "green" : s === "Partial" ? "amber" : "red";
}

export const FEE_COLUMNS = [
    { key: "student", header: "Student" },
    { key: "className", header: "Class" },
    { key: "head", header: "Fee Head" },
    { key: "amount", header: "Amount", render: (r: FeeInvoice) => inr(r.amount) },
    { key: "paid", header: "Paid", render: (r: FeeInvoice) => inr(r.paid) },
    {
        key: "due",
        header: "Due",
        render: (r: FeeInvoice) => (
            <b style={{ color: r.due > 0 ? "#fda4af" : "var(--text)" }}>{inr(r.due)}</b>
        ),
    },
    {
        key: "status",
        header: "Status",
        render: (r: FeeInvoice) => <Badge tone={feeStatusTone(r.status)}>{r.status}</Badge>,
    },
];

export default function FeeInvoicesTable({ rows }: { rows: FeeInvoice[] }) {
    return (
        <Table
            columns={FEE_COLUMNS}
            rows={rows}
            rowKey={(r) => r.id}
            empty="No fee invoices found."
        />
    );
}
