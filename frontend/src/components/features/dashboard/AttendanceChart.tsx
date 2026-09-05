"use client";

import type { DashboardData } from "@/types";
import { BarChart } from "@/components/tremor/BarChart";

type Point = DashboardData["attendanceTrend"][number];

export default function AttendanceChart({ trend }: { trend: Point[] }) {
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
