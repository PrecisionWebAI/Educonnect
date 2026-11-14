"use client";
import { Badge, Table, type BadgeTone } from "@/components/ui";
import type { WorkloadMatrixRows } from "./useStaff";

/**
 * Each teacher's periods against the week the school calls full.
 *
 * `capacity` is the school's rule (`staffworkloadrule`) when it has stated one,
 * the timetable's own slot count otherwise - and `weekSlots` is always that slot
 * count, so the two numbers sit side by side and nobody has to trust a silent
 * choice. `utilisation` is capped at 100 (a bar cannot overflow its track), which
 * is why "over the line" is carried by `band` instead.
 */
const BAND_TONE: Record<WorkloadMatrixRows[number]["band"], BadgeTone> = {
    Overloaded: "red",
    Steady: "green",
    Light: "muted",
    // Amber, not grey: nothing in the timetable yet is a task, not a light load.
    Unassigned: "amber",
};

export default function WorkloadMatrixTable({
    rows,
    onRowClick,
}: {
    rows: WorkloadMatrixRows;
    /** Opens the week sheet for that person - the row is the control. */
    onRowClick?: (row: WorkloadMatrixRows[number]) => void;
}) {
    /**
     * A → Z by teacher, and it is done **here** rather than trusted from the API.
     *
     * The matrix is a list of people, and a list of people reads alphabetically;
     * relying on the server's order would make the screen depend on a query
     * detail (a `COUNT` subquery's ordering) that nobody promised. Sorting a copy
     * keeps the prop immutable, which is what React needs.
     */
    const sorted = [...rows].sort((first, second) =>
        (first.staff || "").localeCompare(second.staff || ""),
    );

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
        { key: "periods", header: "Periods / Wk" },
        {
            key: "capacity",
            header: "Capacity",
            // `0` means "nothing is scheduled yet", so the cell says so rather
            // than printing a denominator nobody can divide by.
            render: (r: WorkloadMatrixRows[number]) => (r.capacity > 0 ? r.capacity : "—"),
        },
        {
            key: "weekSlots",
            header: "Week Slots",
            render: (r: WorkloadMatrixRows[number]) => (r.weekSlots > 0 ? r.weekSlots : "—"),
        },
        {
            key: "duties",
            header: "Duties",
            render: (r: WorkloadMatrixRows[number]) => (r.duties > 0 ? r.duties : "—"),
        },
        {
            key: "band",
            header: "Load",
            render: (r: WorkloadMatrixRows[number]) => (
                <Badge tone={BAND_TONE[r.band] ?? "muted"}>{r.band}</Badge>
            ),
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
            rows={sorted}
            rowKey={(r) => r.id}
            onRowClick={onRowClick}
            empty="No workload data yet."
        />
    );
}
