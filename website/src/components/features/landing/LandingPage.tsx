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
import ParticleField from "./ParticleField";
import TiltCard from "./TiltCard";
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
        <p ref={ref} className="text-3xl sm:text-4xl font-extrabold text-slate-900 dark:text-white mb-1 font-heading group-hover:scale-105 transition-transform">
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
        <div className="relative min-h-screen bg-[#F8FAFF] dark:bg-[#070B14] text-slate-900 dark:text-white transition-colors duration-300 overflow-x-hidden selection:bg-blue-600 selection:text-white">
            {/* Dynamic Living Ambient Gradient Orbs & Shimmering Mesh */}
            <div className="fixed inset-0 pointer-events-none -z-10 overflow-hidden">
                <div
                    className="absolute -top-40 left-1/4 w-[820px] h-[820px] rounded-full blur-[130px] pointer-events-none opacity-55 dark:opacity-35 transition-opacity duration-300 animate-ambient-1"
                    style={{
                        background:
                            "radial-gradient(circle, rgba(37, 99, 235, 0.55) 0%, rgba(99, 102, 241, 0.4) 45%, transparent 75%)",
                    }}
                />
                <div
                    className="absolute top-20 right-10 w-[640px] h-[640px] rounded-full blur-[120px] pointer-events-none opacity-45 dark:opacity-30 transition-opacity duration-300 animate-ambient-2 animate-aurora"
                    style={{
                        background:
                            "radial-gradient(circle, rgba(6, 182, 212, 0.5) 0%, rgba(56, 189, 248, 0.35) 50%, transparent 75%)",
                    }}
                />
                <div
                    className="absolute top-1/3 -left-32 w-[720px] h-[720px] rounded-full blur-[140px] pointer-events-none opacity-45 dark:opacity-25 transition-opacity duration-300 animate-ambient-3"
                    style={{
                        background:
                            "radial-gradient(circle, rgba(99, 102, 241, 0.45) 0%, rgba(56, 189, 248, 0.35) 50%, transparent 75%)",
                    }}
                />
                <div
                    className="absolute bottom-32 left-1/3 w-[680px] h-[680px] rounded-full blur-[130px] pointer-events-none opacity-45 dark:opacity-35 transition-opacity duration-300 animate-ambient-2"
                    style={{
                        background:
                            "radial-gradient(circle, rgba(56, 189, 248, 0.4) 0%, rgba(37, 99, 235, 0.35) 50%, transparent 75%)",
                    }}
                />
            </div>

            {/* Galaxy particle field canvas */}
            <ParticleField speed={0.4} />

            {/* Floating glass navigation */}
            <Navbar />

            {/* Hero Section */}
            <section className="pt-28 pb-12 sm:pt-32 sm:pb-14 px-4 sm:px-6 max-w-7xl mx-auto relative">
                <div className="relative z-10">
                    {/* Massive Frosted Glass Hero Container with Glint & Spotlight */}
                    <div className="glass-frosted-dark rounded-3xl p-8 sm:p-12 lg:p-16 text-slate-900 dark:text-white relative overflow-hidden mb-10 sm:mb-12 shadow-2xl transition-colors glint-surface spotlight-card">
                        {/* Specular Highlights */}
                        <div
                            className="absolute -right-32 -top-32 w-96 h-96 rounded-full blur-3xl pointer-events-none opacity-40 dark:opacity-80 animate-ambient-2"
                            style={{
                                background:
                                    "radial-gradient(circle, rgba(56, 189, 248, 0.35) 0%, transparent 70%)",
                            }}
                        />
                        <div
                            className="absolute -left-32 -bottom-32 w-96 h-96 rounded-full blur-3xl pointer-events-none opacity-40 dark:opacity-80 animate-ambient-1"
                            style={{
                                background:
                                    "radial-gradient(circle, rgba(99, 102, 241, 0.35) 0%, transparent 70%)",
                            }}
                        />

                        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center relative z-10">
                            {/* Left: Copy and Glowing CTAs */}
                            <div className="lg:col-span-7 space-y-6 text-left relative">
                                {/* Release Pill */}
                                <div className="inline-flex items-center gap-2.5 px-4 py-1.5 rounded-full glass-pill text-slate-900 dark:text-white border border-slate-200 dark:border-white/20 text-xs font-semibold tracking-wide shadow-sm hover:scale-105 transition-transform duration-200">
                                    <span className="w-2 h-2 rounded-full bg-blue-600 dark:bg-sky-400 animate-ping" />
                                    <span className="font-bold">✨ EduConnect 2.0 Luminous Institutional Glass</span>
                                    <ArrowRight className="text-slate-600 dark:text-slate-300" size={14} />
                                </div>

                                {/* Main Headline */}
                                <h1 className="text-3xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-slate-900 dark:text-white leading-tight font-heading transition-colors">
                                    Unify Your Entire{" "}
                                    <span className="text-transparent bg-clip-text bg-gradient-to-r from-slate-900 via-blue-600 to-cyan-500 dark:from-white dark:via-sky-300 dark:to-blue-400">
                                        School Ecosystem
                                    </span>{" "}
                                    in One Smart Platform
                                </h1>

                                {/* Engaging Sub-copy */}
                                <p className="text-slate-600 dark:text-slate-200 text-base sm:text-lg max-w-xl font-medium leading-relaxed transition-colors">
                                    Seamlessly connect Principals, Teachers, Students, and Parents through
                                    a synchronized, ultra-responsive crystal glass workspace. Run attendance,
                                    grading, fee pipelines, and real-time alerts effortlessly on autopilot.
                                </p>

                                {/* CTA Button Cluster */}
                                <div className="flex flex-wrap items-center gap-4 pt-2">
                                    <a
                                        className="px-8 py-4 rounded-xl font-bold text-white bg-blue-600 dark:bg-blue-600 dark:text-white flex items-center justify-center gap-2 transition-all transform hover:-translate-y-1 active:scale-95 shadow-xl glow-parchment hover:opacity-90 group"
                                        href={APP_AUTH_URL}
                                    >
                                        <span>Get started free</span>
                                        <ArrowRight className="transition-transform group-hover:translate-x-1" size={20} />
                                    </a>
                                    <a
                                        className="px-7 py-4 rounded-xl glass-pill text-slate-900 dark:text-white font-semibold flex items-center justify-center gap-2 hover:bg-slate-100 dark:hover:bg-slate-700 hover:-translate-y-0.5 transition-all border border-slate-200 dark:border-white/20"
                                        href="#modules"
                                    >
                                        <span>Explore features</span>
                                        <Sliders className="text-slate-600 dark:text-slate-300" size={18} />
                                    </a>
                                    <a
                                        className="px-5 py-4 rounded-xl text-slate-900 dark:text-white text-sm font-semibold flex items-center gap-1.5 hover:underline hover:translate-x-0.5 transition-transform"
                                        href="#calculator"
                                    >
                                        <Calculator className="text-slate-600 dark:text-slate-300" size={18} />
                                        <span>Calculate campus ROI</span>
                                    </a>
                                </div>

                                {/* Social Trust Micro-Bar */}
                                <div className="pt-4 flex items-center gap-6 border-t border-slate-200 dark:border-white/10 text-xs text-slate-600 dark:text-slate-300 transition-colors">
                                    <div className="flex items-center gap-1.5 hover:opacity-100 transition-opacity">
                                        <CheckCircle className="text-slate-900 dark:text-white" size={16} />
                                        <span>ISO 27001 Certified</span>
                                    </div>
                                    <div className="flex items-center gap-1.5 hover:opacity-100 transition-opacity">
                                        <Zap className="text-slate-900 dark:text-white" size={16} />
                                        <span>Instant 24-hr Rollout</span>
                                    </div>
                                    <div className="flex items-center gap-1.5 hover:opacity-100 transition-opacity">
                                        <Shield className="text-slate-900 dark:text-white" size={16} />
                                        <span>FERPA &amp; GDPR Ready</span>
                                    </div>
                                </div>
                            </div>

                            <HeroShowcase />
                        </div>
                    </div>

                    {/* Live Campus Trust Stats Grid */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-5xl mx-auto mb-8 sm:mb-10">
                        {STATS.map((s) => (
                            <div
                                key={s.label}
                                className="text-center p-6 rounded-2xl glass-epic border shadow-sm hover:-translate-y-1.5 hover:shadow-xl transition-all duration-300 group cursor-default"
                            >
                                <Counter value={s.value} />
                                <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-300 font-medium">
                                    {s.label}
                                </p>
                            </div>
                        ))}
                    </div>

                    {/* School Ticker Pill Ribbon */}
                    <div
                        className="max-w-5xl mx-auto rounded-2xl glass-pill p-3.5 border ticker-frame shadow-sm transition-colors"
                        role="region"
                        aria-label="Schools using EduConnect"
                    >
                        <div className="ticker-viewport">
                            <div className="ticker-move text-xs sm:text-sm text-slate-600 dark:text-slate-200 font-semibold font-mono">
                                {/* Two identical groups so the -50% loop is seamless. */}
                                {[0, 1].map((copy) => (
                                    <div
                                        key={copy}
                                        className="ticker-group"
                                        // The duplicate is decorative — keep it out of the a11y tree.
                                        aria-hidden={copy === 1 ? "true" : undefined}
                                    >
                                        {SCHOOLS.map((school) => (
                                            <span
                                                key={school}
                                                className="flex items-center gap-2 shrink-0"
                                            >
                                                <span
                                                    className="text-blue-600 dark:text-sky-400 font-bold"
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
                </div>
            </section>

            {/* Section: Role-Based Architecture */}
            <section
                className="py-14 sm:py-16 px-4 sm:px-6 max-w-7xl mx-auto border-t border-slate-200 dark:border-white/10 transition-colors"
                id="roles"
            >
                <div className="text-center max-w-3xl mx-auto mb-10 sm:mb-12">
                    <span className="px-3.5 py-1 rounded-full glass-pill text-slate-900 dark:text-white font-bold text-xs uppercase tracking-wider border font-mono">
                        Live Feature Previews
                    </span>
                    <h2 className="text-3xl sm:text-4xl font-extrabold text-slate-900 dark:text-white tracking-tight mt-3 mb-4 font-heading">
                        Engineered for Every Stakeholder in Your Ecosystem
                    </h2>
                    <p className="text-base text-slate-600 dark:text-slate-300 leading-relaxed">
                        EduConnect replaces disjointed spreadsheets and standalone apps with role-tailored glass
                        workspaces designed for maximum focus and zero operational clutter.
                    </p>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                    {/* Role 1: Administrators & Principals */}
                    <TiltCard className="glass-epic rounded-3xl p-7 border flex flex-col justify-between hover:shadow-2xl transition-all duration-300 group">
                        <div>
                            <div className="flex items-center justify-between mb-6">
                                <div className="w-12 h-12 rounded-2xl bg-blue-500/10 dark:bg-sky-400/15 text-blue-700 dark:text-sky-300 flex items-center justify-center shadow-sm border border-slate-200 dark:border-white/20 group-hover:scale-110 transition-transform">
                                    <Shield size={28} />
                                </div>
                                <span className="px-3 py-1 rounded-full text-xs font-bold bg-slate-100 dark:bg-white/10 text-slate-900 dark:text-white border border-slate-200 dark:border-white/15 font-mono">
                                    ERP Command
                                </span>
                            </div>
                            <h3 className="text-2xl font-bold text-slate-900 dark:text-white mb-2 font-heading">
                                Administrators &amp; Principals
                            </h3>
                            <p className="text-sm text-slate-600 dark:text-slate-300 mb-6 leading-relaxed">
                                Deep frosted blue glass panel overlaying real-time school fee telemetry, student admissions
                                pipeline, and audit-ready financial reporting.
                            </p>

                            <div className="p-4 rounded-2xl bg-white/70 dark:bg-slate-800/60 border border-slate-200 dark:border-white/10 space-y-3 mb-6 shadow-sm">
                                <div className="flex justify-between items-center text-xs pb-2 border-b border-slate-200 dark:border-white/5">
                                    <span className="font-bold text-slate-900 dark:text-white">
                                        Fee Collection Progress (Q2)
                                    </span>
                                    <span className="text-slate-900 dark:text-white font-bold font-mono">
                                        94.2%
                                    </span>
                                </div>
                                <div className="w-full h-2 bg-slate-200 dark:bg-slate-800 rounded-full overflow-hidden">
                                    <div className="h-full bg-gradient-to-r from-blue-600 to-cyan-500 dark:from-blue-500 dark:to-sky-300 rounded-full transition-all duration-1000" style={{ width: "94%" }} />
                                </div>
                                <div className="grid grid-cols-2 gap-2 pt-1 text-[11px] font-mono">
                                    <div className="p-2 rounded-lg bg-slate-50 dark:bg-slate-800/50">
                                        <p className="text-slate-600 dark:text-slate-300">Total Invoiced</p>
                                        <p className="font-bold text-slate-900 dark:text-white">₹78.2 Lakhs</p>
                                    </div>
                                    <div className="p-2 rounded-lg bg-slate-50 dark:bg-slate-800/50">
                                        <p className="text-slate-600 dark:text-slate-300">Admissions Goal</p>
                                        <p className="font-bold text-slate-900 dark:text-white">420 / 400 (105%)</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div className="pt-4 border-t border-slate-200 dark:border-white/10 flex items-center justify-between text-slate-900 dark:text-white font-semibold text-sm group-hover:translate-x-1 transition-transform">
                            <span>Explore Principal Hub</span>
                            <ArrowRight className="text-slate-600 dark:text-slate-300" size={18} />
                        </div>
                    </TiltCard>

                    {/* Role 2: Teachers & Instructors */}
                    <TiltCard className="glass-epic rounded-3xl p-7 border flex flex-col justify-between hover:shadow-2xl transition-all duration-300 group">
                        <div>
                            <div className="flex items-center justify-between mb-6">
                                <div className="w-12 h-12 rounded-2xl bg-blue-500/10 dark:bg-sky-400/15 text-blue-700 dark:text-sky-300 flex items-center justify-center shadow-sm border border-slate-200 dark:border-white/20 group-hover:scale-110 transition-transform">
                                    <CheckCircle size={28} />
                                </div>
                                <span className="px-3 py-1 rounded-full text-xs font-bold bg-blue-500/10 dark:bg-sky-400/15 text-blue-700 dark:text-sky-300 border border-blue-500/20 dark:border-sky-400/30 font-mono">
                                    Classroom OS
                                </span>
                            </div>
                            <h3 className="text-2xl font-bold text-slate-900 dark:text-white mb-2 font-heading">
                                Teachers &amp; Instructors
                            </h3>
                            <p className="text-sm text-slate-600 dark:text-slate-300 mb-6 leading-relaxed">
                                Multi-layered grid containing micro-cards for assignments, AI smart grading assistance,
                                attendance logs, and synchronized schedules.
                            </p>

                            <div className="p-4 rounded-2xl bg-white/70 dark:bg-slate-800/60 border border-slate-200 dark:border-white/10 space-y-3 mb-6 shadow-sm">
                                <div className="flex items-center justify-between text-xs pb-2 border-b border-slate-200 dark:border-white/5">
                                    <span className="font-bold text-slate-900 dark:text-white">
                                        Assignments Pending Review
                                    </span>
                                    <span className="px-2 py-0.5 rounded bg-slate-200 dark:bg-sky-400/15 text-slate-900 dark:text-white font-bold text-[10px] font-mono">
                                        4 to grade
                                    </span>
                                </div>
                                <div className="space-y-2 text-xs">
                                    <div className="flex items-center justify-between p-2 rounded-lg bg-slate-50 dark:bg-slate-800/50">
                                        <span className="text-slate-900 dark:text-white font-medium truncate">
                                            Physics Lab - Optics (10-B)
                                        </span>
                                        <span className="text-slate-900 dark:text-white font-bold shrink-0 flex items-center gap-1 font-mono">
                                            AI Graded <CheckCircle className="text-emerald-500" size={14} />
                                        </span>
                                    </div>
                                    <div className="flex items-center justify-between p-2 rounded-lg bg-slate-50 dark:bg-slate-800/50">
                                        <span className="text-slate-900 dark:text-white font-medium truncate">
                                            English Essay (9-A)
                                        </span>
                                        <span className="text-slate-600 dark:text-slate-300 font-bold shrink-0 font-mono">
                                            34 / 36 Submitted
                                        </span>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div className="pt-4 border-t border-slate-200 dark:border-white/10 flex items-center justify-between text-slate-900 dark:text-white font-semibold text-sm group-hover:translate-x-1 transition-transform">
                            <span>Explore Instructor Suite</span>
                            <ArrowRight className="text-slate-600 dark:text-slate-300" size={18} />
                        </div>
                    </TiltCard>

                    {/* Role 3: Students & Parents */}
                    <TiltCard className="glass-epic rounded-3xl p-7 border flex flex-col justify-between hover:shadow-2xl transition-all duration-300 group">
                        <div>
                            <div className="flex items-center justify-between mb-6">
                                <div className="w-12 h-12 rounded-2xl bg-blue-500/10 dark:bg-sky-400/15 text-blue-700 dark:text-sky-300 flex items-center justify-center shadow-sm border border-slate-200 dark:border-white/20 group-hover:scale-110 transition-transform">
                                    <Users size={28} />
                                </div>
                                <span className="px-3 py-1 rounded-full text-xs font-bold bg-slate-100 dark:bg-white/10 text-slate-900 dark:text-white border border-slate-200 dark:border-white/15 font-mono">
                                    Parent &amp; Student
                                </span>
                            </div>
                            <h3 className="text-2xl font-bold text-slate-900 dark:text-white mb-2 font-heading">
                                Students &amp; Parents
                            </h3>
                            <p className="text-sm text-slate-600 dark:text-slate-300 mb-6 leading-relaxed">
                                Softly blurred crystal glass card featuring student progress graphs, timetable alerts,
                                one-click fee payments, and direct teacher chat threads.
                            </p>

                            <div className="p-4 rounded-2xl bg-white/70 dark:bg-slate-800/60 border border-slate-200 dark:border-white/10 space-y-3 mb-6 shadow-sm">
                                <div className="flex items-center justify-between text-xs pb-2 border-b border-slate-200 dark:border-white/5">
                                    <span className="font-bold text-slate-900 dark:text-white">
                                        Student: Aarav Sharma (Grade 8)
                                    </span>
                                    <span className="text-slate-600 dark:text-slate-300 font-semibold text-[11px] font-mono">
                                        Next: Math @ 10:15 AM
                                    </span>
                                </div>
                                <div className="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/50 flex items-center justify-between text-xs">
                                    <span className="text-slate-600 dark:text-slate-300">Teacher Mrs. Roy:</span>
                                    <span className="font-medium text-slate-900 dark:text-white">
                                        &ldquo;Great progress today!&rdquo;
                                    </span>
                                </div>
                                <div className="flex items-center justify-between text-[11px] text-slate-600 dark:text-slate-300 pt-1 font-mono">
                                    <span>Bus #12 Live: 4 mins away</span>
                                    <span className="text-slate-900 dark:text-white font-bold flex items-center gap-1">
                                        <span className="w-2 h-2 rounded-full bg-emerald-500 live-beacon" /> On Route
                                    </span>
                                </div>
                            </div>
                        </div>
                        <div className="pt-4 border-t border-slate-200 dark:border-white/10 flex items-center justify-between text-slate-900 dark:text-white font-semibold text-sm group-hover:translate-x-1 transition-transform">
                            <span>Explore Family Portal</span>
                            <ArrowRight className="text-slate-600 dark:text-slate-300" size={18} />
                        </div>
                    </TiltCard>
                </div>
            </section>

            {/* Section: Intelligent Toolkit Modules (Bento Grid) */}
            <section className="py-14 sm:py-16 px-4 sm:px-6 max-w-7xl mx-auto" id="modules">
                <div className="text-center max-w-2xl mx-auto mb-10 sm:mb-12">
                    <span className="text-xs uppercase tracking-wider text-slate-900 dark:text-white font-bold font-mono">
                        Modules
                    </span>
                    <h2 className="text-3xl sm:text-4xl text-slate-900 dark:text-white mt-2 mb-4 font-extrabold font-heading">
                        A Unified Toolkit for the Modern Campus
                    </h2>
                    <p className="text-slate-600 dark:text-slate-300 leading-relaxed">
                        Everything you need to run a physical school, seamlessly integrated and powered by intelligent
                        automation.
                    </p>
                </div>

                {/* Bento Grid */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    {/* Bento 1: Flagship AI Copilot */}
                    <AiCopilotModule />

                    {/* Bento 2: Smart Attendance */}
                    <TiltCard className="crystalline-glass p-8 rounded-3xl flex flex-col justify-between border group">
                        <div>
                            <div className="w-12 h-12 rounded-xl bg-blue-500/10 dark:bg-sky-400/15 border border-blue-500/20 dark:border-sky-400/30 flex items-center justify-center text-blue-700 dark:text-sky-300 mb-6 group-hover:scale-110 transition-transform">
                                <CheckCircle size={24} />
                            </div>
                            <h3 className="text-2xl text-slate-900 dark:text-white font-bold mb-3 font-heading">
                                Smart Attendance
                            </h3>
                            <p className="text-slate-600 dark:text-slate-300 mb-6 leading-relaxed">
                                Frictionless tracking for physical classrooms with automated anomaly detection for absenteeism.
                            </p>
                        </div>
                        <div className="p-3 rounded-xl bg-white/80 dark:bg-slate-800/50 border border-slate-200 dark:border-white/10 flex items-center gap-3 hover:scale-[1.02] transition-transform">
                            <span className="w-2.5 h-2.5 rounded-full bg-amber-500 animate-pulse" />
                            <span className="text-xs text-slate-600 dark:text-slate-300 font-medium font-mono">
                                Auto-SMS sent for 3 absences today
                            </span>
                        </div>
                    </TiltCard>

                    {/* Bento 3: Deep Analytics */}
                    <TiltCard className="crystalline-glass p-8 rounded-3xl flex flex-col justify-between border group">
                        <div>
                            <div className="w-12 h-12 rounded-xl bg-blue-500/10 dark:bg-sky-400/15 border border-blue-500/20 dark:border-sky-400/30 flex items-center justify-center text-blue-700 dark:text-sky-300 mb-6 group-hover:scale-110 transition-transform">
                                <TrendingUp size={24} />
                            </div>
                            <h3 className="text-2xl text-slate-900 dark:text-white font-bold mb-3 font-heading">
                                Deep Analytics
                            </h3>
                            <p className="text-slate-600 dark:text-slate-300 mb-6 leading-relaxed">
                                Transform data into action. Gain comprehensive insights into academic performance and operational efficiency.
                            </p>
                        </div>
                        <div className="p-3 rounded-xl bg-white/80 dark:bg-slate-800/50 border border-slate-200 dark:border-white/10 flex items-center justify-between hover:scale-[1.02] transition-transform cursor-pointer">
                            <span className="text-xs text-slate-600 dark:text-slate-300 font-medium font-mono">
                                CBSE / ICSE format ready
                            </span>
                            <Download className="text-slate-900 dark:text-white group-hover:translate-y-0.5 transition-transform" size={18} />
                        </div>
                    </TiltCard>

                    {/* Bento 4: Transparent Fees */}
                    <TiltCard className="crystalline-glass p-8 rounded-3xl flex flex-col justify-between border group">
                        <div>
                            <div className="w-12 h-12 rounded-xl bg-blue-500/10 dark:bg-sky-400/15 border border-blue-500/20 dark:border-sky-400/30 flex items-center justify-center text-blue-700 dark:text-sky-300 mb-6 group-hover:scale-110 transition-transform">
                                <Award size={24} />
                            </div>
                            <h3 className="text-2xl text-slate-900 dark:text-white font-bold mb-3 font-heading">
                                Transparent Fees
                            </h3>
                            <p className="text-slate-600 dark:text-slate-300 mb-6 leading-relaxed">
                                Online payments, instant receipts and live dues tracking — no more ledger registers.
                            </p>
                        </div>
                        <div className="p-3 rounded-xl bg-white/80 dark:bg-slate-800/50 border border-slate-200 dark:border-white/10 flex items-center justify-between hover:scale-[1.02] transition-transform">
                            <span className="text-xs text-slate-900 dark:text-white font-semibold font-mono">
                                Zero manual reconciliation
                            </span>
                            <CheckCircle className="text-emerald-500" size={18} />
                        </div>
                    </TiltCard>

                    {/* Bento 5: Unified Comms */}
                    <TiltCard className="crystalline-glass p-8 rounded-3xl flex flex-col justify-between border group">
                        <div>
                            <div className="w-12 h-12 rounded-xl bg-slate-200 dark:bg-slate-800 border border-slate-200 dark:border-white/15 flex items-center justify-center text-slate-900 dark:text-white mb-6 group-hover:scale-110 transition-transform">
                                <Lock size={24} />
                            </div>
                            <h3 className="text-2xl text-slate-900 dark:text-white font-bold mb-3 font-heading">
                                Unified Comms
                            </h3>
                            <p className="text-slate-600 dark:text-slate-300 mb-6 leading-relaxed">
                                Secure, real-time messaging connecting teachers, parents, and students in one centralized hub.
                            </p>
                        </div>
                        <div className="p-3 rounded-xl bg-white/80 dark:bg-slate-800/50 border border-slate-200 dark:border-white/10 flex items-center gap-2 hover:scale-[1.02] transition-transform">
                            <Lock className="text-slate-900 dark:text-white" size={18} />
                            <span className="text-xs text-slate-600 dark:text-slate-300 font-medium font-mono">
                                Encrypted verified school channels
                            </span>
                        </div>
                    </TiltCard>
                </div>
            </section>

            {/* Section: Campus ROI Calculator */}
            <RoiCalculator />

            {/* Section: Transparent Pricing */}
            <PricingSection />

            {/* Section: Implementation & Testimonials */}
            <section
                className="py-14 sm:py-16 px-4 sm:px-6 max-w-7xl mx-auto border-t border-slate-200 dark:border-white/10 transition-colors"
                id="how-it-works"
            >
                <div className="text-center max-w-2xl mx-auto mb-10 sm:mb-12">
                    <span className="px-3.5 py-1 rounded-full glass-pill text-slate-900 dark:text-white font-bold text-xs uppercase tracking-wider border font-mono">
                        Verified Social Proof
                    </span>
                    <h2 className="text-3xl sm:text-4xl font-extrabold text-slate-900 dark:text-white tracking-tight mt-3 mb-4 font-heading">
                        Trusted by Leading Educational Leaders
                    </h2>
                    <p className="text-base text-slate-600 dark:text-slate-300">
                        Hear directly from school directors, principals, and IT coordinators on their transition to EduConnect OS.
                    </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    {/* Quote 1: Meera Nair */}
                    <div className="glass-epic p-8 rounded-3xl flex flex-col justify-between border shadow-lg hover:shadow-2xl hover:-translate-y-1.5 transition-all duration-300">
                        <div>
                            <div className="flex items-center justify-between mb-4">
                                <div className="flex text-slate-900 dark:text-white gap-0.5">
                                    {[...Array(5)].map((_, i) => (
                                        <Star key={i} fill="currentColor" size={20} />
                                    ))}
                                </div>
                                <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-blue-500/10 text-blue-700 dark:bg-sky-400/15 dark:text-sky-300 border border-blue-500/20 dark:border-sky-400/30 font-mono">
                                    Verified Director
                                </span>
                            </div>
                            <p className="text-slate-900 dark:text-white text-sm leading-relaxed mb-6 italic font-medium">
                                “Fee collection is fully transparent now — receipts, dues and automated reminders run themselves.
                                Our finance office workload literally dropped by half within 30 days.”
                            </p>
                        </div>
                        <div className="flex items-center gap-3 pt-4 border-t border-slate-200 dark:border-white/10">
                            <div className="w-11 h-11 rounded-full bg-blue-600 text-white dark:bg-sky-500 dark:text-slate-900 flex items-center justify-center font-bold text-sm shadow-sm font-mono">
                                MN
                            </div>
                            <div>
                                <p className="font-bold text-slate-900 dark:text-white text-sm">Meera Nair</p>
                                <p className="text-xs text-slate-600 dark:text-slate-300">
                                    Director · Sunrise Public School (1,850 Students)
                                </p>
                            </div>
                        </div>
                    </div>

                    {/* Quote 2: Rajesh Iyer */}
                    <div className="glass-epic p-8 rounded-3xl flex flex-col justify-between border shadow-lg hover:shadow-2xl hover:-translate-y-1.5 transition-all duration-300">
                        <div>
                            <div className="flex items-center justify-between mb-4">
                                <div className="flex text-slate-900 dark:text-white gap-0.5">
                                    {[...Array(5)].map((_, i) => (
                                        <Star key={i} fill="currentColor" size={20} />
                                    ))}
                                </div>
                                <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-blue-500/10 text-blue-700 dark:bg-sky-400/15 dark:text-sky-300 border border-blue-500/20 dark:border-sky-400/30 font-mono">
                                    Verified Principal
                                </span>
                            </div>
                            <p className="text-slate-900 dark:text-white text-sm leading-relaxed mb-6 italic font-medium">
                                “From attendance to report cards on one unified screen. My teachers finally spend their energy
                                mentoring students instead of wrestling with paper log registers and spreadsheets.”
                            </p>
                        </div>
                        <div className="flex items-center gap-3 pt-4 border-t border-slate-200 dark:border-white/10">
                            <div className="w-11 h-11 rounded-full bg-slate-500 text-white flex items-center justify-center font-bold text-sm shadow-sm font-mono">
                                RI
                            </div>
                            <div>
                                <p className="font-bold text-slate-900 dark:text-white text-sm">Rajesh Iyer</p>
                                <p className="text-xs text-slate-600 dark:text-slate-300">
                                    Principal · Green Valley International Academy
                                </p>
                            </div>
                        </div>
                    </div>

                    {/* Quote 3: Dr. Anita Sharma */}
                    <div className="glass-epic p-8 rounded-3xl flex flex-col justify-between border shadow-lg hover:shadow-2xl hover:-translate-y-1.5 transition-all duration-300">
                        <div>
                            <div className="flex items-center justify-between mb-4">
                                <div className="flex text-slate-900 dark:text-white gap-0.5">
                                    {[...Array(5)].map((_, i) => (
                                        <Star key={i} fill="currentColor" size={20} />
                                    ))}
                                </div>
                                <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-blue-500/10 text-blue-700 dark:bg-sky-400/15 dark:text-sky-300 border border-blue-500/20 dark:border-sky-400/30 font-mono">
                                    Verified Faculty Head
                                </span>
                            </div>
                            <p className="text-slate-900 dark:text-white text-sm leading-relaxed mb-6 italic font-medium">
                                “Parents message directly through verified channels and receive timely answers. The built-in AI Copilot
                                drafts our routine parent communications flawlessly and securely.”
                            </p>
                        </div>
                        <div className="flex items-center gap-3 pt-4 border-t border-slate-200 dark:border-white/10">
                            <div className="w-11 h-11 rounded-full bg-blue-600 text-white dark:bg-sky-500 dark:text-slate-900 flex items-center justify-center font-bold text-sm shadow-sm font-mono">
                                AS
                            </div>
                            <div>
                                <p className="font-bold text-slate-900 dark:text-white text-sm">Dr. Anita Sharma</p>
                                <p className="text-xs text-slate-600 dark:text-slate-300">
                                    Academic Dean · St. Xavier High School
                                </p>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* Section: Frequently Asked Questions */}
            <FaqSection />

            {/* Section: High-Conversion CTA Block */}
            <section className="py-10 sm:py-12 px-4 sm:px-6 max-w-7xl mx-auto">
                <div className="relative rounded-3xl crystalline-dock p-8 sm:p-14 text-center overflow-hidden border glint-surface">
                    <div className="absolute -right-20 -top-20 w-80 h-80 bg-blue-500/10 dark:bg-sky-400/15 rounded-full blur-3xl pointer-events-none animate-ambient-1" />
                    <div className="absolute -left-20 -bottom-20 w-80 h-80 bg-blue-600/25 rounded-full blur-3xl pointer-events-none animate-ambient-2" />
                    <div className="relative z-10 max-w-2xl mx-auto">
                        <h2 className="text-2xl sm:text-4xl text-slate-900 dark:text-white font-bold mb-4 font-heading">
                            Ready to run your school on autopilot?
                        </h2>
                        <p className="text-base sm:text-lg text-slate-600 dark:text-slate-200 mb-8">
                            Join 500+ schools automating attendance, fees and communication with EduConnect.
                        </p>
                        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                            <a
                                className="w-full sm:w-auto px-8 py-3.5 rounded-lg bg-blue-600 text-white dark:bg-blue-600 dark:text-white text-sm font-bold shadow-lg shadow-black/20 dark:shadow-black/40 hover:opacity-90 transition-all hover:-translate-y-1 active:scale-95 glow-parchment font-mono"
                                href={APP_AUTH_URL}
                            >
                                Get started free
                            </a>
                            <a
                                className="w-full sm:w-auto px-8 py-3.5 rounded-lg crystalline-glass text-slate-900 dark:text-white text-sm font-semibold border hover:bg-slate-100 dark:hover:bg-slate-700 transition-all hover:-translate-y-1 active:scale-95 font-mono"
                                href="#modules"
                            >
                                Explore modules
                            </a>
                        </div>
                    </div>
                </div>
            </section>

            {/* Section: About EduConnect */}
            <section
                className="py-14 sm:py-16 px-4 sm:px-6 max-w-7xl mx-auto border-t border-slate-200 dark:border-white/10 transition-colors"
                id="about"
            >
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
                    <div className="lg:col-span-6">
                        <span className="text-xs uppercase tracking-wider text-slate-900 dark:text-white font-bold font-mono">
                            About
                        </span>
                        <h2 className="text-3xl sm:text-4xl text-slate-900 dark:text-white font-bold mt-2 mb-4 font-heading">
                            About EduConnect
                        </h2>
                        <p className="text-base sm:text-lg text-slate-900 dark:text-white mb-6 leading-relaxed">
                            EduConnect is a{" "}
                            <strong className="font-bold text-slate-900 dark:text-white">
                                school operating system
                            </strong>{" "}
                            — it automates the complete workflow of a school in one secure platform.
                        </p>
                        <ul className="space-y-3.5 text-slate-600 dark:text-slate-300 text-sm sm:text-base">
                            {ABOUT_POINTS.map((point) => (
                                <li key={point} className="flex items-start gap-3 hover:translate-x-1 transition-transform">
                                    <CheckCircle className="text-slate-900 dark:text-white shrink-0 mt-0.5" size={20} />
                                    <span className="text-slate-900 dark:text-white">{point}</span>
                                </li>
                            ))}
                        </ul>
                    </div>
                    <div className="lg:col-span-6">
                        <div className="p-8 rounded-3xl crystalline-glass border shadow-xl relative spotlight-card tilt-card">
                            <div className="flex items-center gap-3 mb-6">
                                <div className="w-10 h-10 rounded-xl bg-blue-600 text-white dark:bg-sky-500 dark:text-slate-900 flex items-center justify-center shadow-md">
                                    <Shield size={22} />
                                </div>
                                <div>
                                    <h4 className="text-lg font-bold text-slate-900 dark:text-white font-heading">
                                        Zero-paperwork operations
                                    </h4>
                                    <p className="text-xs text-slate-600 dark:text-slate-300 font-mono">
                                        Engineered for physical schools
                                    </p>
                                </div>
                            </div>
                            <p className="text-sm text-slate-600 dark:text-slate-200 leading-relaxed mb-6">
                                Transform manual physical paperwork into unified digital state machines. From morning bus telemetry
                                to evening parent communication, EduConnect guarantees zero data loss and automated regulatory
                                compliance.
                            </p>
                            <div className="grid grid-cols-2 gap-4">
                                <div className="p-4 rounded-xl bg-white/70 dark:bg-slate-800/60 border border-slate-200 dark:border-white/10 transition-all hover:scale-105">
                                    <span className="text-xs text-slate-600 dark:text-slate-300 block font-mono">
                                        Direct Contact
                                    </span>
                                    <a
                                        className="text-xs font-semibold text-slate-900 dark:text-white hover:underline font-mono"
                                        href="mailto:hello@educonnect.school"
                                    >
                                        hello@educonnect.school
                                    </a>
                                </div>
                                <div className="p-4 rounded-xl bg-white/70 dark:bg-slate-800/60 border border-slate-200 dark:border-white/10 transition-all hover:scale-105">
                                    <span className="text-xs text-slate-600 dark:text-slate-300 block font-mono">
                                        Campus Hotline
                                    </span>
                                    <a
                                        className="text-xs font-semibold text-slate-900 dark:text-white hover:underline font-mono"
                                        href="tel:+919876543210"
                                    >
                                        +91 98765 43210
                                    </a>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            <Footer />
        </div>
    );
}
