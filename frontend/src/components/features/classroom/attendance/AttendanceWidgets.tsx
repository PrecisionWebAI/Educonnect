"use client";

import { Badge, Card, Select, Spinner } from "@/components/ui";
import type { Status, SummaryRange } from "./useAttendance";
import { cn } from "cn";
import { thresholdTone } from "@/lib/attendance/view";
import type { StudentAttendanceTotal } from "@/types";

import { BarChart } from "@/components/tremor/BarChart";
import { Card as TremorCard } from "@/components/tremor/Card";

// The widgets read the server's numbers (`/summary`, `/trend`).
// Nothing here is a percentage the browser invented: a day nobody marked is missing
// from the chart rather than drawn as 0%, and a child below the school's threshold is
// flagged by the threshold the server sent, not by a constant in this file.

/** Weekly trend, straight from `GET …/trend` (open days only). */
export function WeeklyTrendCard({ trend }: { trend: { label: string; value: number }[] }) {
    if (trend.length === 0) {
        return (
            <Card title="Weekly Trend">
                <p style={{ color: "var(--muted)", fontSize: "0.88rem" }}>
                    No register has been saved this week yet.
                </p>
            </Card>
        );
    }
    return (
        <Card title="Weekly Trend">
            <BarChart
                data={trend}
                index="label"
                categories={["value"]}
                colors={["var(--chart-3)"]}
                valueFormatter={(val) => `${val}%`}
                yAxisWidth={36}
                className="mt-2 h-32"
                showLegend={false}
            />
        </Card>
    );
}

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
                <TremorCard key={i.label} className="flex flex-col items-center justify-center p-4">
                    <span className={cn("mb-2 h-3 w-3 rounded-full", i.tone)} />
                    <div className="text-2xl font-bold">{i.value}</div>
                    <div className="text-muted-foreground text-sm">{i.label}</div>
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

/**
 * Per-student totals over a period, with the school's own threshold.
 *
 * A child below it gets the "below 75%" chip; a child nobody has marked shows `—`
 * instead of `0%`, because "no data" and "never came" are not the same thing.
 */
export function TotalsPanel({
    rows,
    threshold,
    workingDays,
    range,
    onRangeChange,
    loading,
}: {
    rows: StudentAttendanceTotal[];
    threshold: number;
    workingDays: number;
    range: SummaryRange;
    onRangeChange: (value: SummaryRange) => void;
    loading: boolean;
}) {
    const flagged = rows.filter((row) => row.belowThreshold).length;
    const noData = rows.filter((row) => row.percent === null).length;

    return (
        <Card
            title="Totals"
            action={
                <Select
                    value={range}
                    onChange={(e) => onRangeChange(e.target.value as SummaryRange)}
                    aria-label="Period"
                >
                    <option value="week">This week</option>
                    <option value="fortnight">Last 14 days</option>
                    <option value="month">This month</option>
                </Select>
            }
        >
            {loading ? (
                <Spinner />
            ) : rows.length === 0 ? (
                <p style={{ color: "var(--muted)", fontSize: "0.88rem" }}>
                    No totals yet — save a register first.
                </p>
            ) : (
                <>
                    <p
                        style={{
                            color: "var(--muted)",
                            fontSize: "0.82rem",
                            marginBottom: "0.5rem",
                        }}
                    >
                        {workingDays} open {workingDays === 1 ? "day" : "days"} · {flagged} below{" "}
                        {threshold}%{noData ? ` · ${noData} with no data` : ""}
                    </p>
                    <div className="table-wrap">
                        <table className="table">
                            <thead>
                                <tr>
                                    <th>Student</th>
                                    <th>Present</th>
                                    <th>Absent</th>
                                    <th>Leave</th>
                                    <th>%</th>
                                </tr>
                            </thead>
                            <tbody>
                                {rows.map((row) => (
                                    <tr key={row.studentId}>
                                        <td>
                                            <b>{row.name}</b>
                                            <div
                                                style={{
                                                    color: "var(--muted)",
                                                    fontSize: "0.74rem",
                                                }}
                                            >
                                                {row.admissionNo ?? "—"}
                                            </div>
                                        </td>
                                        <td>{row.present}</td>
                                        <td>{row.absent}</td>
                                        <td>{row.leave}</td>
                                        <td>
                                            <PercentChip
                                                percent={row.percent}
                                                threshold={threshold}
                                            />
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </>
            )}
        </Card>
    );
}
