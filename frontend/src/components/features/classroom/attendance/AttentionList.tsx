"use client";

import { Card } from "@/components/ui";
import Icon from "@/components/ui/Icon";
import { titleCase } from "@/lib/format";
import type { AttendanceAttentionRow } from "@/types";

// "Attention Required" — the children the office should ring.
//
// The list is `GET /attendance/section/{id}/attention`: below the school's own threshold
// (the heading says which), or absent several open days in a row. A row opens that child's
// register history, so the next step - calling the family - starts from the dates and not
// from a percentage somebody has to interpret. Names print in Title Case because the
// database stores canonical lower-case text.
export default function AttentionList({
    rows,
    threshold,
    onOpen,
}: {
    rows: AttendanceAttentionRow[];
    /** The school's `attendance.absence_threshold` - the heading names it. */
    threshold: number;
    onOpen: (row: AttendanceAttentionRow) => void;
}) {
    return (
        <Card title={`Attention Required · below ${threshold}%`}>
            {rows.length === 0 ? (
                <p style={{ color: "var(--muted)", fontSize: "0.88rem" }}>
                    Nobody is below the mark — nothing to follow up.
                </p>
            ) : (
                <ul className="feed">
                    {rows.map((row) => (
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
                                <span className="feed-sub">{row.reason}</span>
                            </div>
                        </li>
                    ))}
                </ul>
            )}
        </Card>
    );
}
