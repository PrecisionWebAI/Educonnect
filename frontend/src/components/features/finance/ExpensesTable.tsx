"use client";
import { Table, Badge } from "@/components/ui";
import { inr } from "./FeeInvoicesTable";
import type { ExpenseItem } from "@/types";

export default function ExpensesTable({ rows }: { rows: ExpenseItem[] }) {
    const columns = [
        { key: "vendor", header: "Vendor" },
        { key: "head", header: "Expense Head" },
        { key: "amount", header: "Amount", render: (r: ExpenseItem) => inr(r.amount) },
        { key: "date", header: "Date" },
        {
            key: "status",
            header: "Status",
            render: (r: ExpenseItem) => (
                <Badge tone={r.status === "Approved" ? "green" : "amber"}>{r.status}</Badge>
            ),
        },
    ];
    return (
        <Table columns={columns} rows={rows} rowKey={(r) => r.id} empty="No expenses recorded." />
    );
}
