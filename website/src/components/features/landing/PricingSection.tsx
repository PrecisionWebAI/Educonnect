"use client";

import React, { useState } from "react";
import { ArrowRight, BadgeCheck, Check, Crown, ShieldCheck } from "lucide-react";
import Reveal from "./Reveal";
import { cn } from "@/lib/utils";

const APP_AUTH_URL = process.env.NEXT_PUBLIC_APP_URL || "http://localhost:3000";

type Cycle = "annual" | "monthly";

interface Plan {
    id: string;
    name: string;
    tagline: string;
    /** Indicative per-student / month price; null renders "Custom". */
    monthly: number | null;
    annual: number | null;
    students: string;
    badge?: string;
    featured?: boolean;
    features: string[];
    cta: string;
}

const PLANS: Plan[] = [
    {
        id: "essential",
        name: "Essential Campus",
        tagline: "For growing schools digitising the core office",
        monthly: 59,
        annual: 49,
        students: "Up to 800 students",
        features: [
            "Attendance, timetable & academics",
            "Fees, receipts & dues automation",
            "Parent app with real-time alerts",
            "SMS / app notification bundles",
            "Onboarding & data migration support",
            "Business-hours support (Mon–Sat)",
        ],
        cta: "Start free pilot",
    },
    {
        id: "growth",
        name: "Growth Institute",
        tagline: "The full AI toolkit most schools pick",
        monthly: 94,
        annual: 79,
        students: "800 – 2,500 students",
        badge: "Most popular",
        featured: true,
        features: [
            "Everything in Essential Campus",
            "AI Copilot — drafting, summaries, analysis",
            "AI paper generator + question bank",
            "Library, transport & leave workflows",
            "Payroll, payslips & budget tracking",
            "Report builder with scheduled exports",
            "Priority support with 4-hr response",
        ],
        cta: "Start free pilot",
    },
    {
        id: "enterprise",
        name: "Enterprise Academy",
        tagline: "Multi-branch groups & campus chains",
        monthly: null,
        annual: null,
        students: "Unlimited students & branches",
        features: [
            "Everything in Growth Institute",
            "Consolidated multi-branch analytics",
            "SSO & fine-grained access control",
            "Custom integrations (Tally, ERP, biometric)",
            "Dedicated success manager",
            "99.9% uptime SLA + audit pack",
            "On-site training & quarterly reviews",
        ],
        cta: "Talk to sales",
    },
];

const INCLUDED = [
    "14-day guided pilot",
    "Free data migration",
    "Unlimited staff accounts",
    "No credit card required",
];

export default function PricingSection() {
    const [cycle, setCycle] = useState<Cycle>("annual");

    return (
        <section
            id="pricing"
            className="py-14 sm:py-16 px-4 sm:px-6 max-w-7xl mx-auto border-t border-slate-200/80 dark:border-white/10 transition-colors"
        >
            <Reveal className="text-center max-w-3xl mx-auto mb-10 sm:mb-12">
                <span className="px-3.5 py-1 rounded-full glass-pill text-blue-600 dark:text-sky-400 font-bold text-xs uppercase tracking-wider border font-mono">
                    Transparent Pricing
                </span>
                <h2 className="text-3xl sm:text-4xl font-extrabold text-slate-900 dark:text-white tracking-tight mt-3 mb-4 font-heading">
                    Plans That Scale With Your Campus
                </h2>
                <p className="text-base text-slate-600 dark:text-slate-300 leading-relaxed">
                    One platform, every stakeholder — priced per student so budgets stay predictable as you grow.
                    Switch or cancel any term.
                </p>
            </Reveal>

            {/* Billing cycle switch */}
            <Reveal delay={80} className="flex items-center justify-center mb-12">
                <div
                    className="inline-flex items-center gap-1 p-1 rounded-full glass-pill border border-slate-200 dark:border-white/10 shadow-sm"
                    role="group"
                    aria-label="Billing cycle"
                >
                    {(["annual", "monthly"] as Cycle[]).map((option) => {
                        const selected = cycle === option;
                        return (
                            <button
                                key={option}
                                type="button"
                                aria-pressed={selected}
                                onClick={() => setCycle(option)}
                                className={cn(
                                    "px-4 sm:px-5 py-2 rounded-full text-xs font-bold tracking-wide transition-all font-mono",
                                    selected
                                        ? "bg-blue-600 text-white shadow-md shadow-blue-600/25"
                                        : "text-slate-600 dark:text-slate-300 hover:text-blue-600 dark:hover:text-white",
                                )}
                            >
                                {option === "annual" ? "Annual" : "Monthly"}
                                {option === "annual" && (
                                    <span className="ml-2 hidden sm:inline text-[10px] font-bold text-emerald-500 dark:text-emerald-400">
                                        SAVE 20%
                                    </span>
                                )}
                            </button>
                        );
                    })}
                </div>
            </Reveal>

            {/* Plan cards */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 lg:items-stretch">
                {PLANS.map((plan, index) => {
                    const price = cycle === "annual" ? plan.annual : plan.monthly;
                    return (
                        <Reveal key={plan.id} delay={index * 90} className="h-full">
                            <div
                                className={cn(
                                    "relative h-full flex flex-col justify-between rounded-3xl p-7 border transition-all duration-300 group",
                                    plan.featured
                                        ? "glass-epic shadow-2xl ring-2 ring-blue-600/40 dark:ring-sky-400/30 lg:-translate-y-2"
                                        : "glass-epic shadow-lg hover:-translate-y-1.5",
                                )}
                            >
                                {plan.badge && (
                                    <span className="absolute -top-3 left-7 inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider bg-blue-600 text-white shadow-md font-mono">
                                        <Crown size={12} />
                                        {plan.badge}
                                    </span>
                                )}

                                <div>
                                    <h3 className="text-xl font-bold text-slate-900 dark:text-white mb-1.5 font-heading">
                                        {plan.name}
                                    </h3>
                                    <p className="text-xs text-slate-600 dark:text-slate-300 mb-6 leading-relaxed">
                                        {plan.tagline}
                                    </p>

                                    {/* Price */}
                                    <div className="p-5 rounded-2xl bg-slate-50 dark:bg-slate-800/80 border border-slate-200/80 dark:border-white/10 mb-6">
                                        <div className="flex items-end gap-2">
                                            {price === null ? (
                                                <span className="text-3xl font-extrabold text-slate-900 dark:text-white font-heading">
                                                    Custom
                                                </span>
                                            ) : (
                                                <>
                                                    <span className="text-3xl sm:text-4xl font-extrabold text-slate-900 dark:text-white leading-none font-heading">
                                                        ₹{price}
                                                    </span>
                                                    <span className="text-[11px] text-slate-500 dark:text-slate-400 font-mono pb-0.5">
                                                        /student/month
                                                    </span>
                                                </>
                                            )}
                                        </div>
                                        <p className="text-[10px] text-slate-500 dark:text-slate-400 mt-2 font-mono">
                                            {price === null
                                                ? "Volume & branch based · annual contract"
                                                : cycle === "annual"
                                                  ? "Billed annually · 20% lower than monthly"
                                                  : "Billed monthly · cancel anytime"}
                                        </p>
                                        <p className="text-[11px] font-bold text-slate-800 dark:text-slate-200 mt-3 flex items-center gap-1.5">
                                            <BadgeCheck size={14} className="text-blue-600 dark:text-sky-400" />
                                            {plan.students}
                                        </p>
                                    </div>

                                    <ul className="space-y-3 mb-8">
                                        {plan.features.map((feature) => (
                                            <li key={feature} className="flex items-start gap-2.5 text-sm">
                                                <Check
                                                    className="text-emerald-500 dark:text-emerald-400 shrink-0 mt-0.5"
                                                    size={16}
                                                    strokeWidth={3}
                                                />
                                                <span className="text-slate-700 dark:text-slate-200 leading-relaxed">
                                                    {feature}
                                                </span>
                                            </li>
                                        ))}
                                    </ul>
                                </div>

                                <a
                                    href={APP_AUTH_URL}
                                    className={cn(
                                        "w-full inline-flex items-center justify-center gap-2 rounded-xl px-5 py-3.5 text-sm font-bold transition-all hover:-translate-y-0.5 active:scale-[0.98] font-mono",
                                        plan.featured
                                            ? "bg-blue-600 text-white hover:bg-blue-700 shadow-xl shadow-blue-600/30 glow-parchment"
                                            : "crystalline-glass text-slate-800 dark:text-white border hover:bg-blue-50/50 dark:hover:bg-slate-800/60",
                                    )}
                                >
                                    {plan.cta}
                                    <ArrowRight
                                        size={16}
                                        className="transition-transform group-hover:translate-x-1"
                                    />
                                </a>
                            </div>
                        </Reveal>
                    );
                })}
            </div>

            {/* Included with every plan */}
            <Reveal delay={120} className="mt-10">
                <div className="rounded-2xl glass-pill border border-slate-200 dark:border-white/10 p-5 flex flex-wrap items-center justify-center gap-x-8 gap-y-3">
                    {INCLUDED.map((item) => (
                        <span
                            key={item}
                            className="inline-flex items-center gap-2 text-xs font-semibold text-slate-800 dark:text-slate-200 font-mono"
                        >
                            <ShieldCheck className="text-emerald-500 dark:text-emerald-400" size={16} />
                            {item}
                        </span>
                    ))}
                </div>
                <p className="text-center text-[11px] text-slate-500 dark:text-slate-400 mt-4 font-mono leading-relaxed">
                    Indicative India pricing, exclusive of GST. Volume discounts from 2,500 students; non-profit and
                    trust-run schools get special rates.
                </p>
            </Reveal>
        </section>
    );
}
