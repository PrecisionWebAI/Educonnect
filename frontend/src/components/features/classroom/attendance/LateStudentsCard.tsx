"use client";

import { Card, Spinner } from "@/components/ui";
import Icon from "@/components/ui/Icon";
import { pct, titleCase } from "@/lib/format";
import type { LateStudentRow, LateStudents } from "@/types";

// "Late students · last month" — a list, never a graph.
//
// The month is the last **complete** calendar month (in December it is November), because a
// share of a half-finished month swings wildly. The server does the arithmetic — open days
// from the school calendar, the threshold from `attendance.late_share_percent` — so this
// card only prints what it is given, and a name opens that child's register history.
//
// Three different silences, and the card is careful to say which one it is:
//   * loading → a spinner;
//   * no register at all last month → "no data", not "nobody was late";
//   * a register, nobody over the bar → "No late students last month".
export default function LateStudentsCard({
    data,
    loading,
    onOpen,
}: {
    data: LateStudents | undefined;
    loading: boolean;
    onOpen: (row: LateStudentRow) => void;
}) {
    // "Students late more than 10% of days · October 2026": the bar, a dot, the month.
    const title = data
        ? `Students late more than ${data.threshold}% of days · ${data.monthLabel}`
        : "Students late · last month";

    if (loading) {
        return (
            <Card title={title}>
                <Spinner size="sm" />
            </Card>
        );
    }

    if (!data || data.markedDays === 0) {
        return (
            <Card title={title}>
                <p style={{ color: "var(--muted)", fontSize: "0.88rem" }}>
                    No register was saved last month, so there is nothing to compare yet.
                </p>
            </Card>
        );
    }

    if (data.rows.length === 0) {
        return (
            <Card title={title}>
                <p style={{ color: "var(--muted)", fontSize: "0.88rem" }}>
                    No late students last month.
                </p>
            </Card>
        );
    }

    return (
        <Card title={title}>
            <p style={{ color: "var(--muted)", fontSize: "0.82rem", marginBottom: "0.5rem" }}>
                {data.openDays} open {data.openDays === 1 ? "day" : "days"} · {data.markedDays}{" "}
                {data.markedDays === 1 ? "register" : "registers"} taken · more than{" "}
                {data.threshold}% late
            </p>
            <ul className="feed">
                {data.rows.map((row) => (
                    <li key={row.studentId} className="feed-item">
                        <span className="feed-ico feed-ico-warn">
                            <Icon name="warning" size={16} />
                        </span>
                        <div className="feed-body">
                            <button
                                type="button"
                                className="feed-title feed-link"
                                onClick={() => onOpen(row)}
                            >
                                {titleCase(row.name)}
                            </button>
                            <span className="feed-sub">
                                {row.late} late {row.late === 1 ? "day" : "days"} ·{" "}
                                {pct(row.percent)}
                            </span>
                        </div>
                    </li>
                ))}
            </ul>
        </Card>
    );
}
