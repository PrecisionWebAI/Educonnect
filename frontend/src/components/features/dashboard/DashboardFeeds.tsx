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
            <Card title="Upcoming events" className="dashboard-card xl:col-span-6">
                <ul className="mt-2 space-y-1">
                    {upcoming.map((u) => (
                        <li key={u.title} className="flex items-start gap-4 rounded-lg px-2 py-3">
                            <Badge
                                tone={
                                    u.type === "Exam"
                                        ? "amber"
                                        : u.type === "Meeting"
                                          ? "teal"
                                          : "green"
                                }
                                className="mt-1 w-20 justify-center"
                            >
                                {u.type}
                            </Badge>
                            <div className="flex flex-1 flex-col">
                                <span className="text-foreground font-medium">{u.title}</span>
                                <span className="text-sm text-[var(--muted-foreground)]">
                                    {u.when}
                                </span>
                            </div>
                        </li>
                    ))}
                </ul>
            </Card>

            <Card title="Recent marks" className="dashboard-card xl:col-span-6">
                <ul className="mt-2 space-y-1">
                    {marks.slice(0, 3).map((m) => (
                        <li
                            key={m.studentId}
                            className="flex items-start gap-4 rounded-lg px-2 py-3"
                        >
                            <span className="text-primary flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[var(--accent-surface)] font-bold">
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

            <Card title="Notice board" className="dashboard-card xl:col-span-12">
                <ul className="mt-2 grid grid-cols-1 gap-4 md:grid-cols-2">
                    {notices.map((n) => (
                        <li
                            key={n.title}
                            className="border-border bg-background flex flex-col rounded-lg border p-4"
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
