"use client";

import { useEffect, useState } from "react";
import { getParentData, getStudentPortal } from "@/services";
import type { ChildSummary, StudentPortalData } from "@/types";
import { Badge, Card, PageHeader, Select, Spinner } from "@/components/ui";
import Icon from "@/components/ui/Icon";

// Tab D.7 — Parent Dashboard (stitch: parent_portal_dark_mode), child switcher.
export default function ParentDashboard() {
    const [children, setChildren] = useState<ChildSummary[]>([]);
    const [activeId, setActiveId] = useState(0);
    const [detail, setDetail] = useState<StudentPortalData | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        void getParentData().then((c) => {
            setChildren(c);
            if (c.length > 0) setActiveId(c[0].id);
        });
    }, []);

    useEffect(() => {
        if (!activeId) return;
        void getStudentPortal().then((d) => {
            setDetail(d);
            setLoading(false);
        });
    }, [activeId]);

    if (loading) return <Spinner />;
    const child = children.find((c) => c.id === activeId);

    return (
        <div className="page">
            <PageHeader
                title="Child Dashboard"
                subtitle="Parent — per-child view"
                actions={
                    children.length > 1 && (
                        <Select
                            value={activeId}
                            onChange={(e) => {
                                setActiveId(Number(e.target.value));
                                setLoading(true);
                            }}
                            aria-label="Select child"
                        >
                            {children.map((c) => (
                                <option key={c.id} value={c.id}>
                                    {c.name} · {c.className}-{c.section}
                                </option>
                            ))}
                        </Select>
                    )
                }
            />

            {child && (
                <>
                    {/* child summary */}
                    <div className="kpi-grid" style={{ marginBottom: "1rem" }}>
                        {[
                            {
                                icon: "attendance" as const,
                                label: "Attendance",
                                value: `${child.attendancePct}%`,
                            },
                            {
                                icon: "trending" as const,
                                label: "Avg Marks",
                                value: `${child.avgMarks}%`,
                            },
                            { icon: "wallet" as const, label: "Fees", value: child.feeStatus },
                            {
                                icon: "book" as const,
                                label: "Pending HW",
                                value: String(child.pendingHw),
                            },
                        ].map((p) => (
                            <Card key={p.label} className="relative">
                                <div className="flex items-center justify-between">
                                    <span className="text-sm font-medium text-muted-foreground">{p.label}</span>
                                    <Icon name={p.icon} size={22} className="text-muted-foreground" />
                                </div>
                                <div className="mt-4 flex items-baseline gap-2">
                                    <span className="text-3xl font-bold">{p.value}</span>
                                </div>
                            </Card>
                        ))}
                    </div>

                    {/* performance + schedule */}
                    {detail && (
                        <div className="dash-grid">
                            <Card title={`Recent Grades — ${child.name}`} className="dash-span-2">
                                <div className="feed">
                                    {detail.recentGrades.map((g) => (
                                        <li key={g.subject} className="feed-item">
                                            <div className="feed-body">
                                                <span className="feed-title">{g.subject}</span>
                                                <span className="feed-sub">
                                                    Score: {g.score}/{g.max}
                                                </span>
                                            </div>
                                        </li>
                                    ))}
                                </div>
                            </Card>

                            <Card title="Homework to track">
                                <ul className="feed">
                                    {detail.homework
                                        .filter((h) => !h.done)
                                        .map((h) => (
                                            <li key={h.id} className="feed-item">
                                                <Badge tone={h.due === "Today" ? "red" : "amber"}>
                                                    {h.due}
                                                </Badge>
                                                <div className="feed-body">
                                                    <span className="feed-title">{h.title}</span>
                                                    <span className="feed-sub">{h.subject}</span>
                                                </div>
                                            </li>
                                        ))}
                                </ul>
                            </Card>

                            <Card title="Today's Schedule" className="dash-col-2">
                                <ul className="feed">
                                    {detail.todaySchedule.map((c) => (
                                        <li key={c.id} className="feed-item">
                                            <span className="feed-avatar">{c.period}</span>
                                            <div className="feed-body">
                                                <span className="feed-title">{c.subject}</span>
                                                <span className="feed-sub">
                                                    {c.className} · {c.room}
                                                </span>
                                            </div>
                                        </li>
                                    ))}
                                </ul>
                            </Card>
                        </div>
                    )}
                </>
            )}
        </div>
    );
}
