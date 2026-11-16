"use client";

import {
    ArrowUpRight,
    BookOpen,
    CalendarDays,
    ClipboardList,
    GraduationCap,
    UsersRound,
    Wallet,
} from "lucide-react";
import type { ReactNode } from "react";
import type { ClassSectionCard } from "@/types";

function pct(value: number | null): string {
    if (value === null) return "—";
    return `${new Intl.NumberFormat(undefined, { maximumFractionDigits: 1 }).format(value)}%`;
}

function inr(value: number | null): string {
    if (value === null) return "—";
    if (value >= 100000) return `₹${(value / 100000).toFixed(1)}L`;
    if (value >= 1000) return `₹${Math.round(value / 1000)}K`;
    return `₹${Math.round(value)}`;
}

function ProgressMetric({
    label,
    value,
    detail,
    icon,
}: {
    label: string;
    value: number | null;
    detail: string;
    icon: ReactNode;
}) {
    const percentage = value === null ? null : Math.max(0, Math.min(100, value));

    return (
        <div className="space-y-1.5">
            <div className="flex items-center justify-between gap-3">
                <div className="flex min-w-0 items-center gap-2">
                    <span className="text-primary [&>svg]:size-3.5">{icon}</span>
                    <span className="truncate text-xs font-medium">{label}</span>
                </div>
                <span className="shrink-0 text-xs font-semibold">
                    {value === null ? "No data" : pct(value)}
                </span>
            </div>
            {percentage === null ? (
                <div className="bg-muted/70 h-1.5 rounded-full" aria-hidden="true" />
            ) : (
                <div
                    className="bg-muted/70 h-1.5 overflow-hidden rounded-full"
                    role="progressbar"
                    aria-label={label}
                    aria-valuemin={0}
                    aria-valuemax={100}
                    aria-valuenow={percentage}
                    aria-valuetext={pct(value)}
                >
                    <div
                        className="bg-primary h-full rounded-full transition-[width]"
                        style={{ width: `${percentage}%` }}
                    />
                </div>
            )}
            <p className="text-muted-foreground truncate text-[0.7rem]">{detail}</p>
        </div>
    );
}

function QuickStat({ icon, label, value }: { icon: ReactNode; label: string; value: string }) {
    return (
        <div className="classroom-quick-stat border-border/70 bg-card/35 flex min-w-0 items-center gap-2 rounded-xl border px-2.5 py-2">
            <span className="text-muted-foreground shrink-0 [&>svg]:size-3.5">{icon}</span>
            <span className="min-w-0 flex-1 truncate text-[0.68rem]">{label}</span>
            <span className="shrink-0 text-xs font-semibold">{value}</span>
        </div>
    );
}

export default function ClassCard({ card }: { card: ClassSectionCard }) {
    return (
        <article className="glass-tile classroom-section-card group flex h-full flex-col gap-4 rounded-2xl p-4 sm:p-5">
            <header className="flex items-start justify-between gap-3">
                <div className="flex min-w-0 items-center gap-3">
                    <span className="bg-primary/10 text-primary grid size-10 shrink-0 place-items-center rounded-xl">
                        <GraduationCap aria-hidden="true" className="size-5" />
                    </span>
                    <div className="min-w-0">
                        <p className="text-muted-foreground text-[0.65rem] font-semibold tracking-[0.14em] uppercase">
                            Section
                        </p>
                        <h3 className="truncate text-base font-semibold">{card.sectionName}</h3>
                    </div>
                </div>
                <div className="shrink-0 text-right">
                    <div className="text-lg leading-tight font-semibold">
                        {card.strength.toLocaleString()}
                    </div>
                    <div className="text-muted-foreground text-[0.68rem]">
                        {card.strength === 1 ? "student" : "students"}
                    </div>
                </div>
            </header>

            <div className="text-muted-foreground flex min-w-0 items-center gap-2 text-xs">
                <UsersRound aria-hidden="true" className="text-primary size-4 shrink-0" />
                <span className="truncate">
                    {card.classTeacher ?? "Class teacher not assigned"}
                </span>
            </div>

            <div className="border-border/70 space-y-3 border-y py-3.5">
                <ProgressMetric
                    label="Attendance"
                    value={card.attendancePercent}
                    detail={
                        card.attendanceDate
                            ? `${card.presentToday} of ${card.strength} present today`
                            : "No attendance register recorded today"
                    }
                    icon={<UsersRound aria-hidden="true" />}
                />
                <ProgressMetric
                    label="Course completion"
                    value={card.syllabusPercent}
                    detail={
                        card.subjectsTracked > 0
                            ? `${card.subjectsTracked} subjects tracked`
                            : "No subjects tracked yet"
                    }
                    icon={<BookOpen aria-hidden="true" />}
                />
                <ProgressMetric
                    label="Fees received"
                    value={card.feesPercent}
                    detail={
                        card.feesCollected === null
                            ? "No fee collection data yet"
                            : `${inr(card.feesCollected)} collected`
                    }
                    icon={<Wallet aria-hidden="true" />}
                />
            </div>

            <div className="grid grid-cols-2 gap-2">
                <QuickStat
                    icon={<BookOpen aria-hidden="true" />}
                    label="Open homework"
                    value={card.homeworkOpen.toLocaleString()}
                />
                <QuickStat
                    icon={<GraduationCap aria-hidden="true" />}
                    label="Average marks"
                    value={pct(card.avgMarksPercent)}
                />
                <QuickStat
                    icon={<CalendarDays aria-hidden="true" />}
                    label="Periods / week"
                    value={card.timetablePeriods.toLocaleString()}
                />
                <QuickStat
                    icon={<ClipboardList aria-hidden="true" />}
                    label="Exams"
                    value={card.examsCount.toLocaleString()}
                />
            </div>

            <footer className="text-muted-foreground mt-auto flex items-center justify-between gap-2 text-[0.7rem]">
                <span className="truncate">
                    {card.lastDiaryDate
                        ? `Diary updated ${card.lastDiaryDate}`
                        : "No class diary update"}
                </span>
                <span className="text-primary inline-flex shrink-0 items-center gap-1 font-semibold">
                    Open section
                    <ArrowUpRight
                        aria-hidden="true"
                        className="size-3.5 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5"
                    />
                </span>
            </footer>
        </article>
    );
}
