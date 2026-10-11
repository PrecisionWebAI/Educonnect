"use client";

import React, { useState } from "react";
import {
  ArrowRight,
  BadgeCheck,
  Check,
  Crown,
  ShieldCheck,
} from "lucide-react";
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
      className="py-20 sm:py-24 px-4 sm:px-6 max-w-7xl mx-auto border-t border-slate-200/80 dark:border-white/5 transition-colors"
    >
      <Reveal className="text-center max-w-3xl mx-auto mb-12 sm:mb-16">
        <span className="px-3.5 py-1.5 rounded-full bg-[#99753a]/10 text-[#99753a] font-semibold text-xs uppercase tracking-wider border border-[#99753a]/25 dark:bg-[#99753a]/15 dark:text-[#99753a] dark:border-[#99753a]/30">
          Transparent Pricing
        </span>
        <h2 className="text-3xl sm:text-4xl font-extrabold text-slate-900 dark:text-slate-50 tracking-tight mt-3 mb-4 font-heading">
          Plans That Scale With Your Campus
        </h2>
        <p className="text-base sm:text-lg text-slate-600 dark:text-slate-300 leading-relaxed">
          One platform, every stakeholder — priced per student so budgets stay
          predictable as you grow. Switch or cancel any term.
        </p>
      </Reveal>

      {/* Billing cycle switch */}
      <Reveal delay={80} className="flex items-center justify-center mb-12">
        <div
          className="inline-flex items-center gap-1 p-1 rounded-full bg-slate-100 dark:bg-[#131E3A] border border-slate-200 dark:border-white/10 shadow-sm"
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
                  "px-5 py-2 rounded-full text-xs font-semibold tracking-normal transition-all",
                  selected
                    ? "bg-[#99753a] text-white shadow-sm font-bold dark:shadow-md dark:shadow-black/40"
                    : "text-slate-600 dark:text-slate-300 hover:text-[#99753a] dark:hover:text-[#99753a]",
                )}
              >
                {option === "annual" ? "Annual Billing" : "Monthly"}
                {option === "annual" && (
                  <span className="ml-2 hidden sm:inline text-[11px] font-bold text-white/90 bg-black/20 px-1.5 py-0.5 rounded">
                    SAVE 20%
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </Reveal>

      {/* Plan cards */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 lg:items-stretch">
        {PLANS.map((plan, index) => {
          const price = cycle === "annual" ? plan.annual : plan.monthly;
          return (
            <Reveal key={plan.id} delay={index * 100} className="h-full">
              <div
                className={cn(
                  "relative h-full flex flex-col justify-between rounded-3xl transition-all duration-300 group",
                  plan.featured
                    ? "relative z-10 lg:scale-105 p-8 sm:p-10 border-2 border-[#99753a] dark:border-[#99753a]/60 bg-white dark:bg-[#1C294A] text-slate-900 dark:text-slate-50 shadow-xl shadow-slate-200/80 dark:shadow-2xl dark:shadow-black/60"
                    : "p-8 sm:p-10 border border-slate-200 dark:border-white/5 bg-white dark:bg-[#131E3A] text-slate-900 dark:text-slate-50 shadow-lg shadow-slate-200/50 dark:shadow-xl dark:shadow-black/30 hover:-translate-y-1 hover:shadow-xl dark:hover:shadow-black/50",
                )}
              >
                {plan.badge && (
                  <span className="absolute -top-3.5 left-1/2 -translate-x-1/2 inline-flex items-center gap-1.5 px-4 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-[#99753a] text-white shadow-md shadow-[#99753a]/25 dark:shadow-md dark:shadow-black/40">
                    <Crown size={13} />
                    {plan.badge}
                  </span>
                )}

                <div>
                  <h3
                    className={cn(
                      "font-bold mb-2 font-heading text-slate-900 dark:text-slate-50",
                      plan.featured ? "text-2xl" : "text-xl",
                    )}
                  >
                    {plan.name}
                  </h3>
                  <p
                    className={cn(
                      "text-xs mb-6 leading-relaxed",
                      plan.featured
                        ? "text-slate-600 dark:text-slate-300"
                        : "text-slate-600 dark:text-slate-400",
                    )}
                  >
                    {plan.tagline}
                  </p>

                  {/* Price Box */}
                  <div
                    className={cn(
                      "p-5 rounded-2xl mb-6 transition-colors",
                      plan.featured
                        ? "bg-slate-50 dark:bg-[#131E3A] border border-slate-200/80 dark:border-white/5"
                        : "bg-slate-50 dark:bg-[#0B1221] border border-slate-200/70 dark:border-white/5",
                    )}
                  >
                    <div className="flex items-end gap-2">
                      {price === null ? (
                        <span className="text-3xl font-extrabold font-heading text-slate-900 dark:text-slate-50">
                          Custom
                        </span>
                      ) : (
                        <>
                          <span className="text-3xl sm:text-4xl font-extrabold leading-none font-heading text-slate-900 dark:text-slate-50">
                            ₹{price}
                          </span>
                          <span className="text-xs font-medium pb-0.5 text-slate-500 dark:text-slate-400">
                            /student/month
                          </span>
                        </>
                      )}
                    </div>
                    <p className="text-xs mt-2 font-medium text-slate-500 dark:text-slate-400">
                      {price === null
                        ? "Volume & branch based · annual contract"
                        : cycle === "annual"
                          ? "Billed annually · 20% lower than monthly"
                          : "Billed monthly · cancel anytime"}
                    </p>
                    <p className="text-xs font-semibold mt-3 flex items-center gap-1.5 text-slate-800 dark:text-slate-200">
                      <BadgeCheck size={14} className="text-[#99753a]" />
                      {plan.students}
                    </p>
                  </div>

                  {/* Features List */}
                  <ul className="space-y-3 mb-8">
                    {plan.features.map((feature) => (
                      <li
                        key={feature}
                        className="flex items-start gap-2.5 text-sm"
                      >
                        <Check
                          className="shrink-0 mt-0.5 text-[#99753a]"
                          size={16}
                          strokeWidth={2.5}
                        />
                        <span className="leading-relaxed text-slate-700 dark:text-slate-300">
                          {feature}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>

                {/* CTA Button Hierarchy: Solid fill on featured vs. ghost/outline on adjacent */}
                <a
                  href={APP_AUTH_URL}
                  className={cn(
                    "w-full inline-flex items-center justify-center gap-2 rounded-xl transition-all hover:-translate-y-0.5 active:scale-[0.98]",
                    plan.featured
                      ? "px-5 py-4 text-sm font-bold bg-[#99753a] hover:bg-[#85632f] text-white shadow-lg shadow-[#99753a]/25 dark:shadow-xl dark:shadow-black/40"
                      : "px-5 py-3.5 text-sm font-semibold border border-slate-300 dark:border-white/10 text-slate-700 dark:text-slate-200 bg-white dark:bg-[#1C294A] hover:bg-slate-100 dark:hover:bg-[#22335C]",
                  )}
                >
                  <span>{plan.cta}</span>
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
      <Reveal delay={120} className="mt-12">
        <div className="rounded-2xl bg-white dark:bg-[#131E3A] border border-slate-200 dark:border-white/5 p-5 flex flex-wrap items-center justify-center gap-x-8 gap-y-3 shadow-sm">
          {INCLUDED.map((item) => (
            <span
              key={item}
              className="inline-flex items-center gap-2 text-xs font-semibold text-slate-800 dark:text-slate-200"
            >
              <ShieldCheck className="text-[#99753a]" size={16} />
              {item}
            </span>
          ))}
        </div>
        <p className="text-center text-xs text-slate-500 dark:text-slate-400 mt-4 leading-relaxed">
          Indicative India pricing, exclusive of GST. Volume discounts from
          2,500 students; non-profit and trust-run schools get special rates.
        </p>
      </Reveal>
    </section>
  );
}
