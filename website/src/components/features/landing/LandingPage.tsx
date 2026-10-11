"use client";

import React, { useEffect, useRef, useState } from "react";
import {
  ArrowRight,
  Award,
  Calculator,
  CheckCircle,
  Download,
  Lock,
  Shield,
  Sliders,
  Star,
  TrendingUp,
  Users,
  Zap,
} from "lucide-react";
import TiltCard from "./TiltCard";
import Reveal from "./Reveal";
import AiCopilotModule from "./AiCopilotModule";
import RoiCalculator from "./RoiCalculator";
import HeroShowcase from "./HeroShowcase";
import PricingSection from "./PricingSection";
import FaqSection from "./FaqSection";
import Navbar from "@/components/layout/Navbar";
import Footer from "@/components/layout/Footer";

const APP_AUTH_URL = process.env.NEXT_PUBLIC_APP_URL || "http://localhost:3000";

const STATS = [
  { value: "500+", label: "Schools onboarded" },
  { value: "2.5L+", label: "Active Students" },
  { value: "99.9%", label: "Uptime guarantee" },
  { value: "40%", label: "Admin time saved" },
];

function Counter({ value }: { value: string }) {
  const num = parseFloat(value.replace(/[^0-9.]/g, ""));
  const suffix = value.replace(/[0-9.,]/g, "");
  const ref = useRef<HTMLParagraphElement>(null);
  const [display, setDisplay] = useState("0");
  const decimals = num % 1 !== 0 ? 1 : 0;

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const io = new IntersectionObserver(
      ([entry]) => {
        if (!entry?.isIntersecting) return;
        io.disconnect();
        const dur = 950;
        const start = performance.now();
        const tick = (t: number) => {
          const p = Math.min(1, (t - start) / dur);
          const eased = 1 - Math.pow(1 - p, 3);
          setDisplay((num * eased).toFixed(decimals));
          if (p < 1) requestAnimationFrame(tick);
        };
        requestAnimationFrame(tick);
      },
      { threshold: 0.4 },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [num, decimals]);

  return (
    <p
      ref={ref}
      className="font-heading mb-1 text-3xl font-extrabold text-slate-900 transition-transform group-hover:scale-105 sm:text-4xl dark:text-white"
    >
      {display}
      {suffix}
    </p>
  );
}

const SCHOOLS = [
  "Sunrise Public School",
  "Green Valley Academy",
  "St. Xavier High",
  "Nova International",
  "Little Flowers School",
  "Prime Scholars Global",
  "Riverdale Public School",
  "Bright Future Academy",
];

const ABOUT_POINTS = [
  "Attendance, marks, exams and report cards — one screen for every teacher",
  "Fees, receipts, budgets, payroll and payslips for the finance team",
  "Library, transport, leave & applications — all workflows online",
  "Parent–teacher meetings, chat, tickets and role-based notifications",
  "Reports, analytics and AI Copilot for smarter school decisions",
];

export default function LandingPage() {
  return (
    <div className="relative min-h-screen overflow-x-hidden bg-slate-50 text-slate-900 transition-colors duration-300 selection:bg-[#99753a] selection:text-white dark:bg-[#0B1221] dark:text-slate-200">
      {/* Subtle Institutional Ambient Gradient Wash */}
      <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
        <div
          className="pointer-events-none absolute -top-40 left-1/4 h-[720px] w-[720px] rounded-full opacity-40 blur-[140px] transition-opacity duration-300 dark:opacity-20"
          style={{
            background:
              "radial-gradient(circle, rgba(19, 30, 58, 0.45) 0%, rgba(153, 117, 58, 0.05) 50%, transparent 75%)",
          }}
        />
        <div
          className="pointer-events-none absolute top-1/3 -right-32 h-[600px] w-[600px] rounded-full opacity-30 blur-[140px] transition-opacity duration-300 dark:opacity-15"
          style={{
            background:
              "radial-gradient(circle, rgba(28, 41, 74, 0.35) 0%, transparent 75%)",
          }}
        />
      </div>

      {/* Floating glass navigation */}
      <Navbar />

      {/* Hero Section */}
      <section className="relative mx-auto max-w-7xl px-4 pt-28 pb-14 sm:px-6 sm:pt-36 sm:pb-16">
        <div className="relative z-10">
          {/* Professional Frosted Hero Container */}
          <div className="relative mb-12 overflow-hidden rounded-3xl border border-slate-200/80 bg-white/95 p-8 text-slate-900 shadow-xl shadow-slate-200/50 backdrop-blur-xl transition-colors sm:mb-16 sm:p-12 lg:p-16 dark:border-white/5 dark:bg-[#131E3A]/90 dark:text-slate-50 dark:shadow-2xl dark:shadow-black/50">
            <div className="relative z-10 grid grid-cols-1 items-center gap-12 lg:grid-cols-12">
              {/* Left: Copy and Balanced CTAs */}
              <div className="relative space-y-6 text-left lg:col-span-7">
                <Reveal>
                  {/* Main Headline */}
                  <h1 className="font-heading text-3xl leading-[1.15] font-extrabold tracking-tight text-slate-900 transition-colors sm:text-5xl lg:text-6xl dark:text-slate-50">
                    Unify Your Entire{" "}
                    <span className="text-[#99753a]">School Ecosystem</span> in
                    One Smart Platform
                  </h1>

                  {/* Readable Sub-copy with Increased Leading and Font-Size */}
                  <p className="mt-5 max-w-2xl text-lg leading-relaxed font-normal text-slate-600 transition-colors sm:text-xl dark:text-slate-300">
                    Seamlessly connect Principals, Teachers, Students, and
                    Parents through a unified, reliable workspace. Manage
                    attendance, grading, fee pipelines, and real-time alerts
                    with complete operational clarity.
                  </p>

                  {/* CTA Button Cluster: Clear Hierarchy */}
                  <div className="flex flex-wrap items-center gap-4 pt-6">
                    {/* Primary CTA: Solid background, high contrast, definitive action */}
                    <a
                      className="group flex items-center justify-center gap-2.5 rounded-xl bg-[#99753a] px-8 py-4 text-base font-bold text-white shadow-md shadow-[#99753a]/25 transition-all hover:-translate-y-0.5 hover:bg-[#85632f] active:scale-[0.99] dark:shadow-xl dark:shadow-black/40"
                      href={APP_AUTH_URL}
                    >
                      <span>Get started free</span>
                      <ArrowRight
                        className="transition-transform group-hover:translate-x-1"
                        size={18}
                      />
                    </a>

                    {/* Secondary CTA: Ghost button with subtle outline */}
                    <a
                      className="flex items-center justify-center gap-2 rounded-xl border border-slate-300 bg-white/80 px-6 py-4 text-base font-semibold text-slate-700 transition-all hover:-translate-y-0.5 hover:bg-slate-100 dark:border-white/10 dark:bg-[#1C294A] dark:text-slate-200 dark:hover:bg-[#22335C]"
                      href="#modules"
                    >
                      <span>Explore features</span>
                      <Sliders
                        className="text-slate-500 dark:text-slate-400"
                        size={18}
                      />
                    </a>

                    {/* Tertiary Action: Low friction simple text link */}
                    <a
                      className="flex items-center gap-1.5 px-3 py-4 text-sm font-semibold text-slate-600 transition-colors hover:text-[#99753a] hover:underline dark:text-slate-300 dark:hover:text-[#99753a]"
                      href="#calculator"
                    >
                      <Calculator
                        className="text-slate-500 dark:text-slate-400"
                        size={16}
                      />
                      <span>Calculate campus ROI</span>
                    </a>
                  </div>
                </Reveal>
              </div>

              <HeroShowcase />
            </div>
          </div>

          {/* Live Campus Trust Stats Grid */}
          <Reveal delay={80} className="mx-auto max-w-5xl">
            <div className="grid grid-cols-2 gap-4 sm:gap-6 md:grid-cols-4">
              {STATS.map((s) => (
                <div
                  key={s.label}
                  className="group cursor-default rounded-2xl border border-slate-200/80 bg-white p-6 text-center shadow-sm transition-all duration-300 hover:-translate-y-1 hover:shadow-md sm:p-8 dark:border-white/5 dark:bg-[#131E3A] dark:shadow-lg dark:shadow-black/30 dark:hover:shadow-black/50"
                >
                  <Counter value={s.value} />
                  <p className="mt-1 text-xs font-medium text-slate-600 sm:text-sm dark:text-slate-400">
                    {s.label}
                  </p>
                </div>
              ))}
            </div>
          </Reveal>
        </div>
      </section>

      {/* Dedicated Social Proof Logo Ticker Section */}
      <section
        className="ticker-frame w-full border-y border-slate-200/80 bg-white py-7 transition-colors sm:py-9 dark:border-white/5 dark:bg-[#0D1527]"
        role="region"
        aria-label="Partner schools and security accreditation"
      >
        <div className="mx-auto max-w-7xl px-4 sm:px-6">
          <p className="font-heading mb-5 text-center text-xs font-bold tracking-wider text-slate-500 uppercase dark:text-slate-400">
            Trusted by 500+ Leading Schools &amp; Campuses Nationwide
          </p>

          <div className="ticker-viewport">
            <div className="ticker-move text-sm font-medium text-slate-700 sm:text-base dark:text-slate-300">
              {/* Two identical groups for seamless -50% infinite translation */}
              {[0, 1].map((copy) => (
                <div
                  key={copy}
                  className="ticker-group flex items-center gap-7 sm:gap-9"
                  aria-hidden={copy === 1 ? "true" : undefined}
                >
                  {/* ISO 27001 Certified Chip */}
                  <span className="inline-flex shrink-0 items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-3.5 py-1.5 text-xs font-bold text-emerald-800 shadow-xs dark:border-emerald-500/20 dark:bg-[#1C294A] dark:text-emerald-300/80">
                    <Shield
                      className="text-emerald-600/80 dark:text-emerald-400/80"
                      size={15}
                    />
                    <span>ISO 27001 Certified</span>
                  </span>

                  {/* 99.9% Uptime Chip */}
                  <span className="inline-flex shrink-0 items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-3.5 py-1.5 text-xs font-bold text-slate-800 shadow-xs dark:border-white/10 dark:bg-[#1C294A] dark:text-slate-200">
                    <span className="h-2 w-2 animate-pulse rounded-full bg-emerald-500/80" />
                    <span>99.9% SLA Guaranteed</span>
                  </span>

                  {SCHOOLS.map((school) => (
                    <span
                      key={school}
                      className="flex shrink-0 items-center gap-2.5 text-sm font-semibold text-slate-700 sm:text-base dark:text-slate-200"
                    >
                      <span
                        className="text-xs font-bold text-[#99753a]"
                        aria-hidden="true"
                      >
                        ◆
                      </span>
                      {school}
                    </span>
                  ))}
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Section: Role-Based Architecture */}
      <section
        className="mx-auto max-w-7xl border-t border-slate-200/80 px-4 py-20 transition-colors sm:py-24 md:px-8 dark:border-white/5"
        id="roles"
      >
        <Reveal className="mx-auto mb-12 max-w-3xl text-center sm:mb-16">
          <span className="rounded-full border border-[#99753a]/25 bg-[#99753a]/10 px-3.5 py-1.5 text-xs font-semibold tracking-wider text-[#99753a] uppercase dark:border-[#99753a]/30 dark:bg-[#99753a]/15 dark:text-[#99753a]">
            Role-Specific Workspaces
          </span>
          <h2 className="font-heading mt-3 mb-4 text-3xl font-extrabold tracking-tight text-slate-900 sm:text-4xl dark:text-slate-50">
            Engineered for Every Stakeholder in Your Ecosystem
          </h2>
          <p className="text-base leading-relaxed text-slate-600 sm:text-lg dark:text-slate-300">
            EduConnect replaces disjointed spreadsheets and standalone apps with
            role-tailored workspaces designed for maximum focus and zero
            operational clutter.
          </p>
        </Reveal>

        <div className="grid grid-cols-1 items-stretch gap-6 md:grid-cols-2 lg:grid-cols-3 lg:gap-8">
          {/* Role 1: Administrators & Principals */}
          <Reveal delay={0} className="h-full">
            <TiltCard className="group flex h-full flex-col justify-between rounded-3xl border border-slate-200 bg-white p-6 shadow-lg shadow-slate-200/50 transition-all duration-300 hover:-translate-y-1 hover:shadow-xl sm:p-8 dark:border-white/5 dark:bg-[#1C294A] dark:shadow-black/40 hover:dark:shadow-black/60">
              <div>
                <div className="mb-6 flex items-center justify-between">
                  <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-[#99753a]/20 bg-[#99753a]/10 text-[#99753a] shadow-sm transition-transform group-hover:scale-105 dark:border-white/5 dark:bg-[#131E3A]">
                    <Shield size={26} />
                  </div>
                  <span className="rounded-full border border-slate-200 bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700 dark:border-white/5 dark:bg-[#131E3A] dark:text-slate-300">
                    ERP Command
                  </span>
                </div>
                <h3 className="font-heading mb-2 text-2xl font-bold text-slate-900 dark:text-slate-50">
                  Administrators &amp; Principals
                </h3>
                <p className="mb-6 text-sm leading-relaxed text-slate-600 dark:text-slate-300">
                  Complete real-time visibility across school fee collections,
                  student admissions pipeline, and audit-ready institutional
                  reports.
                </p>

                <div className="mb-6 space-y-3.5 rounded-2xl border border-slate-200/80 bg-slate-50/90 p-5 shadow-xs sm:p-6 dark:border-white/5 dark:bg-[#131E3A]">
                  <div className="flex items-center justify-between border-b border-slate-200 pb-2 text-xs dark:border-white/5">
                    <span className="font-semibold text-slate-800 dark:text-slate-200">
                      Fee Collection Progress (Q2)
                    </span>
                    <span className="font-bold text-[#99753a]">94.2%</span>
                  </div>
                  <div className="h-2 w-full overflow-hidden rounded-full bg-slate-200 dark:bg-slate-800">
                    <div
                      className="h-full rounded-full bg-[#99753a] transition-all duration-1000"
                      style={{ width: "94%" }}
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-2.5 pt-1 text-xs">
                    <div className="rounded-lg border border-slate-100 bg-white p-2.5 dark:border-white/5 dark:bg-[#1C294A]">
                      <p className="text-[11px] text-slate-500 dark:text-slate-400">
                        Total Invoiced
                      </p>
                      <p className="font-bold text-slate-900 dark:text-slate-50">
                        ₹78.2 Lakhs
                      </p>
                    </div>
                    <div className="rounded-lg border border-slate-100 bg-white p-2.5 dark:border-white/5 dark:bg-[#1C294A]">
                      <p className="text-[11px] text-slate-500 dark:text-slate-400">
                        Admissions Goal
                      </p>
                      <p className="font-bold text-slate-900 dark:text-slate-50">
                        420 / 400 (105%)
                      </p>
                    </div>
                  </div>
                </div>
              </div>
              <div className="flex items-center justify-between border-t border-slate-200/80 pt-4 text-sm font-semibold text-[#99753a] transition-transform group-hover:translate-x-1 dark:border-white/5">
                <span>Explore Principal Hub</span>
                <ArrowRight size={18} />
              </div>
            </TiltCard>
          </Reveal>

          {/* Role 2: Teachers & Instructors */}
          <Reveal delay={100} className="h-full">
            <TiltCard className="group flex h-full flex-col justify-between rounded-3xl border border-slate-200 bg-white p-6 shadow-lg shadow-slate-200/50 transition-all duration-300 hover:-translate-y-1 hover:shadow-xl sm:p-8 dark:border-white/5 dark:bg-[#1C294A] dark:shadow-black/40 hover:dark:shadow-black/60">
              <div>
                <div className="mb-6 flex items-center justify-between">
                  <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-[#99753a]/20 bg-[#99753a]/10 text-[#99753a] shadow-sm transition-transform group-hover:scale-105 dark:border-white/5 dark:bg-[#131E3A]">
                    <CheckCircle size={26} />
                  </div>
                  <span className="rounded-full border border-[#99753a]/25 bg-[#99753a]/10 px-3 py-1 text-xs font-semibold text-[#99753a] dark:border-[#99753a]/30 dark:bg-[#99753a]/15 dark:text-[#99753a]">
                    Classroom OS
                  </span>
                </div>
                <h3 className="font-heading mb-2 text-2xl font-bold text-slate-900 dark:text-slate-50">
                  Teachers &amp; Instructors
                </h3>
                <p className="mb-6 text-sm leading-relaxed text-slate-600 dark:text-slate-300">
                  Streamlined workflows for daily assignments, AI-assisted
                  grading, period attendance logs, and synchronized exam
                  calendars.
                </p>

                <div className="mb-6 space-y-3.5 rounded-2xl border border-slate-200/80 bg-slate-50/90 p-5 shadow-xs sm:p-6 dark:border-white/5 dark:bg-[#131E3A]">
                  <div className="flex items-center justify-between border-b border-slate-200 pb-2 text-xs dark:border-white/5">
                    <span className="font-semibold text-slate-800 dark:text-slate-200">
                      Assignments Pending Review
                    </span>
                    <span className="rounded bg-[#99753a]/10 px-2 py-0.5 text-[11px] font-semibold text-[#99753a]">
                      4 to grade
                    </span>
                  </div>
                  <div className="space-y-2 text-xs">
                    <div className="flex items-center justify-between rounded-lg border border-slate-100 bg-white p-2.5 dark:border-white/5 dark:bg-[#1C294A]">
                      <span className="truncate font-medium text-slate-800 dark:text-slate-200">
                        Physics Lab - Optics (10-B)
                      </span>
                      <span className="flex shrink-0 items-center gap-1 font-bold text-emerald-700/80 dark:text-emerald-300/80">
                        AI Graded{" "}
                        <CheckCircle
                          className="text-emerald-600/80 dark:text-emerald-400/80"
                          size={14}
                        />
                      </span>
                    </div>
                    <div className="flex items-center justify-between rounded-lg border border-slate-100 bg-white p-2.5 dark:border-white/5 dark:bg-[#1C294A]">
                      <span className="truncate font-medium text-slate-800 dark:text-slate-200">
                        English Essay (9-A)
                      </span>
                      <span className="shrink-0 font-semibold text-slate-600 dark:text-slate-400">
                        34 / 36 Submitted
                      </span>
                    </div>
                  </div>
                </div>
              </div>
              <div className="flex items-center justify-between border-t border-slate-200/80 pt-4 text-sm font-semibold text-[#99753a] transition-transform group-hover:translate-x-1 dark:border-white/5">
                <span>Explore Instructor Suite</span>
                <ArrowRight size={18} />
              </div>
            </TiltCard>
          </Reveal>

          {/* Role 3: Students & Parents */}
          <Reveal delay={200} className="h-full">
            <TiltCard className="group flex h-full flex-col justify-between rounded-3xl border border-slate-200 bg-white p-6 shadow-lg shadow-slate-200/50 transition-all duration-300 hover:-translate-y-1 hover:shadow-xl sm:p-8 dark:border-white/5 dark:bg-[#1C294A] dark:shadow-black/40 hover:dark:shadow-black/60">
              <div>
                <div className="mb-6 flex items-center justify-between">
                  <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-[#99753a]/20 bg-[#99753a]/10 text-[#99753a] shadow-sm transition-transform group-hover:scale-105 dark:border-white/5 dark:bg-[#131E3A]">
                    <Users size={26} />
                  </div>
                  <span className="rounded-full border border-slate-200 bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700 dark:border-white/5 dark:bg-[#131E3A] dark:text-slate-300">
                    Parent &amp; Student
                  </span>
                </div>
                <h3 className="font-heading mb-2 text-2xl font-bold text-slate-900 dark:text-slate-50">
                  Students &amp; Parents
                </h3>
                <p className="mb-6 text-sm leading-relaxed text-slate-600 dark:text-slate-300">
                  Unified family portal for academic progress tracking,
                  timetable notifications, one-click online fee receipts, and
                  teacher communications.
                </p>

                <div className="mb-6 space-y-3.5 rounded-2xl border border-slate-200/80 bg-slate-50/90 p-5 shadow-xs sm:p-6 dark:border-white/5 dark:bg-[#131E3A]">
                  <div className="flex items-center justify-between border-b border-slate-200 pb-2 text-xs dark:border-white/5">
                    <span className="font-semibold text-slate-800 dark:text-slate-200">
                      Student: Aarav Sharma (Grade 8)
                    </span>
                    <span className="text-[11px] font-medium text-slate-600 dark:text-slate-400">
                      Next: Math @ 10:15 AM
                    </span>
                  </div>
                  <div className="flex items-center justify-between rounded-lg border border-slate-100 bg-white p-2.5 text-xs dark:border-white/5 dark:bg-[#1C294A]">
                    <span className="text-slate-600 dark:text-slate-400">
                      Teacher Mrs. Roy:
                    </span>
                    <span className="font-semibold text-slate-800 dark:text-slate-200">
                      &ldquo;Great progress today!&rdquo;
                    </span>
                  </div>
                  <div className="flex items-center justify-between pt-1 text-[11px] text-slate-600 dark:text-slate-400">
                    <span>Bus #12 Live: 4 mins away</span>
                    <span className="flex items-center gap-1.5 font-semibold text-emerald-700/80 dark:text-emerald-300/80">
                      <span className="h-2 w-2 rounded-full bg-emerald-500/80" />{" "}
                      On Route
                    </span>
                  </div>
                </div>
              </div>
              <div className="flex items-center justify-between border-t border-slate-200/80 pt-4 text-sm font-semibold text-[#99753a] transition-transform group-hover:translate-x-1 dark:border-white/5">
                <span>Explore Family Portal</span>
                <ArrowRight size={18} />
              </div>
            </TiltCard>
          </Reveal>
        </div>
      </section>

      {/* Section: Intelligent Toolkit Modules (Bento Grid) */}
      <section
        className="mx-auto max-w-7xl px-4 py-20 sm:px-6 sm:py-24"
        id="modules"
      >
        <Reveal className="mx-auto mb-12 max-w-2xl text-center sm:mb-16">
          <span className="rounded-full border border-[#99753a]/25 bg-[#99753a]/10 px-3.5 py-1.5 text-xs font-semibold tracking-wider text-[#99753a] uppercase dark:border-[#99753a]/30 dark:bg-[#99753a]/15 dark:text-[#99753a]">
            Campus Modules
          </span>
          <h2 className="font-heading mt-3 mb-4 text-3xl font-extrabold text-slate-900 sm:text-4xl dark:text-slate-50">
            A Unified Toolkit for the Modern Campus
          </h2>
          <p className="text-base leading-relaxed text-slate-600 sm:text-lg dark:text-slate-300">
            Everything you need to run a physical school, seamlessly integrated
            and powered by intelligent automation.
          </p>
        </Reveal>

        {/* Bento Grid */}
        <div className="grid grid-cols-1 gap-6 sm:gap-8 md:grid-cols-3">
          {/* Bento 1: Flagship AI Copilot */}
          <Reveal delay={0} className="h-full md:col-span-2">
            <AiCopilotModule className="h-full" />
          </Reveal>

          {/* Bento 2: Smart Attendance */}
          <Reveal delay={100} className="h-full">
            <TiltCard className="group flex h-full flex-col justify-between rounded-3xl border border-slate-200/80 bg-white/95 p-8 shadow-md shadow-slate-200/50 transition-all hover:-translate-y-1 hover:shadow-2xl sm:p-10 dark:border-white/5 dark:bg-[#1C294A] dark:shadow-xl dark:shadow-black/40 hover:dark:shadow-black/60">
              <div>
                <div className="mb-6 flex h-12 w-12 items-center justify-center rounded-2xl border border-[#99753a]/20 bg-[#99753a]/10 text-[#99753a] transition-transform group-hover:scale-105 dark:border-white/5 dark:bg-[#131E3A]">
                  <CheckCircle size={24} />
                </div>
                <h3 className="font-heading mb-3 text-2xl font-bold text-slate-900 dark:text-slate-50">
                  Smart Attendance
                </h3>
                <p className="mb-6 leading-relaxed text-slate-600 dark:text-slate-300">
                  Frictionless tracking for physical classrooms with automated
                  anomaly detection for absenteeism.
                </p>
              </div>
              <div className="flex items-center gap-3 rounded-xl border border-slate-200/70 bg-slate-50/80 p-3.5 dark:border-white/5 dark:bg-[#131E3A]">
                <span className="h-2.5 w-2.5 rounded-full bg-[#99753a]" />
                <span className="text-xs font-medium text-slate-700 dark:text-slate-300">
                  Auto-SMS sent for 3 absences today
                </span>
              </div>
            </TiltCard>
          </Reveal>

          {/* Bento 3: Deep Analytics */}
          <Reveal delay={200} className="h-full">
            <TiltCard className="group flex h-full flex-col justify-between rounded-3xl border border-slate-200/80 bg-white/95 p-8 shadow-md shadow-slate-200/50 transition-all hover:-translate-y-1 hover:shadow-2xl sm:p-10 dark:border-white/5 dark:bg-[#1C294A] dark:shadow-xl dark:shadow-black/40 hover:dark:shadow-black/60">
              <div>
                <div className="mb-6 flex h-12 w-12 items-center justify-center rounded-2xl border border-[#99753a]/20 bg-[#99753a]/10 text-[#99753a] transition-transform group-hover:scale-105 dark:border-white/5 dark:bg-[#131E3A]">
                  <TrendingUp size={24} />
                </div>
                <h3 className="font-heading mb-3 text-2xl font-bold text-slate-900 dark:text-slate-50">
                  Deep Analytics
                </h3>
                <p className="mb-6 leading-relaxed text-slate-600 dark:text-slate-300">
                  Transform data into action. Gain comprehensive insights into
                  academic performance and operational efficiency.
                </p>
              </div>
              <div className="flex cursor-pointer items-center justify-between rounded-xl border border-slate-200/70 bg-slate-50/80 p-3.5 dark:border-white/5 dark:bg-[#131E3A]">
                <span className="text-xs font-medium text-slate-700 dark:text-slate-300">
                  CBSE / ICSE format ready
                </span>
                <Download
                  className="text-slate-700 transition-transform group-hover:translate-y-0.5 dark:text-slate-300"
                  size={18}
                />
              </div>
            </TiltCard>
          </Reveal>

          {/* Bento 4: Transparent Fees */}
          <Reveal delay={300} className="h-full">
            <TiltCard className="group flex h-full flex-col justify-between rounded-3xl border border-slate-200/80 bg-white/95 p-8 shadow-md shadow-slate-200/50 transition-all hover:-translate-y-1 hover:shadow-2xl sm:p-10 dark:border-white/5 dark:bg-[#1C294A] dark:shadow-xl dark:shadow-black/40 hover:dark:shadow-black/60">
              <div>
                <div className="mb-6 flex h-12 w-12 items-center justify-center rounded-2xl border border-[#99753a]/20 bg-[#99753a]/10 text-[#99753a] transition-transform group-hover:scale-105 dark:border-white/5 dark:bg-[#131E3A]">
                  <Award size={24} />
                </div>
                <h3 className="font-heading mb-3 text-2xl font-bold text-slate-900 dark:text-slate-50">
                  Transparent Fees
                </h3>
                <p className="mb-6 leading-relaxed text-slate-600 dark:text-slate-300">
                  Online payments, instant receipts and live dues tracking — no
                  more ledger registers.
                </p>
              </div>
              <div className="flex items-center justify-between rounded-xl border border-slate-200/70 bg-slate-50/80 p-3.5 dark:border-white/5 dark:bg-[#131E3A]">
                <span className="text-xs font-semibold text-slate-800 dark:text-slate-200">
                  Zero manual reconciliation
                </span>
                <CheckCircle className="text-[#99753a]" size={18} />
              </div>
            </TiltCard>
          </Reveal>

          {/* Bento 5: Unified Comms */}
          <Reveal delay={400} className="h-full">
            <TiltCard className="group flex h-full flex-col justify-between rounded-3xl border border-slate-200/80 bg-white/95 p-8 shadow-md shadow-slate-200/50 transition-all hover:-translate-y-1 hover:shadow-2xl sm:p-10 dark:border-white/5 dark:bg-[#1C294A] dark:shadow-xl dark:shadow-black/40 hover:dark:shadow-black/60">
              <div>
                <div className="mb-6 flex h-12 w-12 items-center justify-center rounded-2xl border border-[#99753a]/20 bg-[#99753a]/10 text-[#99753a] transition-transform group-hover:scale-105 dark:border-white/5 dark:bg-[#131E3A]">
                  <Lock size={24} />
                </div>
                <h3 className="font-heading mb-3 text-2xl font-bold text-slate-900 dark:text-slate-50">
                  Unified Comms
                </h3>
                <p className="mb-6 leading-relaxed text-slate-600 dark:text-slate-300">
                  Secure, real-time messaging connecting teachers, parents, and
                  students in one centralized hub.
                </p>
              </div>
              <div className="flex items-center gap-2.5 rounded-xl border border-slate-200/70 bg-slate-50/80 p-3.5 dark:border-white/5 dark:bg-[#131E3A]">
                <Lock className="text-[#99753a]" size={16} />
                <span className="text-xs font-medium text-slate-700 dark:text-slate-300">
                  Encrypted verified school channels
                </span>
              </div>
            </TiltCard>
          </Reveal>
        </div>
      </section>

      {/* Section: Campus ROI Calculator */}
      <RoiCalculator />

      {/* Section: Transparent Pricing */}
      <PricingSection />

      {/* Section: Implementation & Testimonials */}
      <section
        className="mx-auto max-w-7xl border-t border-slate-200/80 px-4 py-20 transition-colors sm:px-6 sm:py-24 dark:border-white/5"
        id="how-it-works"
      >
        <Reveal className="mx-auto mb-12 max-w-2xl text-center sm:mb-16">
          <span className="rounded-full border border-[#99753a]/25 bg-[#99753a]/10 px-3.5 py-1.5 text-xs font-semibold tracking-wider text-[#99753a] uppercase dark:border-[#99753a]/30 dark:bg-[#99753a]/15 dark:text-[#99753a]">
            Verified Institutional Proof
          </span>
          <h2 className="font-heading mt-3 mb-4 text-3xl font-extrabold tracking-tight text-slate-900 sm:text-4xl dark:text-slate-50">
            Trusted by Leading Educational Leaders
          </h2>
          <p className="text-base leading-relaxed text-slate-600 sm:text-lg dark:text-slate-300">
            Hear directly from school directors, principals, and IT coordinators
            on their transition to EduConnect.
          </p>
        </Reveal>

        <div className="grid grid-cols-1 gap-8 md:grid-cols-3">
          {/* Quote 1: Meera Nair */}
          <Reveal delay={0} className="h-full">
            <div className="flex h-full flex-col justify-between rounded-3xl border border-slate-200/80 bg-white/95 p-8 shadow-md shadow-slate-200/50 transition-all duration-300 hover:-translate-y-1 hover:shadow-2xl sm:p-10 dark:border-white/5 dark:bg-[#1C294A] dark:shadow-xl dark:shadow-black/40 hover:dark:shadow-black/60">
              <div>
                <div className="mb-5 flex items-center justify-between">
                  <div className="flex gap-0.5 text-[#99753a]">
                    {[...Array(5)].map((_, i) => (
                      <Star key={i} fill="currentColor" size={18} />
                    ))}
                  </div>
                  <span className="rounded-full border border-[#99753a]/25 bg-[#99753a]/10 px-2.5 py-0.5 text-xs font-semibold text-[#99753a] dark:border-[#99753a]/30 dark:bg-[#99753a]/15 dark:text-[#99753a]">
                    Verified Director
                  </span>
                </div>
                <p className="mb-6 text-sm leading-relaxed font-normal text-slate-700 italic dark:text-slate-300">
                  “Fee collection is fully transparent now — receipts, dues and
                  automated reminders run themselves. Our finance office
                  workload literally dropped by half within 30 days.”
                </p>
              </div>
              <div className="flex items-center gap-3 border-t border-slate-100 pt-5 dark:border-white/5">
                <div className="flex h-11 w-11 items-center justify-center rounded-full bg-[#99753a] text-sm font-bold text-white shadow-sm dark:border dark:border-[#99753a]/30 dark:bg-[#131E3A] dark:text-[#99753a]">
                  MN
                </div>
                <div>
                  <p className="text-sm font-bold text-slate-900 dark:text-slate-50">
                    Meera Nair
                  </p>
                  <p className="text-xs font-medium text-slate-600 dark:text-slate-400">
                    Director · Sunrise Public School (1,850 Students)
                  </p>
                </div>
              </div>
            </div>
          </Reveal>

          {/* Quote 2: Rajesh Iyer */}
          <Reveal delay={100} className="h-full">
            <div className="flex h-full flex-col justify-between rounded-3xl border border-slate-200/80 bg-white/95 p-8 shadow-md shadow-slate-200/50 transition-all duration-300 hover:-translate-y-1 hover:shadow-2xl sm:p-10 dark:border-white/5 dark:bg-[#1C294A] dark:shadow-xl dark:shadow-black/40 hover:dark:shadow-black/60">
              <div>
                <div className="mb-5 flex items-center justify-between">
                  <div className="flex gap-0.5 text-[#99753a]">
                    {[...Array(5)].map((_, i) => (
                      <Star key={i} fill="currentColor" size={18} />
                    ))}
                  </div>
                  <span className="rounded-full border border-[#99753a]/25 bg-[#99753a]/10 px-2.5 py-0.5 text-xs font-semibold text-[#99753a] dark:border-[#99753a]/30 dark:bg-[#99753a]/15 dark:text-[#99753a]">
                    Verified Principal
                  </span>
                </div>
                <p className="mb-6 text-sm leading-relaxed font-normal text-slate-700 italic dark:text-slate-300">
                  “From attendance to report cards on one unified screen. My
                  teachers finally spend their energy mentoring students instead
                  of wrestling with paper log registers and spreadsheets.”
                </p>
              </div>
              <div className="flex items-center gap-3 border-t border-slate-100 pt-5 dark:border-white/5">
                <div className="flex h-11 w-11 items-center justify-center rounded-full bg-[#99753a] text-sm font-bold text-white shadow-sm dark:border dark:border-[#99753a]/30 dark:bg-[#131E3A] dark:text-[#99753a]">
                  RI
                </div>
                <div>
                  <p className="text-sm font-bold text-slate-900 dark:text-slate-50">
                    Rajesh Iyer
                  </p>
                  <p className="text-xs font-medium text-slate-600 dark:text-slate-400">
                    Principal · Green Valley International Academy
                  </p>
                </div>
              </div>
            </div>
          </Reveal>

          {/* Quote 3: Dr. Anita Sharma */}
          <Reveal delay={200} className="h-full">
            <div className="flex h-full flex-col justify-between rounded-3xl border border-slate-200/80 bg-white/95 p-8 shadow-md shadow-slate-200/50 transition-all duration-300 hover:-translate-y-1 hover:shadow-2xl sm:p-10 dark:border-white/5 dark:bg-[#1C294A] dark:shadow-xl dark:shadow-black/40 hover:dark:shadow-black/60">
              <div>
                <div className="mb-5 flex items-center justify-between">
                  <div className="flex gap-0.5 text-[#99753a]">
                    {[...Array(5)].map((_, i) => (
                      <Star key={i} fill="currentColor" size={18} />
                    ))}
                  </div>
                  <span className="rounded-full border border-[#99753a]/25 bg-[#99753a]/10 px-2.5 py-0.5 text-xs font-semibold text-[#99753a] dark:border-[#99753a]/30 dark:bg-[#99753a]/15 dark:text-[#99753a]">
                    Verified Faculty Head
                  </span>
                </div>
                <p className="mb-6 text-sm leading-relaxed font-normal text-slate-700 italic dark:text-slate-300">
                  “Parents message directly through verified channels and
                  receive timely answers. The built-in AI Copilot drafts our
                  routine parent communications flawlessly and securely.”
                </p>
              </div>
              <div className="flex items-center gap-3 border-t border-slate-100 pt-5 dark:border-white/5">
                <div className="flex h-11 w-11 items-center justify-center rounded-full bg-[#99753a] text-sm font-bold text-white shadow-sm dark:border dark:border-[#99753a]/30 dark:bg-[#131E3A] dark:text-[#99753a]">
                  AS
                </div>
                <div>
                  <p className="text-sm font-bold text-slate-900 dark:text-slate-50">
                    Dr. Anita Sharma
                  </p>
                  <p className="text-xs font-medium text-slate-600 dark:text-slate-400">
                    Academic Dean · St. Xavier High School
                  </p>
                </div>
              </div>
            </div>
          </Reveal>
        </div>
      </section>

      {/* Section: Frequently Asked Questions */}
      <FaqSection />

      {/* Section: High-Conversion CTA Block */}
      <section className="mx-auto max-w-7xl px-4 py-16 sm:px-6 sm:py-20">
        <Reveal>
          <div className="relative overflow-hidden rounded-3xl border border-slate-800 bg-gradient-to-br from-slate-900 to-[#131E3A] p-10 text-center text-white shadow-2xl sm:p-16 dark:border-white/10 dark:from-[#131E3A] dark:to-[#0B1221] dark:shadow-black/60">
            <div className="relative z-10 mx-auto max-w-2xl space-y-4">
              <h2 className="font-heading text-3xl font-extrabold tracking-tight text-white sm:text-4xl dark:text-slate-50">
                Ready to run your school on autopilot?
              </h2>
              <p className="mx-auto max-w-xl text-base leading-relaxed text-slate-300 sm:text-lg">
                Join 500+ schools automating attendance, fees, and communication
                with EduConnect.
              </p>
              <div className="flex flex-col items-center justify-center gap-4 pt-4 sm:flex-row">
                {/* Primary Action */}
                <a
                  className="w-full rounded-xl bg-[#99753a] px-8 py-4 text-base font-bold text-white shadow-lg shadow-[#99753a]/30 transition-all hover:-translate-y-0.5 hover:bg-[#85632f] active:scale-[0.99] sm:w-auto dark:shadow-xl dark:shadow-black/40"
                  href={APP_AUTH_URL}
                >
                  Get started free
                </a>
                {/* Ghost / Secondary Action */}
                <a
                  className="w-full rounded-xl border border-white/20 bg-white/10 px-8 py-4 text-base font-semibold text-white transition-all hover:-translate-y-0.5 hover:bg-white/15 sm:w-auto dark:border-white/10 dark:bg-white/5 dark:text-slate-200 dark:hover:bg-white/10"
                  href="#modules"
                >
                  Explore modules
                </a>
              </div>
            </div>
          </div>
        </Reveal>
      </section>

      {/* Section: About EduConnect */}
      <section
        className="mx-auto max-w-7xl border-t border-slate-200/80 px-4 py-20 transition-colors sm:px-6 sm:py-24 dark:border-white/5"
        id="about"
      >
        <div className="grid grid-cols-1 items-center gap-12 lg:grid-cols-12">
          <Reveal className="space-y-5 lg:col-span-6">
            <span className="rounded-full border border-[#99753a]/25 bg-[#99753a]/10 px-3.5 py-1.5 text-xs font-semibold tracking-wider text-[#99753a] uppercase dark:border-[#99753a]/30 dark:bg-[#99753a]/15 dark:text-[#99753a]">
              About The Platform
            </span>
            <h2 className="font-heading text-3xl font-bold text-slate-900 sm:text-4xl dark:text-slate-50">
              About EduConnect
            </h2>
            <p className="text-base leading-relaxed text-slate-700 sm:text-lg dark:text-slate-300">
              EduConnect is a{" "}
              <strong className="font-semibold text-slate-900 dark:text-slate-50">
                school operating system
              </strong>{" "}
              — it automates the complete operational workflow of a physical
              campus in one secure platform.
            </p>
            <ul className="space-y-3.5 text-sm leading-relaxed text-slate-600 sm:text-base dark:text-slate-300">
              {ABOUT_POINTS.map((point) => (
                <li key={point} className="flex items-start gap-3">
                  <CheckCircle
                    className="mt-0.5 shrink-0 text-[#99753a]"
                    size={20}
                  />
                  <span className="text-slate-700 dark:text-slate-300">
                    {point}
                  </span>
                </li>
              ))}
            </ul>
          </Reveal>
          <Reveal delay={100} className="lg:col-span-6">
            <div className="space-y-6 rounded-3xl border border-slate-200/80 bg-white/95 p-8 shadow-xl shadow-slate-200/50 sm:p-10 dark:border-white/5 dark:bg-[#1C294A] dark:shadow-2xl dark:shadow-black/40">
              <div className="flex items-center gap-3.5">
                <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-[#99753a]/20 bg-[#99753a]/10 text-[#99753a] shadow-sm dark:border-white/5 dark:bg-[#131E3A]">
                  <Shield size={22} />
                </div>
                <div>
                  <h4 className="font-heading text-lg font-bold text-slate-900 dark:text-slate-50">
                    Zero-paperwork operations
                  </h4>
                  <p className="text-xs font-medium text-slate-500 dark:text-slate-400">
                    Engineered for physical schools
                  </p>
                </div>
              </div>
              <p className="text-sm leading-relaxed text-slate-600 dark:text-slate-300">
                Transform manual physical paperwork into unified digital state
                machines. From morning bus telemetry to evening parent
                communication, EduConnect guarantees zero data loss and
                automated regulatory compliance.
              </p>
              <div className="grid grid-cols-1 gap-4 pt-2 sm:grid-cols-2">
                <div className="rounded-xl border border-slate-200/70 bg-slate-50 p-4 dark:border-white/5 dark:bg-[#131E3A]">
                  <span className="mb-1 block text-xs text-slate-500 dark:text-slate-400">
                    Direct Contact
                  </span>
                  <a
                    className="text-xs font-semibold text-slate-900 transition-colors hover:text-[#99753a] dark:text-slate-200 dark:hover:text-[#99753a]"
                    href="mailto:hello@educonnect.school"
                  >
                    hello@educonnect.school
                  </a>
                </div>
                <div className="rounded-xl border border-slate-200/70 bg-slate-50 p-4 dark:border-white/5 dark:bg-[#131E3A]">
                  <span className="mb-1 block text-xs text-slate-500 dark:text-slate-400">
                    Campus Hotline
                  </span>
                  <a
                    className="text-xs font-semibold text-slate-900 transition-colors hover:text-[#99753a] dark:text-slate-200 dark:hover:text-[#99753a]"
                    href="tel:+919876543210"
                  >
                    +91 98765 43210
                  </a>
                </div>
              </div>
            </div>
          </Reveal>
        </div>
      </section>

      <Footer />
    </div>
  );
}
