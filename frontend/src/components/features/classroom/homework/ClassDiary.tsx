"use client";

import { Badge, Table } from "@/components/ui";
import type { DiaryEntry } from "@/types";

// The class diary (Phase 9): what was taught, in which subject, in which period.
//
// The old table had empty "Homework" and "Activity" columns (nothing ever wrote them).
// The line now names its **subject** and its **period**, which is what a reader - a
// parent, a substitute, the principal - actually looks for.

export default function ClassDiary({ rows }: { rows: DiaryEntry[] }) {
    const cols = [
        {
            key: "day",
            header: "Day",
            render: (r: DiaryEntry) => (
                <div className="flex items-center gap-2">
                    <Badge tone="accent">{r.day}</Badge>
                    <span className="text-muted-foreground text-xs">{r.date}</span>
                </div>
            ),
        },
        {
            key: "subject",
            header: "Subject",
            render: (r: DiaryEntry) => <span className="text-sm">{r.subject || "Whole day"}</span>,
        },
        {
            key: "period",
            header: "Period",
            render: (r: DiaryEntry) => (
                <span className="text-muted-foreground text-sm">{r.period || "—"}</span>
            ),
        },
        {
            key: "topic",
            header: "What was done",
            render: (r: DiaryEntry) => <span className="text-sm">{r.topic}</span>,
        },
    ];
    return <Table columns={cols} rows={rows} rowKey={(r) => r.id} empty="No diary entries." />;
}
