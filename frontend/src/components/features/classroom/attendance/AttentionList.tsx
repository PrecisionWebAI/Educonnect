"use client";

import Link from "next/link";
import { Card } from "@/components/ui";
import Icon from "@/components/ui/Icon";
import type { AttendanceAttentionRow } from "@/types";

// "Attention Required" — the children the office should ring.
//
// Phase 4: the list is `GET /attendance/section/{id}/attention`, i.e. below the
// school's own attendance threshold or absent several open days in a row. Each row
// deep-links to that child in the directory, so the next step (call the family) starts
// from the person and not from a name somebody has to search again.
export default function AttentionList({ rows }: { rows: AttendanceAttentionRow[] }) {
    return (
        <Card title="Attention Required">
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
                                <Link
                                    href={`/dashboard/students?student=${row.studentId}`}
                                    className="feed-title"
                                >
                                    {row.name}
                                </Link>
                                <span className="feed-sub">{row.reason}</span>
                            </div>
                        </li>
                    ))}
                </ul>
            )}
        </Card>
    );
}
