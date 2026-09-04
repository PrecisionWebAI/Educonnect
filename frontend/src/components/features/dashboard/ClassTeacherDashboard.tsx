"use client";

import { useEffect, useState } from "react";
import {
    getMeetingReminders,
    getSubjectLeaves,
    getTodayClasses,
    getHomeworkStatus,
} from "@/services";
import type {
    HomeworkStatusItem,
    MeetingReminderItem,
    SubjectLeaveItem,
    TodayClassItem,
} from "@/types";
import { Badge, Button, Card, PageHeader, Spinner } from "@/components/ui";
import { useToast } from "@/components/ui/toast";

// Tab D.4 — Class Teacher Dashboard (blue)
export default function ClassTeacherDashboard() {
    const toast = useToast();
    const [classes, setClasses] = useState<TodayClassItem[]>([]);
    const [hw, setHw] = useState<HomeworkStatusItem[]>([]);
    const [leaves, setLeaves] = useState<SubjectLeaveItem[]>([]);
    const [meetings, setMeetings] = useState<MeetingReminderItem[]>([]);
    const [ready, setReady] = useState(false);

    useEffect(() => {
        void Promise.all([
            getTodayClasses(),
            getHomeworkStatus(),
            getSubjectLeaves(),
            getMeetingReminders(),
        ]).then(([c, h, l, m]) => {
            setClasses(c);
            setHw(h);
            setLeaves(l);
            setMeetings(m);
            setReady(true);
        });
    }, []);

    if (!ready) return <Spinner />;

    return (
        <div className="page">
            <PageHeader title="My Class Today" subtitle="Class 10-A" />

            <div className="dash-grid">
                <Card title="Running Classes" className="dash-span-2">
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

                <Card title="Homework Status">
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

                <Card title="Leave Apps of My Students" className="dash-span-2">
                    {leaves.length === 0 ? (
                        <p style={{ color: "var(--muted)" }}>No pending leave apps.</p>
                    ) : (
                        <ul className="feed">
                            {leaves.map((l) => (
                                <li key={l.id} className="feed-item">
                                    <Badge tone="amber">{l.type}</Badge>
                                    <div className="feed-body">
                                        <span className="feed-title">{l.student}</span>
                                        <span className="feed-sub">{l.range}</span>
                                    </div>
                                    <Button
                                        size="sm"
                                        variant="success"
                                        onClick={() => {
                                            setLeaves((x) => x.filter((y) => y.id !== l.id));
                                            toast.push("success", "Leave approved");
                                        }}
                                    >
                                        Approve
                                    </Button>
                                </li>
                            ))}
                        </ul>
                    )}
                </Card>

                <Card title="Parent Meeting Reminders">
                    <ul className="feed">
                        {meetings.map((m) => (
                            <li key={m.id} className="feed-item">
                                <div className="feed-body">
                                    <span className="feed-title">{m.parent}</span>
                                    <span className="feed-sub">{m.time}</span>
                                </div>
                            </li>
                        ))}
                    </ul>
                </Card>
            </div>
        </div>
    );
}
