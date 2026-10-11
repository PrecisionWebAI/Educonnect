"use client";

import React, { useRef, useState } from "react";
import {
  GraduationCap,
  LayoutDashboard,
  Lock,
  Mail,
  Users,
  Wallet,
  Zap,
} from "lucide-react";
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
      {
        label: "Today's Attendance",
        value: "96.4%",
        delta: "+2.1%",
        tone: "success",
      },
      {
        label: "Fee Collection (Q2)",
        value: "₹42.8L",
        delta: "+18.4%",
        tone: "success",
      },
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
      {
        label: "Papers Awaiting Review",
        value: "4",
        delta: "AI pre-graded",
        tone: "neutral",
      },
      {
        label: "Periods Today",
        value: "6",
        delta: "Next 10:15 AM",
        tone: "success",
      },
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
      {
        label: "Child Attendance",
        value: "96%",
        delta: "41/43 days",
        tone: "success",
      },
      {
        label: "Pending Fees",
        value: "₹0",
        delta: "Paid 12 Sep",
        tone: "success",
      },
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
      {
        label: "Payroll Cleared",
        value: "₹18.2L",
        delta: "142 staff",
        tone: "success",
      },
      {
        label: "Overdues Recovered",
        value: "78%",
        delta: "+11% MoM",
        tone: "success",
      },
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
  success:
    "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300/80 dark:bg-emerald-950/30 border-emerald-500/20",
  warning:
    "bg-[#99753a]/10 text-[#99753a] dark:text-[#99753a] dark:bg-[#99753a]/10 border-[#99753a]/20",
  neutral:
    "bg-slate-100 dark:bg-white/5 text-slate-700 dark:text-slate-300 border-slate-200 dark:border-white/5",
};

const TONE_DOT: Record<Tone, string> = {
  success: "bg-emerald-500 dark:bg-emerald-400/80",
  warning: "bg-[#99753a]",
  neutral: "bg-slate-500 dark:bg-slate-400",
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
    <div className="relative w-full lg:col-span-5">
      {/* Minimalistic Web Browser Frame with Diffuse Depth Shadow */}
      <div className="group relative w-full overflow-hidden rounded-2xl border border-slate-200/90 bg-white shadow-xl shadow-slate-200/60 transition-all sm:rounded-3xl dark:border-white/10 dark:bg-[#1C294A] dark:shadow-2xl dark:shadow-black/50">
        {/* Minimalist Browser Chrome Top Bar */}
        <div className="flex items-center justify-between gap-2 border-b border-slate-200/80 bg-slate-100/90 px-3.5 py-2.5 sm:gap-3 sm:px-4 sm:py-3 dark:border-white/5 dark:bg-[#131E3A]">
          {/* macOS-style 3 Traffic Light Dots */}
          <div
            className="flex shrink-0 items-center gap-1.5"
            aria-hidden="true"
          >
            <span className="inline-block h-2.5 w-2.5 rounded-full border border-rose-500/40 bg-rose-400 sm:h-3 sm:w-3" />
            <span className="inline-block h-2.5 w-2.5 rounded-full border border-amber-500/40 bg-amber-400 sm:h-3 sm:w-3" />
            <span className="inline-block h-2.5 w-2.5 rounded-full border border-emerald-500/40 bg-emerald-400 sm:h-3 sm:w-3" />
          </div>

          {/* Centered Minimal Browser Address / Title Bar */}
          <div className="mx-auto flex max-w-42.5 min-w-0 flex-1 items-center justify-center gap-1.5 rounded-lg border border-slate-200/80 bg-white/95 px-2.5 py-1 text-[10px] text-slate-500 shadow-xs select-none sm:max-w-xs sm:px-3 sm:text-[11px] dark:border-white/5 dark:bg-[#0B1221] dark:text-slate-400">
            <Lock
              size={11}
              className="shrink-0 text-emerald-600 dark:text-emerald-400/80"
            />
            <span className="truncate font-medium text-slate-700 dark:text-slate-300">
              app.educonnect.school/overview
            </span>
          </div>

          {/* Right Live Indicator Pill */}
          <div className="flex shrink-0 items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold text-emerald-700 sm:px-2.5 sm:text-[11px] dark:border-emerald-500/20 dark:bg-emerald-950/30 dark:text-emerald-300/80">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-500" />
            <span className="hidden sm:inline">Live Sync</span>
          </div>
        </div>

        {/* Browser Viewport Content Area */}
        <div className="space-y-5 bg-white p-6 sm:space-y-6 sm:p-8 dark:bg-[#1C294A]">
          {/* Role Switcher Tabs: Horizontal Swipe Container on Mobile, Wrapped Center on Tablet/Desktop */}
          <div className="w-full">
            <div
              role="tablist"
              aria-label="Workspace preview"
              onKeyDown={onKeyDown}
              className="flex overflow-x-auto whitespace-nowrap hide-scrollbar md:flex-wrap md:justify-center gap-2 p-1.5 rounded-xl border border-slate-200/80 bg-slate-100/90 dark:border-white/5 dark:bg-[#131E3A]"
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
                      "inline-flex shrink-0 items-center justify-center gap-2 rounded-lg px-3.5 py-2 text-xs font-semibold whitespace-nowrap transition-all cursor-pointer",
                      selected
                        ? "bg-[#99753a] font-bold text-white shadow-md shadow-[#99753a]/25 dark:shadow-md dark:shadow-black/40"
                        : "text-slate-600 hover:bg-white hover:text-slate-900 dark:text-slate-300 dark:hover:bg-[#1C294A] dark:hover:text-slate-50",
                    )}
                  >
                    <Icon size={14} className="shrink-0" />
                    <span>{view.label}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Isolated Key Metrics Panel */}
          <div
            key={active.id}
            role="tabpanel"
            id={`showcase-panel-${active.id}`}
            aria-labelledby={`showcase-tab-${active.id}`}
            className="panel-enter space-y-4"
          >
            {/* Dual KPIs: Responsive 1 col on mobile, 2 col on tablet/desktop */}
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 sm:gap-4">
              {active.kpis.map((kpi) => (
                <div
                  key={kpi.label}
                  className="rounded-xl border border-slate-200/80 bg-slate-50/90 p-5 transition-all hover:border-slate-300 sm:p-6 dark:border-white/5 dark:bg-[#131E3A] dark:hover:border-white/10 shadow-xs"
                >
                  <p className="mb-2 flex items-center justify-between gap-2 text-xs font-medium text-slate-600 dark:text-slate-400">
                    <span className="truncate">{kpi.label}</span>
                    <span
                      className={cn(
                        "h-2 w-2 shrink-0 rounded-full",
                        TONE_DOT[kpi.tone],
                      )}
                    />
                  </p>
                  <div className="flex flex-wrap items-baseline gap-2">
                    <span className="font-heading text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-50 sm:text-3xl">
                      {kpi.value}
                    </span>
                    <span className="rounded border border-emerald-200/60 bg-emerald-50 px-2 py-0.5 text-xs font-semibold text-emerald-700/80 dark:border-emerald-500/20 dark:bg-emerald-950/30 dark:text-emerald-300/80">
                      {kpi.delta}
                    </span>
                  </div>
                </div>
              ))}
            </div>

            {/* Progress & Milestone Card */}
            <div className="rounded-xl border border-slate-200/80 bg-slate-50/90 p-5 sm:p-6 dark:border-white/5 dark:bg-[#131E3A] shadow-xs">
              <div className="mb-2.5 flex items-center justify-between gap-3 text-xs sm:text-sm">
                <span className="truncate font-semibold text-slate-900 dark:text-slate-200">
                  {active.progress.label}
                </span>
                <span className="shrink-0 font-bold text-[#99753a]">
                  {active.progress.value}%
                </span>
              </div>
              <div className="h-2.5 w-full overflow-hidden rounded-full bg-slate-200 dark:bg-[#0B1221]">
                <div
                  className="h-full rounded-full bg-[#99753a] transition-all duration-700"
                  style={{ width: `${active.progress.value}%` }}
                />
              </div>
              <p className="mt-2 text-xs font-medium text-slate-500 dark:text-slate-400">
                {active.progress.note}
              </p>
            </div>

            {/* Operational Summary Highlight */}
            <div className="flex flex-col items-start justify-between gap-3 rounded-xl border border-slate-200/80 bg-slate-50/90 p-5 sm:flex-row sm:items-center sm:gap-4 sm:p-6 dark:border-white/5 dark:bg-[#131E3A] shadow-xs">
              <div className="flex w-full min-w-0 items-center gap-3 sm:w-auto">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-[#99753a]/20 bg-[#99753a]/10 text-[#99753a] dark:border-white/5 dark:bg-[#0B1221]">
                  <Mail size={16} />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-xs sm:text-sm font-semibold text-slate-900 dark:text-slate-100">
                    {active.highlight.title}
                  </p>
                  <p className="truncate text-xs text-slate-500 dark:text-slate-400">
                    {active.highlight.body}
                  </p>
                </div>
              </div>
              <span className="shrink-0 self-end rounded-md border border-[#99753a]/20 bg-[#99753a]/10 px-3 py-1 text-[11px] font-semibold text-[#99753a] sm:self-auto">
                {active.highlight.status}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
