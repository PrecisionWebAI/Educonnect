"use client";
import { Table, type Column } from "@/components/ui";
import type { StaffPerfRows } from "./useStaff";

/**
 * Performance per person: attendance, workload and the chapter plan, over the
 * school's session (1 April -> 31 March).
 *
 * Three rules the table follows, all from the API's own contract:
 *
 * * **"no data" is printed, not 0** - a component the school has nothing for is
 *   `null`, and a 0 would read as a failing teacher. The overall score is `null`
 *   too when nothing is known, so it prints "no data" rather than an empty bar;
 * * **the tooltip carries the working** - `display` says "18 of 24 period(s) a
 *   week" or "6 of 10 chapter(s) (60%) Â· 50% on time Â· 2 day(s) late on average",
 *   so a percentage is never a number without its denominator;
 * * **staff have no workload or course column** (0.9): their job has neither a
 *   timetable nor a chapter plan, and an empty column would read as a failure.
 */
type Row = StaffPerfRows[number];

export default function StaffPerformanceTable({
    rows,
    showCourse = true,
}: {
    rows: StaffPerfRows;
    /** Staff have no timetable/plan facts (0.9); both columns are hidden for them. */
    showCourse?: boolean;
}) {
    /** The component behind a column, or `null` when this person has none. */
    const ingredient = (row: Row, key: string) =>
        row.components.find((item) => item.key === key) ?? null;

    const percent = (row: Row, key: string) => {
        const item = ingredient(row, key);
        if (!item || item.value === null) {
            return <span style={{ color: "var(--muted)" }}>no data</span>;
        }
        return (
            <span title={item.display}>
                {Math.round(item.value)}
                <span style={{ color: "var(--muted)", fontSize: "0.78rem" }}>%</span>
            </span>
        );
    };

    const columns: Column<Row>[] = [
        { key: "staff", header: "Name" },
        {
            key: "attendance",
            header: "Attendance",
            render: (row) => percent(row, "attendance"),
        },
    ];

    if (showCourse) {
        columns.push(
            {
                key: "workload",
                header: "Workload",
                render: (row) => percent(row, "workload"),
            },
            {
                key: "course",
                header: "Course",
                render: (row) => percent(row, "course"),
            },
        );
    }

    columns.push({
        key: "score",
        header: "Score",
        render: (row) =>
            row.score === null ? (
                <span style={{ color: "var(--muted)" }}>no data</span>
            ) : (
                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                    <div className="cls-bar" style={{ flex: 1, height: 8, maxWidth: 110 }}>
                        <div
                            className="bar-fill"
                            style={{ width: `${Math.min(100, row.score)}%` }}
                        />
                    </div>
                    <span style={{ color: "var(--muted)", fontSize: "0.78rem" }}>{row.score}</span>
                </div>
            ),
    });

    const session = rows[0]?.session ?? "";

    return (
        <>
            {session !== "" && (
                <p style={{ color: "var(--muted)", margin: "0 0 0.75rem" }}>
                    Session <b>{session}</b> Â· 1 April â€“ 31 March. Attendance weighs 40%,
                    workload 30% and course completion 30%; a component the school has nothing for
                    is left out rather than scored at zero.
                </p>
            )}
            <Table
                columns={columns}
                rows={rows}
                rowKey={(row) => row.id}
                empty="No performance records."
            />
        </>
    );
}
