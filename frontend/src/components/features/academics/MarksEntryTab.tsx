"use client";

import type { MarksEntry } from "@/types";
import { Table, type Column } from "@/components/ui";
import { totalsFor } from "./useAcademics";

// Spreadsheet-style editable marks grid. Score cells update live.
export default function MarksEntryTab({
    entries,
    subjects,
    onScoreChange,
}: {
    entries: MarksEntry[];
    subjects: string[];
    onScoreChange: (studentId: number, subject: string, value: number) => void;
}) {
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
        ...subjects.map((subject) => ({
            key: subject,
            header: subject,
            render: (e: MarksEntry) => {
                const row = e.rows.find((r) => r.subject === subject);
                if (!row) return <span style={{ color: "var(--muted)" }}>—</span>;
                return (
                    <input
                        className="input marks-input"
                        type="number"
                        min={0}
                        max={row.max}
                        value={row.obtained}
                        aria-label={`${e.studentName} — ${subject}`}
                        onChange={(ev) => {
                            const v = Math.min(row.max, Math.max(0, Number(ev.target.value)));
                            onScoreChange(e.studentId, subject, Number.isNaN(v) ? 0 : v);
                        }}
                    />
                );
            },
        })),
        {
            key: "total",
            header: "Total %",
            align: "right",
            render: (e) => <strong>{totalsFor(e).percent}%</strong>,
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
