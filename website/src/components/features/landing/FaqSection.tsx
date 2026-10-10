"use client";

import React, { useState } from "react";
import { ChevronDown, HelpCircle, Mail, Phone } from "lucide-react";
import Reveal from "./Reveal";
import { cn } from "@/lib/utils";

interface Faq {
    question: string;
    answer: string;
}

const FAQS: Faq[] = [
    {
        question: "How long does a typical campus rollout take?",
        answer:
            "Most schools are fully live in 24–72 hours. We import your student, staff and fee masters on day one, run a parallel week alongside your existing registers, and train each role in 45-minute sessions for principals, teachers, office and finance staff.",
    },
    {
        question: "Can you migrate our existing Excel sheets or legacy ERP data?",
        answer:
            "Yes. Our onboarding team maps your existing spreadsheets, Tally ledgers or legacy ERP exports into EduConnect — students, guardians, staff, classes, fee structures, transport routes and historical attendance. Migration is included in every plan, and we validate record counts with your office before go-live.",
    },
    {
        question: "What happens when the campus internet drops?",
        answer:
            "Attendance capture keeps working offline and syncs automatically the moment connectivity returns. Fee receipts, report cards and low-bandwidth screens are optimised for 2G/3G too, so a spotty connection never blocks the school day.",
    },
    {
        question: "How is student and parent data protected?",
        answer:
            "Every record is encrypted in transit and at rest, with role-based access control, audit trails and per-child visibility scoping. EduConnect is ISO 27001 certified, follows FERPA & GDPR data principles, and never sells or shares school data. You can export or purge your data at any time.",
    },
    {
        question: "Do parents and students need to download an app?",
        answer:
            "No app store download is required to get started — parents receive a mobile-friendly web portal link plus SMS/WhatsApp alerts. Optional Android and iOS apps are available for schools that want push notifications and bus GPS tracking.",
    },
    {
        question: "Is EduConnect aligned to CBSE, ICSE and state board formats?",
        answer:
            "Yes. Report cards, exam blueprints, co-scholastic grading and attendance registers ship with CBSE and ICSE templates out of the box, and every report template can be customised to your board's exact format — including bilingual English/Hindi output.",
    },
    {
        question: "Can we start with only a few modules?",
        answer:
            "Absolutely. Schools commonly begin with attendance, fees and the parent portal, then switch on academics, exams, library, transport and payroll as each department is ready. Modules share the same data, so nothing needs to be re-entered when you expand.",
    },
];

export default function FaqSection() {
    const [openIndex, setOpenIndex] = useState<number | null>(0);

    return (
        <section
            id="faq"
            className="py-14 sm:py-16 px-4 sm:px-6 max-w-4xl mx-auto border-t border-slate-200/80 dark:border-white/10 transition-colors"
        >
            <Reveal className="text-center max-w-2xl mx-auto mb-10 sm:mb-12">
                <span className="px-3.5 py-1 rounded-full glass-pill text-blue-600 dark:text-sky-400 font-bold text-xs uppercase tracking-wider border font-mono">
                    Answers for Decision Makers
                </span>
                <h2 className="text-3xl sm:text-4xl font-extrabold text-slate-900 dark:text-white tracking-tight mt-3 mb-4 font-heading">
                    Frequently Asked Questions
                </h2>
                <p className="text-base text-slate-600 dark:text-slate-300 leading-relaxed">
                    Everything principals, directors and IT coordinators ask us before switching their campus to
                    EduConnect OS.
                </p>
            </Reveal>

            <div className="space-y-3">
                {FAQS.map((faq, index) => {
                    const open = openIndex === index;
                    return (
                        <Reveal key={faq.question} delay={index * 50}>
                            <div
                                className={cn(
                                    "rounded-2xl border transition-all duration-300",
                                    open
                                        ? "glass-epic shadow-lg border-blue-500/30 dark:border-sky-400/30"
                                        : "glass-epic shadow-sm hover:-translate-y-0.5",
                                )}
                            >
                                <button
                                    type="button"
                                    onClick={() => setOpenIndex(open ? null : index)}
                                    aria-expanded={open}
                                    aria-controls={`faq-panel-${index}`}
                                    id={`faq-trigger-${index}`}
                                    className="w-full flex items-center justify-between gap-4 px-6 py-5 text-left"
                                >
                                    <span className="flex items-center gap-3 min-w-0">
                                        <HelpCircle
                                            size={18}
                                            className={cn(
                                                "shrink-0 transition-colors",
                                                open
                                                    ? "text-blue-600 dark:text-sky-400"
                                                    : "text-slate-400 dark:text-slate-400",
                                            )}
                                        />
                                        <span className="text-sm sm:text-base font-bold text-slate-900 dark:text-white font-heading">
                                            {faq.question}
                                        </span>
                                    </span>
                                    <ChevronDown
                                        size={20}
                                        className={cn(
                                            "shrink-0 text-slate-400 dark:text-slate-400 transition-transform duration-300",
                                            open && "rotate-180",
                                        )}
                                    />
                                </button>

                                <div
                                    id={`faq-panel-${index}`}
                                    role="region"
                                    aria-labelledby={`faq-trigger-${index}`}
                                    className={cn(
                                        "grid transition-all duration-500 ease-out",
                                        open ? "grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0",
                                    )}
                                >
                                    <div className="overflow-hidden">
                                        <p className="px-6 pb-5 pl-[3.25rem] text-sm text-slate-600 dark:text-slate-300 leading-relaxed">
                                            {faq.answer}
                                        </p>
                                    </div>
                                </div>
                            </div>
                        </Reveal>
                    );
                })}
            </div>

            {/* Still unsure? Talk to a rollout specialist */}
            <Reveal delay={120} className="mt-10">
                <div className="rounded-2xl crystalline-glass border p-6 flex flex-col sm:flex-row items-center justify-between gap-5 text-center sm:text-left">
                    <div>
                        <h3 className="text-base font-bold text-slate-900 dark:text-white font-heading">
                            Still evaluating options?
                        </h3>
                        <p className="text-xs text-slate-600 dark:text-slate-300 mt-1 leading-relaxed">
                            Get a 20-minute walkthrough built around your board, student count and current systems.
                        </p>
                    </div>
                    <div className="flex flex-wrap items-center justify-center gap-3 shrink-0">
                        <a
                            href="mailto:hello@educonnect.school"
                            className="inline-flex items-center gap-2 rounded-lg border border-slate-200 dark:border-white/10 px-4 py-2.5 text-xs font-bold text-slate-800 dark:text-white transition-all hover:-translate-y-0.5 font-mono"
                        >
                            <Mail size={15} />
                            hello@educonnect.school
                        </a>
                        <a
                            href="tel:+919876543210"
                            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 hover:bg-blue-700 px-4 py-2.5 text-xs font-bold text-white shadow-md transition-all hover:-translate-y-0.5 active:scale-[0.98] glow-parchment font-mono"
                        >
                            <Phone size={15} />
                            Book a demo
                        </a>
                    </div>
                </div>
            </Reveal>
        </section>
    );
}
