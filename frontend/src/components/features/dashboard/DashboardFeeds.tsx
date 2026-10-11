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
                <ul className="mt-2 space-y-4">
                    {upcoming.map((u) => (
                        <li
                            key={u.title}
                            className="group flex items-start gap-4 rounded-lg border border-transparent p-3 transition-colors hover:border-[var(--border-subtle)] hover:bg-[var(--accent-surface)]"
                        >
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
                            <div className="flex flex-1 flex-col">
                                <span className="font-medium text-[var(--foreground)] transition-colors group-hover:text-[var(--primary)]">
                                    {u.title}
                                </span>
                                <span className="text-sm text-[var(--muted-foreground)]">
                                    {u.when}
                                </span>
                            </div>
                        </li>
                    ))}
                </ul>
            </Card>

            <Card title="Recent Marks" className="bento-span-2 bento-card glass-card">
                <ul className="mt-2 space-y-4">
                    {marks.slice(0, 3).map((m) => (
                        <li
                            key={m.studentId}
                            className="group flex items-start gap-4 rounded-lg border border-transparent p-3 transition-colors hover:border-[var(--border-subtle)] hover:bg-[var(--accent-surface)]"
                        >
                            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[var(--primary)]/10 font-bold text-[var(--primary)]">
                                {m.studentName[0]}
                            </span>
                            <div className="flex flex-1 flex-col overflow-hidden">
                                <span className="truncate font-medium text-[var(--foreground)]">
                                    {m.studentName}{" "}
                                    <span className="ml-1 font-normal text-[var(--muted-foreground)]">
                                        · {m.className}
                                    </span>
                                </span>
                                <span className="mt-1 truncate text-xs text-[var(--muted-foreground)]">
                                    {m.rows.map((r) => `${r.subject}: ${r.obtained}`).join(" · ")}
                                </span>
                            </div>
                        </li>
                    ))}
                </ul>
            </Card>

            <Card
                title="Notice Board"
                className="bento-span-2 lg:bento-span-4 bento-card glass-card"
            >
                <ul className="mt-2 grid grid-cols-1 gap-4 md:grid-cols-2">
                    {notices.map((n) => (
                        <li
                            key={n.title}
                            className="group flex flex-col rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-hover)]/50 p-4 transition-colors hover:bg-[var(--surface-hover)]"
                        >
                            <div className="mb-2 flex items-start justify-between">
                                <span className="font-semibold text-[var(--foreground)]">
                                    {n.title}
                                </span>
                                <span className="ml-2 text-xs whitespace-nowrap text-[var(--muted-foreground)]">
                                    {n.time}
                                </span>
                            </div>
                            <span className="line-clamp-2 text-sm text-[var(--muted-foreground)]">
                                {n.body}
                            </span>
                        </li>
                    ))}
                </ul>
            </Card>
        </>
    );
}
