"use client";

import React, { useRef, useState } from "react";
import { GraduationCap, LayoutDashboard, Mail, Users, Wallet, Zap } from "lucide-react";
import TiltCard from "./TiltCard";
import { cn } from "@/lib/utils";

type Tone = "success" | "warning" | "neutral";

interface Kpi {
    label: string;
    value: string;
    delta: string;
    tone: Tone;
}

interface Row {
    title: string;
    meta: string;
    status: string;
    tone: Tone;
}

interface View {
    id: string;
    label: string;
    short: string;
    icon: React.ElementType;
    headline: string;
    badge: string;
    kpis: Kpi[];
    progress: { label: string; value: number; note: string };
    rows: Row[];
    highlight: { title: string; body: string; status: string };
}

const VIEWS: View[] = [
    {
        id: "principal",
        label: "Principal Command",
        short: "Principal",
        icon: LayoutDashboard,
        headline: "Campus Live Telemetry",
        badge: "Active Session • Live Feed",
        kpis: [
            { label: "Today's Attendance", value: "96.4%", delta: "+2.1%", tone: "success" },
            { label: "Fee Collection (Q2)", value: "₹42.8L", delta: "+18.4%", tone: "success" },
        ],
        progress: {
            label: "Fee Collection Progress (Q2)",
            value: 94,
            note: "₹78.2L invoiced · 94.2% collected",
        },
        rows: [
            {
                title: "Admissions Pipeline",
                meta: "Grade 6–11 · 2026 intake",
                status: "420 / 400 (105%)",
                tone: "success",
            },
            {
                title: "Audit-ready Compliance Pack",
                meta: "CBSE + state board returns",
                status: "Auto-generated",
                tone: "neutral",
            },
        ],
        highlight: {
            title: "Principal digest dispatched",
            body: "Daily attendance, fee and staff summary sent to 6 leaders at 07:05 AM.",
            status: "Delivered",
        },
    },
    {
        id: "faculty",
        label: "Faculty Workspace",
        short: "Faculty",
        icon: GraduationCap,
        headline: "Classroom OS — Grade 10-A",
        badge: "Smart Grading • AI Assisted",
        kpis: [
            { label: "Papers Awaiting Review", value: "4", delta: "AI pre-graded", tone: "neutral" },
            { label: "Periods Today", value: "6", delta: "Next 10:15 AM", tone: "success" },
        ],
        progress: {
            label: "Term Evaluation Completion",
            value: 88,
            note: "Mathematics Honors · Avg 88.4% (A+)",
        },
        rows: [
            {
                title: "Physics Lab — Optics (10-B)",
                meta: "Rubric-aligned answer sheet scan",
                status: "AI Graded",
                tone: "success",
            },
            {
                title: "English Essay (9-A)",
                meta: "Submissions close today 6:00 PM",
                status: "34 / 36 Submitted",
                tone: "warning",
            },
        ],
        highlight: {
            title: "Homework reminder queued",
            body: "2 pending students auto-nudged with a parent copy on the family app.",
            status: "Queued",
        },
    },
    {
        id: "family",
        label: "Family Portal",
        short: "Family",
        icon: Users,
        headline: "Family Companion — Aarav Sharma",
        badge: "Parent & Student • Live Sync",
        kpis: [
            { label: "Child Attendance", value: "96%", delta: "41/43 days", tone: "success" },
            { label: "Pending Fees", value: "₹0", delta: "Paid 12 Sep", tone: "success" },
        ],
        progress: {
            label: "Term Progress — Grade 8",
            value: 82,
            note: "Next: Mathematics @ 10:15 AM · Room 204",
        },
        rows: [
            {
                title: "Teacher Mrs. Roy",
                meta: "\u201cGreat progress on the science project today!\u201d",
                status: "New Message",
                tone: "neutral",
            },
            {
                title: "Bus #12 — Route 4",
                meta: "Driver Ramesh · Live GPS telemetry",
                status: "4 mins away",
                tone: "success",
            },
        ],
        highlight: {
            title: "Report card published",
            body: "Term II report card and attendance register available as PDF in the app.",
            status: "Download",
        },
    },
    {
        id: "finance",
        label: "Finance Desk",
        short: "Finance",
        icon: Wallet,
        headline: "Finance Control Tower",
        badge: "Reconciled • Zero Manual Ledgers",
        kpis: [
            { label: "Payroll Cleared", value: "₹18.2L", delta: "142 staff", tone: "success" },
            { label: "Overdues Recovered", value: "78%", delta: "+11% MoM", tone: "success" },
        ],
        progress: {
            label: "Monthly Budget Utilisation",
            value: 71,
            note: "Transport & library well within plan",
        },
        rows: [
            {
                title: "Automated Fee Reminders",
                meta: "Every Monday 10:00 · 96 guardians",
                status: "Running",
                tone: "success",
            },
            {
                title: "Vendor Invoice Batch #2291",
                meta: "Awaiting principal e-sign",
                status: "Pending",
                tone: "warning",
            },
        ],
        highlight: {
            title: "Tally / ERP export ready",
            body: "Ledger, receipts and payroll journals exported for the accountant.",
            status: "Export",
        },
    },
];

const TONE_PILL: Record<Tone, string> = {
    success: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-500/30",
    warning: "bg-amber-500/10 text-amber-700 dark:text-amber-300 border-amber-500/30",
    neutral:
        "bg-slate-100 dark:bg-white/10 text-slate-700 dark:text-slate-200 border-slate-200 dark:border-white/20",
};

const TONE_DOT: Record<Tone, string> = {
    success: "bg-emerald-500",
    warning: "bg-amber-500",
    neutral: "bg-slate-500 dark:bg-slate-300",
};

/**
 * Interactive product preview used in the hero — visitors switch between the
 * Principal / Faculty / Family / Finance workspaces without leaving the page.
 */
export default function HeroShowcase() {
    const [activeIndex, setActiveIndex] = useState(0);
    const tabRefs = useRef<Array<HTMLButtonElement | null>>([]);
    const active = VIEWS[activeIndex] ?? VIEWS[0];

    const move = (direction: 1 | -1) => {
        const count = VIEWS.length;
        const next = (activeIndex + direction + count) % count;
        setActiveIndex(next);
        tabRefs.current[next]?.focus();
    };

    const onKeyDown = (event: React.KeyboardEvent<HTMLDivElement>) => {
        if (event.key === "ArrowRight") {
            event.preventDefault();
            move(1);
        } else if (event.key === "ArrowLeft") {
            event.preventDefault();
            move(-1);
        }
    };

    return (
        <div className="lg:col-span-5 relative">
            {/* Floating Glass Micro-Badges */}
            <div className="absolute -top-6 -left-6 z-20 hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-xl glass-pill shadow-xl text-xs font-semibold text-slate-800 dark:text-slate-100 border border-slate-200 dark:border-white/20 animate-float-slow backdrop-blur-xl font-mono">
                <span className="w-2 h-2 rounded-full bg-emerald-500 live-beacon" />
                <span>99.9% Uptime Verified</span>
            </div>
            <div className="absolute -bottom-5 -right-4 z-20 hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-xl glass-pill shadow-xl text-xs font-semibold text-slate-800 dark:text-slate-100 border border-slate-200 dark:border-white/20 animate-float-reverse backdrop-blur-xl font-mono">
                <Zap className="text-cyan-500" size={18} />
                <span>1.2s AI Copilot Response</span>
            </div>

            {/* 3D Perspective Tilt container */}
            <TiltCard
                maxRotation={5}
                className="relative rounded-2xl p-5 border border-slate-200 dark:border-white/15 shadow-2xl space-y-4 bg-white/85 dark:bg-slate-900/70 backdrop-blur-2xl transition-all"
                style={{
                    boxShadow:
                        "rgba(255, 255, 255, 0.75) 0px 2px 1.5px 0px inset, rgba(191, 219, 254, 0.3) 1px 0px 1px 0px inset, rgba(0, 0, 0, 0.3) 0px -1.5px 2px 0px inset, rgba(15, 23, 42, 0.45) 0px 30px 60px -12px, rgba(37, 99, 235, 0.18) 0px 0px 30px",
                }}
            >
                {/* Mock Header Bar with live beacon */}
                <div className="flex items-center justify-between gap-3 pb-3 border-b border-slate-200 dark:border-white/10">
                    <div className="flex items-center gap-2 min-w-0">
                        <div className="w-3 h-3 rounded-full bg-slate-400/50" />
                        <div className="w-3 h-3 rounded-full bg-slate-500 dark:bg-slate-400/60" />
                        <div className="w-3 h-3 rounded-full bg-slate-700 dark:bg-slate-200" />
                        <span className="ml-2 text-xs font-bold text-slate-900 dark:text-white tracking-wide font-heading truncate">
                            {active.headline}
                        </span>
                    </div>
                    <span className="shrink-0 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-blue-500/10 text-blue-700 dark:bg-sky-400/15 dark:text-sky-300 border border-blue-500/20 dark:border-sky-400/30 flex items-center gap-1.5 font-mono">
                        <span className="w-2 h-2 rounded-full bg-emerald-500 live-beacon" />
                        <span>{active.badge}</span>
                    </span>
                </div>

                {/* Workspace switcher */}
                <div
                    role="tablist"
                    aria-label="Workspace preview"
                    onKeyDown={onKeyDown}
                    className="flex gap-1 p-1 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-white/10"
                >
                    {VIEWS.map((view, index) => {
                        const Icon = view.icon;
                        const selected = index === activeIndex;
                        return (
                            <button
                                key={view.id}
                                ref={(el) => {
                                    tabRefs.current[index] = el;
                                }}
                                type="button"
                                role="tab"
                                id={`showcase-tab-${view.id}`}
                                aria-selected={selected}
                                aria-controls={`showcase-panel-${view.id}`}
                                tabIndex={selected ? 0 : -1}
                                onClick={() => setActiveIndex(index)}
                                className={cn(
                                    "flex-1 inline-flex items-center justify-center gap-1 rounded-lg px-1.5 py-2 text-[9px] sm:text-[11px] font-bold tracking-wide transition-all font-mono",
                                    selected
                                        ? "bg-blue-600 text-white shadow-md shadow-blue-600/25"
                                        : "text-slate-500 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700/70",
                                )}
                            >
                                <Icon size={13} />
                                <span className="hidden sm:inline">{view.label}</span>
                                <span className="sm:hidden">{view.short}</span>
                            </button>
                        );
                    })}
                </div>

                {/* Active workspace panel */}
                <div
                    key={active.id}
                    role="tabpanel"
                    id={`showcase-panel-${active.id}`}
                    aria-labelledby={`showcase-tab-${active.id}`}
                    className="panel-enter space-y-3"
                >
                    {/* KPI dual widget */}
                    <div className="grid grid-cols-2 gap-3">
                        {active.kpis.map((kpi) => (
                            <div
                                key={kpi.label}
                                className="p-3.5 rounded-xl border border-slate-200 dark:border-white/10 bg-slate-50/70 dark:bg-slate-800/60 transition-all hover:scale-[1.02] cursor-default"
                            >
                                <p className="text-[11px] text-slate-500 dark:text-slate-400 mb-1 font-medium flex items-center justify-between gap-2">
                                    <span className="truncate">{kpi.label}</span>
                                    <span className={cn("w-1.5 h-1.5 rounded-full shrink-0", TONE_DOT[kpi.tone])} />
                                </p>
                                <div className="flex items-baseline gap-1.5">
                                    <span className="text-xl font-bold text-slate-900 dark:text-white font-heading">
                                        {kpi.value}
                                    </span>
                                    <span className="text-[11px] font-bold text-blue-700 dark:text-sky-300 bg-blue-500/10 dark:bg-sky-400/15 px-1 rounded font-mono">
                                        {kpi.delta}
                                    </span>
                                </div>
                            </div>
                        ))}
                    </div>

                    {/* Progress block */}
                    <div className="p-3.5 rounded-xl bg-slate-50/70 dark:bg-slate-800/60 border border-slate-200 dark:border-white/10">
                        <div className="flex items-center justify-between text-xs mb-2 gap-3">
                            <span className="font-bold text-slate-900 dark:text-white truncate">
                                {active.progress.label}
                            </span>
                            <span className="font-bold text-blue-700 dark:text-sky-300 font-mono shrink-0">
                                {active.progress.value}%
                            </span>
                        </div>
                        <div className="w-full h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                            <div
                                className="h-full bg-gradient-to-r from-blue-600 via-indigo-500 to-cyan-400 dark:to-sky-300 rounded-full transition-all duration-1000"
                                style={{ width: `${active.progress.value}%` }}
                            />
                        </div>
                        <p className="text-[10px] text-slate-500 dark:text-slate-400 mt-2 font-mono">
                            {active.progress.note}
                        </p>
                    </div>

                    {/* Activity rows */}
                    <div className="space-y-2">
                        {active.rows.map((row) => (
                            <div
                                key={row.title}
                                className="p-3 rounded-xl bg-slate-50/70 dark:bg-slate-800/50 border border-slate-200 dark:border-white/5 flex items-center justify-between gap-3 transition-transform hover:scale-[1.01]"
                            >
                                <div className="min-w-0">
                                    <p className="text-xs font-semibold text-slate-900 dark:text-white truncate">
                                        {row.title}
                                    </p>
                                    <p className="text-[10px] text-slate-500 dark:text-slate-400 font-mono truncate">
                                        {row.meta}
                                    </p>
                                </div>
                                <span
                                    className={cn(
                                        "shrink-0 text-[10px] font-bold px-2 py-0.5 rounded-md border font-mono",
                                        TONE_PILL[row.tone],
                                    )}
                                >
                                    {row.status}
                                </span>
                            </div>
                        ))}
                    </div>

                    {/* Cross-role highlight */}
                    <div className="p-3.5 rounded-xl border border-slate-200 dark:border-white/15 flex items-center justify-between gap-3 bg-white/95 dark:bg-slate-900/85 backdrop-blur-md transition-transform hover:scale-[1.01]">
                        <div className="flex items-center gap-2.5 min-w-0">
                            <div className="w-7 h-7 rounded-lg bg-blue-500/10 dark:bg-sky-400/15 text-blue-600 dark:text-sky-300 flex items-center justify-center relative shrink-0">
                                <Mail size={16} />
                                <span className="absolute -top-1 -right-1 w-2 h-2 rounded-full bg-emerald-500" />
                            </div>
                            <div className="min-w-0">
                                <p className="text-xs font-semibold text-slate-900 dark:text-white truncate">
                                    {active.highlight.title}
                                </p>
                                <p className="text-[10px] text-slate-500 dark:text-slate-400 font-mono truncate">
                                    {active.highlight.body}
                                </p>
                            </div>
                        </div>
                        <span className="shrink-0 text-[10px] font-bold text-white bg-blue-600 px-2 py-0.5 rounded-md font-mono shadow-sm shadow-blue-600/25">
                            {active.highlight.status}
                        </span>
                    </div>
                </div>
            </TiltCard>
        </div>
    );
}
