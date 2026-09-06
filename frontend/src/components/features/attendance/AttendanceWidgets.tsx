"use client";

import { Card } from "@/components/ui";
import type { Status } from "./useAttendance";
import { cn } from "cn";

import { BarChart } from "@/components/tremor/BarChart";

// Mini weekly trend bars (stitch right-column widget).
export function WeeklyTrendCard({ trend }: { trend: Record<string, number> }) {
    const data = Object.entries(trend).map(([label, value]) => ({ label, value }));
    return (
        <Card title="Weekly Trend">
            <BarChart
                data={data}
                index="label"
                categories={["value"]}
                colors={["var(--chart-3)"]}
                valueFormatter={(val) => `${val}%`}
                yAxisWidth={36}
                className="h-32 mt-2"
                showLegend={false}
            />
        </Card>
    );
}

import { Card as TremorCard } from "@/components/tremor/Card";

export function SummaryStrip({ counts }: { counts: Record<Status | "Unmarked", number> }) {
    const items = [
        { label: "Present", value: counts.Present, tone: "bg-emerald-400" },
        { label: "Absent", value: counts.Absent, tone: "bg-rose-400" },
        { label: "Late", value: counts.Late, tone: "bg-amber-400" },
        { label: "Leave", value: counts.Leave, tone: "bg-violet-400" },
        { label: "Unmarked", value: counts.Unmarked, tone: "bg-slate-400" },
    ];
    return (
        <div className="kpi-grid" style={{ marginBottom: "1rem" }}>
            {items.map((i) => (
                <TremorCard
                    key={i.label}
                    className="flex flex-col items-center justify-center p-4"
                >
                    <span className={cn("w-3 h-3 rounded-full mb-2", i.tone)} />
                    <div className="text-2xl font-bold">
                        {i.value}
                    </div>
                    <div className="text-sm text-muted-foreground">{i.label}</div>
                </TremorCard>
            ))}
        </div>
    );
}
