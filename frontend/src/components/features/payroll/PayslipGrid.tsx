"use client";
import { Badge, Card } from "@/components/ui";
import { inr } from "@/lib/format";
import type { PayrollEntry } from "@/types";

export default function PayslipGrid({
    entries,
    statusTone,
}: {
    entries: PayrollEntry[];
    statusTone: (s: string) => "amber" | "accent" | "green" | "muted";
}) {
    if (entries.length === 0) {
        return <p style={{ color: "var(--muted)" }}>No payslips generated yet.</p>;
    }
    return (
        <div
            style={{
                display: "grid",
                gap: "1rem",
                gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))",
            }}
        >
            {entries.map((e) => (
                <Card key={e.id} className="p-0">
                    <div className="border-border-subtle flex items-center justify-between gap-3 border-b px-4 py-3">
                        <h3 className="font-semibold">{e.name}</h3>
                        <Badge tone={statusTone(e.status)}>{e.status}</Badge>
                    </div>
                    <div className="grid gap-2 p-4 text-sm">
                        <div className="flex justify-between">
                            <span className="text-muted-foreground">ID</span>
                            {e.staffCode}
                        </div>
                        <div className="flex justify-between">
                            <span className="text-muted-foreground">Basic</span>
                            {inr(e.basic)}
                        </div>
                        <div className="flex justify-between">
                            <span className="text-muted-foreground">Allowances</span>
                            {inr(e.allowances)}
                        </div>
                        <div className="flex justify-between">
                            <span className="text-muted-foreground">Deductions</span>
                            <span>-{inr(e.deductions)}</span>
                        </div>
                        <div className="border-border mt-1 flex justify-between border-t pt-3">
                            <b>Net Pay</b>
                            <b>{inr(e.net)}</b>
                        </div>
                    </div>
                </Card>
            ))}
        </div>
    );
}
