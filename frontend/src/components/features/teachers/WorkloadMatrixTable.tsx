"use client";
import { Table } from "@/components/ui";
import type { WorkloadMatrixRows } from "./useStaff";

/**
 * Each teacher's periods against the week the timetable actually runs.
 *
 * `capacity` comes from the timetable's own slot count, so the bar means
 * something: 18 periods out of 24 is 75%, while the old screen printed a
 * percentage of a hard-coded 22 nobody had checked.
 */
export default function WorkloadMatrixTable({ rows }: { rows: WorkloadMatrixRows }) {
    const columns = [
        { key: "staff", header: "Teacher" },
        {
            key: "subject",
            header: "Subject",
            render: (r: WorkloadMatrixRows[number]) => r.subject || "—",
        },
        {
            key: "classes",
            header: "Classes",
            render: (r: WorkloadMatrixRows[number]) => r.classes.join(", ") || "—",
        },
        { key: "periods", header: "Periods / wk" },
        {
            key: "capacity",
            header: "Week slots",
            render: (r: WorkloadMatrixRows[number]) => r.capacity,
        },
        {
            key: "utilisation",
            header: "Utilisation",
            render: (r: WorkloadMatrixRows[number]) => (
                <div
                    style={{ display: "flex", alignItems: "center", gap: "0.5rem", minWidth: 120 }}
                >
                    <div className="cls-bar" style={{ flex: 1, height: 8, maxWidth: 110 }}>
                        <div className="bar-fill" style={{ width: `${r.utilisation}%` }} />
                    </div>
                    <span style={{ color: "var(--muted)", fontSize: "0.78rem" }}>
                        {r.utilisation}%
                    </span>
                </div>
            ),
        },
    ];

    return (
        <Table
            columns={columns}
            // The employee id, not the name: two teachers can share a name.
            rows={rows}
            rowKey={(r) => r.id}
            empty="No workload data yet."
        />
    );
}
