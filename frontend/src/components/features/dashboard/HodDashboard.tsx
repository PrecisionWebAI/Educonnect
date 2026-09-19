"use client";

import { useEffect, useState } from "react";
import { getSubjectPerf } from "@/services";
import type { SubjectPerf } from "@/types";
import { Badge, Card, PageHeader, Spinner } from "@/components/ui";

// Tab D.3 — HOD Academic Dashboard (purple)
export default function HodDashboard() {
    const [perf, setPerf] = useState<SubjectPerf[]>([]);
    const [ready, setReady] = useState(false);

    useEffect(() => {
        void getSubjectPerf().then((p) => {
            setPerf(p);
            setReady(true);
        });
    }, []);

    if (!ready) return <Spinner />;

    return (
        <div className="page">
            <PageHeader title="Academic HOD Overview" subtitle="Science department" />

            <div className="dash-grid">
                <Card title="Subject Performance" className="dash-span-2">
                    <div className="feed">
                        {perf.map((p) => (
                            <li key={p.subject + p.className} className="feed-item">
                                <div className="feed-body">
                                    <span className="feed-title">
                                        {p.subject} · {p.className}
                                    </span>
                                    <span className="feed-sub">
                                        Avg {p.average}% — weak topic: {p.weakTopic}
                                    </span>
                                </div>
                                <Badge
                                    tone={
                                        p.average >= 85
                                            ? "green"
                                            : p.average >= 75
                                              ? "teal"
                                              : "amber"
                                    }
                                >
                                    {p.average}%
                                </Badge>
                            </li>
                        ))}
                    </div>
                </Card>

            </div>
        </div>
    );
}
