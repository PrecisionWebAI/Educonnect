"use client";

import { Badge, Button, Table } from "@/components/ui";
import type { Column } from "@/components/ui";
import { inr } from "@/lib/format";
import type { SalaryPaymentRow } from "@/types";
import { SALARY_STATUS_TONE } from "./useSalary";

// Monthly salary register with payout actions.

export default function SalaryRegisterTable({
    rows,
    onMarkPaid,
    onPayslip,
}: {
    rows: SalaryPaymentRow[];
    onMarkPaid: (row: SalaryPaymentRow) => void;
    onPayslip: (row: SalaryPaymentRow) => void;
}) {
    const columns: Column<SalaryPaymentRow>[] = [
        {
            key: "staffCode",
            header: "Staff ID",
            render: (r) => (
                <span className="text-muted-foreground text-xs">{r.staffCode}</span>
            ),
        },
        { key: "staffName", header: "Staff" },
        { key: "designation", header: "Designation" },
        { key: "department", header: "Department" },
        { key: "month", header: "Month" },
        { key: "gross", header: "Gross", align: "right", render: (r) => inr(r.gross) },
        { key: "deductions", header: "Deductions", align: "right", render: (r) => inr(r.deductions) },
        {
            key: "net",
            header: "Net Pay",
            align: "right",
            render: (r) => <b>{inr(r.net)}</b>,
        },
        {
            key: "status",
            header: "Status",
            render: (r) => <Badge tone={SALARY_STATUS_TONE[r.status]}>{r.status}</Badge>,
        },
        { key: "paidOn", header: "Paid On" },
        {
            key: "actions",
            header: "Actions",
            render: (r) => (
                <div className="flex flex-wrap items-center gap-2">
                    {r.status !== "Paid" && (
                        <Button variant="success" size="sm" onClick={() => onMarkPaid(r)}>
                            Mark Paid
                        </Button>
                    )}
                    <Button variant="ghost" size="sm" onClick={() => onPayslip(r)}>
                        Payslip
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
            empty="No salary rows match this filter."
        />
    );
}
