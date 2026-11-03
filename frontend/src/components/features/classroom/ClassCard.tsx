"use client";

import { Badge } from "@/components/ui";
import type { ClassSectionCard } from "@/types";

// One class-section card on the principal's Classroom grid.
//
// Every figure is real: a value the backend could not compute comes back null and
// renders as "—" rather than a made-up number.

/** `90.5` -> `90.5%`, `null` -> `—`. */
function pct(value: number | null): string {
    return value === null ? "—" : `${value}%`;
}

/** Compact rupees: 425000 -> `₹4.3L`. */
function inr(value: number | null): string {
    if (value === null) return "—";
    if (value >= 100000) return `₹${(value / 100000).toFixed(1)}L`;
    if (value >= 1000) return `₹${Math.round(value / 1000)}K`;
    return `₹${Math.round(value)}`;
}

function Metric({ label, value }: { label: string; value: string }) {
    return (
        <div className="min-w-0">
            <div className="text-muted-foreground truncate text-[0.68rem] font-medium tracking-wide uppercase">
                {label}
            </div>
            <div className="truncate text-sm font-semibold">{value}</div>
        </div>
    );
}

function Bar({ value, tone }: { value: number | null; tone: string }) {
    const width = value === null ? 0 : Math.max(0, Math.min(100, value));
    return (
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-black/10 dark:bg-white/10">
            <div
                className={`h-full rounded-full transition-all ${tone}`}
                style={{ width: `${width}%` }}
            />
        </div>
    );
}

export default function ClassCard({
    classLabel,
    card,
}: {
    classLabel: string;
    card: ClassSectionCard;
}) {
    return (
        <article className="glass-tile flex h-full flex-col gap-3 rounded-2xl p-4">
            <header className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                    <div className="truncate text-base font-semibold">{classLabel}</div>
                    <div className="text-muted-foreground truncate text-xs">
                        {card.classTeacher ?? "No class teacher"}
                    </div>
                </div>
                <Badge tone={card.strength > 0 ? "accent" : "muted"}>
                    {card.strength} {card.strength === 1 ? "student" : "students"}
                </Badge>
            </header>

            <div className="grid grid-cols-3 gap-x-3 gap-y-3">
                <Metric label="Attendance" value={pct(card.attendancePercent)} />
                <Metric label="Course" value={pct(card.syllabusPercent)} />
                <Metric label="Fees" value={pct(card.feesPercent)} />
                <Metric
                    label="Present"
                    value={
                        card.attendanceDate
                            ? `${card.presentToday}/${card.strength}`
                            : "—"
                    }
                />
                <Metric label="Collected" value={inr(card.feesCollected)} />
                <Metric label="Avg marks" value={pct(card.avgMarksPercent)} />
            </div>

            <div className="space-y-2">
                <div>
                    <div className="text-muted-foreground mb-1 flex justify-between text-[0.68rem]">
                        <span>Attendance</span>
                        <span>{pct(card.attendancePercent)}</span>
                    </div>
                    <Bar value={card.attendancePercent} tone="bg-emerald-500" />
                </div>
                <div>
                    <div className="text-muted-foreground mb-1 flex justify-between text-[0.68rem]">
                        <span>Course complete</span>
                        <span>{pct(card.syllabusPercent)}</span>
                    </div>
                    <Bar value={card.syllabusPercent} tone="bg-violet-500" />
                </div>
                <div>
                    <div className="text-muted-foreground mb-1 flex justify-between text-[0.68rem]">
                        <span>Fees received</span>
                        <span>{pct(card.feesPercent)}</span>
                    </div>
                    <Bar value={card.feesPercent} tone="bg-amber-500" />
                </div>
            </div>

            <footer className="text-muted-foreground flex flex-wrap gap-x-3 gap-y-1 text-[0.68rem]">
                <span>{card.homeworkOpen} homework due</span>
                <span>{card.timetablePeriods} periods/wk</span>
                <span>{card.examsCount} exams</span>
                <span>
                    {card.lastDiaryDate ? `Diary ${card.lastDiaryDate}` : "No diary yet"}
                </span>
            </footer>
        </article>
    );
}
