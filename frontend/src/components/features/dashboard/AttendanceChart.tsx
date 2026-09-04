"use client";

import type { DashboardData } from "@/types";

type Point = DashboardData["attendanceTrend"][number];

// Pure-CSS weekly attendance bar chart.
export default function AttendanceChart({ trend }: { trend: Point[] }) {
    const max = Math.max(...trend.map((p) => p.value));
    return (
        <div className="bar-chart">
            {trend.map((p) => (
                <div key={p.label} className="bar-col" title={`${p.label}: ${p.value}%`}>
                    <div className="bar-track">
                        <div className="bar" style={{ height: `${(p.value / max) * 100}%` }} />
                    </div>
                    <span className="bar-label">{p.label}</span>
                </div>
            ))}
        </div>
    );
}
