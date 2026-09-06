"use client";
import { Badge } from "@/components/ui";
import { currency } from "./PayrollPage";
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
                <div key={e.id} className="card">
                    <div className="card-head">
                        <h3>{e.name}</h3>
                        <Badge tone={statusTone(e.status)}>{e.status}</Badge>
                    </div>
                    <div
                        className="card-body"
                        style={{ display: "grid", gap: "0.4rem", fontSize: "0.88rem" }}
                    >
                        <div style={{ display: "flex", justifyContent: "space-between" }}>
                            <span style={{ color: "var(--muted)" }}>ID</span>
                            {e.staffCode}
                        </div>
                        <div style={{ display: "flex", justifyContent: "space-between" }}>
                            <span style={{ color: "var(--muted)" }}>Basic</span>
                            {currency(e.basic)}
                        </div>
                        <div style={{ display: "flex", justifyContent: "space-between" }}>
                            <span style={{ color: "var(--muted)" }}>Allowances</span>
                            {currency(e.allowances)}
                        </div>
                        <div style={{ display: "flex", justifyContent: "space-between" }}>
                            <span style={{ color: "var(--muted)" }}>Deductions</span>-
                            {currency(e.deductions)}
                        </div>
                        <div
                            style={{
                                display: "flex",
                                justifyContent: "space-between",
                                marginTop: "0.4rem",
                                borderTop: "1px solid var(--border)",
                                paddingTop: "0.4rem",
                            }}
                        >
                            <b>Net Pay</b>
                            <b>{currency(e.net)}</b>
                        </div>
                    </div>
                </div>
            ))}
        </div>
    );
}
