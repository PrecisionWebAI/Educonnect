"use client";

import type { MarksEntry } from "@/types";
import { Badge, Table, type Column } from "@/components/ui";
import { gradeFor, totalsFor } from "./useAcademics";

// Read-only gradebook: totals + auto grade per student.
export default function GradebookTab({ entries }: { entries: MarksEntry[] }) {
    const columns: Column<MarksEntry>[] = [
        {
            key: "studentName",
            header: "Student",
            render: (e) => (
                <span>
                    <strong>{e.studentName}</strong>
                    <br />
                    <span style={{ color: "var(--muted)", fontSize: "0.78rem" }}>
                        {e.className} · {e.exam}
                    </span>
                </span>
            ),
        },
        ...Object.keys(
            entries.reduce<Record<string, true>>((acc, e) => {
                e.rows.forEach((r) => {
                    acc[r.subject] = true;
                });
                return acc;
            }, {}),
        ).map((subject) => ({
            key: subject,
            header: subject,
            render: (e: MarksEntry) => {
                const row = e.rows.find((r) => r.subject === subject);
                if (!row) return <span style={{ color: "var(--muted)" }}>—</span>;
                const pct = row.max > 0 ? Math.round((row.obtained / row.max) * 100) : 0;
                return (
                    <span>
                        {row.obtained}/{row.max}{" "}
                        <small style={{ color: "var(--muted)" }}>({pct}%)</small>
                    </span>
                );
            },
        })),
        {
            key: "percent",
            header: "Total",
            align: "right",
            render: (e) => {
                const t = totalsFor(e);
                return <strong>{t.percent}%</strong>;
            },
        },
        {
            key: "grade",
            header: "Grade",
            align: "right",
            render: (e) => {
                const g = gradeFor(totalsFor(e).percent);
                return <Badge tone={g.tone}>{g.label}</Badge>;
            },
        },
    ];

    return (
        <Table
            columns={columns}
            rows={entries}
            rowKey={(e) => e.studentId}
            empty="No marks records yet."
        />
    );
}
