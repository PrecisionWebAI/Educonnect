"use client";

import { Badge, Button, Card } from "@/components/ui";
import type { TrendRange } from "./useAttendance";
import { cn } from "cn";
import { dayLabel, thresholdTone, type DayCounts, type TrendBar } from "@/lib/attendance/view";

import { BarChart } from "@/components/tremor/BarChart";
import { Card as TremorCard } from "@/components/tremor/Card";

// The widgets read the server's numbers (`/summary`, `/trend`).
// Nothing here is a percentage the browser invented: a day nobody marked is missing
// from the chart rather than drawn as 0%, and a child below the school's threshold is
// flagged by the threshold the server sent, not by a constant in this file.

/**
 * The trend: one bar per open day somebody marked, for the week or the month of the day
 * on screen.
 *
 * The axis stays short (Mon, Tue ...) - a month of dates would not fit - but hovering a
 * bar names the day, the percentage and what it was made of ("12 of 16 present"), because
 * a percentage alone never told a teacher how many children it covered.
 */
export function TrendCard({
    bars,
    range,
    onRangeChange,
}: {
    bars: TrendBar[];
    range: TrendRange;
    onRangeChange: (range: TrendRange) => void;
}) {
    const toggle = (
        <div className="flex gap-1">
            {(["week", "month"] as const).map((option) => (
                <Button
                    key={option}
                    size="sm"
                    variant={range === option ? "primary" : "ghost"}
                    onClick={() => onRangeChange(option)}
                >
                    {option === "week" ? "Weekly" : "Monthly"}
                </Button>
            ))}
        </div>
    );

    if (bars.length === 0) {
        return (
            <Card title="Trend" action={toggle}>
                <p style={{ color: "var(--muted)", fontSize: "0.88rem" }}>
                    {range === "week"
                        ? "No register has been saved this week yet."
                        : "No register has been saved this month yet."}
                </p>
            </Card>
        );
    }

    return (
        <Card title="Trend" action={toggle}>
            <BarChart
                data={bars as unknown as Record<string, unknown>[]}
                index="label"
                categories={["value"]}
                colors={["var(--chart-3)"]}
                valueFormatter={(val) => `${val}%`}
                yAxisWidth={36}
                className="mt-2 h-32"
                showLegend={false}
                tooltipRenderer={(row) => {
                    const bar = row as unknown as TrendBar;
                    return (
                        <div className="space-y-1">
                            <p className="text-foreground text-sm font-medium">
                                {bar.label} · {dayLabel(bar.date)}
                            </p>
                            <p className="text-foreground text-sm font-semibold">{bar.value}%</p>
                            <p className="text-muted-foreground text-xs">
                                {bar.present} of {bar.marked} present
                            </p>
                        </div>
                    );
                }}
            />
        </Card>
    );
}

/**
 * The day at a glance: Present, Absent, Late and Unmarked - all from `dayModel`.
 *
 * Every number moves with the tap that changed it: the cards describe the register the
 * teacher is filling in, not the last save. The rows, the Save button and this strip read
 * the same object, so they cannot disagree.
 */
export function SummaryStrip({ counts }: { counts: DayCounts }) {
    const cards = [
        { label: "Present", value: counts.present, tone: "bg-emerald-400" },
        { label: "Absent", value: counts.absent, tone: "bg-rose-400" },
        { label: "Late", value: counts.late, tone: "bg-amber-400" },
        { label: "Unmarked", value: counts.unmarked, tone: "bg-slate-400" },
    ];
    return (
        <div className="kpi-grid" style={{ marginBottom: "1rem" }}>
            {cards.map((card) => (
                <TremorCard
                    key={card.label}
                    className="flex flex-col items-center justify-center p-4"
                >
                    <span className={cn("mb-2 h-3 w-3 rounded-full", card.tone)} />
                    <div className="text-2xl font-bold">{card.value}</div>
                    <div className="text-muted-foreground text-sm">{card.label}</div>
                </TremorCard>
            ))}
        </div>
    );
}

/** The threshold chip: below / at-or-above / no data. */
export function PercentChip({ percent, threshold }: { percent: number | null; threshold: number }) {
    const tone = thresholdTone(percent, threshold);
    if (tone === "none") return <span style={{ color: "var(--muted)" }}>—</span>;
    return (
        <Badge tone={tone === "below" ? "red" : "green"}>
            {percent}%{tone === "below" ? ` · below ${threshold}%` : ""}
        </Badge>
    );
}
