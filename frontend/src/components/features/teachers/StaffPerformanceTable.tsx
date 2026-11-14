"use client";
import { Table, Badge } from "@/components/ui";
import type { StaffPerfRows } from "./useStaff";

/**
 * Performance per person: the rating, the components behind the score, and the
 * score itself.
 *
 * Two rules the table follows, both from the API's own contract:
 *
 * * **"no data" is printed, not 0** - a component the school has nothing for is
 *   `null`, and a 0 would read as a failing teacher. The overall score is `null`
 *   too when nothing is known, so it prints "—" rather than an empty bar;
 * * **the bar is capped at 100** but the number beside it is the real value, the
 *   same rule the workload matrix follows for an overloaded teacher.
 */
export default function StaffPerformanceTable({
    rows,
    showSyllabus = true,
}: {
    rows: StaffPerfRows;
    /** Staff have no syllabus/periods facts (0.9); the column is hidden for them. */
    showSyllabus?: boolean;
}) {
    const trendTone: Record<string, "green" | "muted" | "amber"> = {
        up: "green",
        flat: "muted",
        down: "amber",
    };
    const columns = [
        { key: "staff", header: "Name" },
        {
            key: "rating",
            header: "Rating",
            render: (r: (typeof rows)[0]) =>
                r.reviews === 0 ? (
                    <span style={{ color: "var(--muted)" }}>no data</span>
                ) : (
                    <span>
                        {r.rating}{" "}
                        <span style={{ color: "var(--muted)", fontSize: "0.78rem" }}>/ 5</span>
                    </span>
                ),
        },
        { key: "reviews", header: "Reviews" },
        {
            key: "components",
            header: "Components",
            render: (r: (typeof rows)[0]) => {
                const shown = r.components.filter(
                    (item) => showSyllabus || item.key !== "syllabus",
                );
                return (
                    <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
                        {shown.map((item) => (
                            <span
                                key={item.key}
                                title={item.display}
                                style={{ color: "var(--muted)", fontSize: "0.78rem" }}
                            >
                                {item.label}:{" "}
                                {item.value === null ? "no data" : `${Math.round(item.value)}`}
                            </span>
                        ))}
                    </div>
                );
            },
        },
        {
            key: "score",
            header: "Score",
            render: (r: (typeof rows)[0]) =>
                r.score === null ? (
                    <span style={{ color: "var(--muted)" }}>no data</span>
                ) : (
                    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                        <div className="cls-bar" style={{ flex: 1, height: 8, maxWidth: 110 }}>
                            <div className="bar-fill" style={{ width: `${r.score}%` }} />
                        </div>
                        <span style={{ color: "var(--muted)", fontSize: "0.78rem" }}>
                            {r.score}
                        </span>
                    </div>
                ),
        },
        {
            key: "trend",
            header: "Trend",
            render: (r: (typeof rows)[0]) => <Badge tone={trendTone[r.trend]}>{r.trend}</Badge>,
        },
    ];

    return (
        <Table columns={columns} rows={rows} rowKey={(r) => r.id} empty="No performance records." />
    );
}
