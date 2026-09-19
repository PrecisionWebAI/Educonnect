"use client";

import { useEffect, useState } from "react";
import { getHomeworkStatus, getTodayClasses } from "@/services";
import type { HomeworkStatusItem, TodayClassItem } from "@/types";
import { Badge, Card, PageHeader, Spinner } from "@/components/ui";

// Tab D.5 — Subject Teacher Dashboard (purple)
export default function SubjectTeacherDashboard() {
    const [classes, setClasses] = useState<TodayClassItem[]>([]);
    const [hw, setHw] = useState<HomeworkStatusItem[]>([]);
    const [ready, setReady] = useState(false);

    useEffect(() => {
        void Promise.all([getTodayClasses(), getHomeworkStatus()]).then(([c, h]) => {
            setClasses(c);
            setHw(h);
            setReady(true);
        });
    }, []);

    if (!ready) return <Spinner />;

    return (
        <div className="page">
            <PageHeader title="My Classes Today" subtitle="Subject teacher" />

            <div className="dash-grid">
                <Card title="My Classes Today" className="dash-span-2">
                    <ul className="feed">
                        {classes.map((c) => (
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

                <Card title="HW / Assignment Status" className="dash-span-2">
                    <ul className="feed">
                        {hw.map((h) => (
                            <li key={h.subject} className="feed-item">
                                <Badge tone={h.assigned - h.submitted > 3 ? "red" : "green"}>
                                    {h.submitted}/{h.assigned}
                                </Badge>
                                <div className="feed-body">
                                    <span className="feed-title">{h.subject}</span>
                                    <span className="feed-sub">{h.className}</span>
                                </div>
                            </li>
                        ))}
                    </ul>
                </Card>

            </div>
        </div>
    );
}
