"use client";

import type { DashboardData, MarksEntry } from "@/types";
import { Badge, Card } from "@/components/ui";

// Right-side dashboard feed cards: upcoming, recent marks, notices.
export default function DashboardFeeds({
    upcoming,
    marks,
    notices,
}: {
    upcoming: DashboardData["upcoming"];
    marks: MarksEntry[];
    notices: DashboardData["notices"];
}) {
    return (
        <>
            <Card title="Upcoming Events" className="bento-span-2 bento-card glass-card">
                <ul className="space-y-4 mt-2">
                    {upcoming.map((u) => (
                        <li key={u.title} className="group flex items-start gap-4 p-3 rounded-lg hover:bg-[var(--accent-surface)] transition-colors border border-transparent hover:border-[var(--border-subtle)]">
                            <Badge
                                tone={
                                    u.type === "Exam"
                                        ? "violet"
                                        : u.type === "Meeting"
                                          ? "teal"
                                          : "amber"
                                }
                                className="mt-1 w-20 justify-center"
                            >
                                {u.type}
                            </Badge>
                            <div className="flex flex-col flex-1">
                                <span className="font-medium text-[var(--foreground)] group-hover:text-[var(--primary)] transition-colors">{u.title}</span>
                                <span className="text-sm text-[var(--muted-foreground)]">{u.when}</span>
                            </div>
                        </li>
                    ))}
                </ul>
            </Card>

            <Card title="Recent Marks" className="bento-span-2 bento-card glass-card">
                <ul className="space-y-4 mt-2">
                    {marks.slice(0, 3).map((m) => (
                        <li key={m.studentId} className="group flex items-start gap-4 p-3 rounded-lg hover:bg-[var(--accent-surface)] transition-colors border border-transparent hover:border-[var(--border-subtle)]">
                            <span className="flex items-center justify-center w-10 h-10 rounded-full bg-[var(--primary)]/10 text-[var(--primary)] font-bold shrink-0">
                                {m.studentName[0]}
                            </span>
                            <div className="flex flex-col flex-1 overflow-hidden">
                                <span className="font-medium truncate text-[var(--foreground)]">{m.studentName} <span className="text-[var(--muted-foreground)] font-normal ml-1">· {m.className}</span></span>
                                <span className="text-xs text-[var(--muted-foreground)] truncate mt-1">
                                    {m.rows.map((r) => `${r.subject}: ${r.obtained}`).join(" · ")}
                                </span>
                            </div>
                        </li>
                    ))}
                </ul>
            </Card>

            <Card title="Notice Board" className="bento-span-2 lg:bento-span-4 bento-card glass-card">
                <ul className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-2">
                    {notices.map((n) => (
                        <li key={n.title} className="group flex flex-col p-4 rounded-lg bg-[var(--surface-hover)]/50 hover:bg-[var(--surface-hover)] transition-colors border border-[var(--border-subtle)]">
                            <div className="flex justify-between items-start mb-2">
                                <span className="font-semibold text-[var(--foreground)]">{n.title}</span>
                                <span className="text-xs text-[var(--muted-foreground)] whitespace-nowrap ml-2">{n.time}</span>
                            </div>
                            <span className="text-sm text-[var(--muted-foreground)] line-clamp-2">{n.body}</span>
                        </li>
                    ))}
                </ul>
            </Card>
        </>
    );
}
