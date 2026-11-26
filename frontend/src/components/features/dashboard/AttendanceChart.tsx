"use client";

import type { DashboardData } from "@/types";
import { BarChart } from "@/components/tremor/BarChart";

type Point = DashboardData["attendanceTrend"][number];

export default function AttendanceChart({ trend }: { trend: Point[] }) {
    if (trend.length === 0) {
        return (
            <p className="text-muted-foreground flex h-48 items-center justify-center text-sm">
                No attendance has been marked yet.
            </p>
        );
    }
    return (
        <BarChart
            data={trend}
            index="label"
            categories={["value"]}
            colors={["var(--chart-1)"]}
            valueFormatter={(val) => `${val}%`}
            yAxisWidth={48}
            className="h-48"
            showLegend={false}
        />
    );
}
