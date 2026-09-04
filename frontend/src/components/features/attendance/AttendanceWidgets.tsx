"use client";

import { Card } from "@/components/ui";
import type { Status } from "./useAttendance";

// Mini weekly trend bars (stitch right-column widget).
export function WeeklyTrendCard({ trend }: { trend: Record<string, number> }) {
    const entries = Object.entries(trend);
    const max = Math.max(100, ...entries.map(([, v]) => v));
    return (
        <Card title="Weekly Trend">
            <div className="bar-chart" style={{ height: 120 }}>
                {entries.map(([label, value]) => (
                    <div key={label} className="bar-col" title={`${label}: ${value}%`}>
                        <div className="bar-track">
                            <div className="bar" style={{ height: `${(value / max) * 100}%` }} />
                        </div>
                        <span className="bar-label">{label}</span>
                    </div>
                ))}
            </div>
        </Card>
    );
}

export function SummaryStrip({ counts }: { counts: Record<Status | "Unmarked", number> }) {
    const items = [
        { label: "Present", value: counts.Present, tone: "#5eead4" },
        { label: "Absent", value: counts.Absent, tone: "#fda4af" },
        { label: "Late", value: counts.Late, tone: "#fcd34d" },
        { label: "Leave", value: counts.Leave, tone: "#c4b5fd" },
        { label: "Unmarked", value: counts.Unmarked, tone: "#9aa3c7" },
    ];
    return (
        <div className="kpi-grid" style={{ marginBottom: "1rem" }}>
            {items.map((i) => (
                <div
                    key={i.label}
                    className="stat"
                    style={{ padding: "0.8rem", alignItems: "center" }}
                >
                    <span style={{ width: 9, height: 9, borderRadius: 99, background: i.tone }} />
                    <div>
                        <div className="stat-value" style={{ fontSize: "1.2rem" }}>
                            {i.value}
                        </div>
                        <div className="stat-label">{i.label}</div>
                    </div>
                </div>
            ))}
        </div>
    );
}
