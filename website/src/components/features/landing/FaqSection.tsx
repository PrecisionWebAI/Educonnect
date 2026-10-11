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
      className="mx-auto max-w-4xl border-t border-slate-200/80 px-4 py-20 transition-colors sm:px-6 sm:py-24 dark:border-white/5"
    >
      <Reveal className="mx-auto mb-12 max-w-2xl text-center sm:mb-16">
        <span className="rounded-full border border-[#99753a]/25 bg-[#99753a]/10 px-3.5 py-1.5 text-xs font-semibold tracking-wider text-[#99753a] uppercase dark:border-[#99753a]/30 dark:bg-[#99753a]/15 dark:text-[#99753a]">
          Answers for Decision Makers
        </span>
        <h2 className="font-heading mt-3 mb-4 text-3xl font-extrabold tracking-tight text-slate-900 sm:text-4xl dark:text-slate-50">
          Frequently Asked Questions
        </h2>
        <p className="text-base leading-relaxed text-slate-600 sm:text-lg dark:text-slate-300">
          Everything principals, directors and IT coordinators ask us before
          switching their campus to EduConnect.
        </p>
      </Reveal>

      <div className="space-y-3.5">
        {FAQS.map((faq, index) => {
          const open = openIndex === index;
          return (
            <Reveal key={faq.question} delay={index * 50}>
              <div
                className={cn(
                  "rounded-2xl border bg-white/95 transition-all duration-300 dark:bg-[#1C294A]",
                  open
                    ? "border-[#99753a]/40 shadow-md ring-1 ring-[#99753a]/20 dark:border-[#99753a]/40 dark:shadow-xl dark:shadow-black/40 dark:ring-[#99753a]/20"
                    : "border-slate-200/80 shadow-sm hover:border-slate-300 dark:border-white/5 dark:hover:border-white/10",
                )}
              >
                <button
                  type="button"
                  onClick={() => setOpenIndex(open ? null : index)}
                  aria-expanded={open}
                  aria-controls={`faq-panel-${index}`}
                  id={`faq-trigger-${index}`}
                  className="flex w-full items-center justify-between gap-4 px-6 py-5 text-left"
                >
                  <span className="flex min-w-0 items-center gap-3">
                    <HelpCircle
                      size={18}
                      className={cn(
                        "shrink-0 transition-colors",
                        open
                          ? "text-[#99753a]"
                          : "text-slate-400 dark:text-slate-500",
                      )}
                    />
                    <span className="font-heading text-sm font-bold text-slate-900 sm:text-base dark:text-slate-50">
                      {faq.question}
                    </span>
                  </span>
                  <ChevronDown
                    size={20}
                    className={cn(
                      "shrink-0 text-slate-400 transition-transform duration-300 dark:text-slate-400",
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
                    open
                      ? "grid-rows-[1fr] opacity-100"
                      : "grid-rows-[0fr] opacity-0",
                  )}
                >
                  <div className="overflow-hidden">
                    <p className="px-6 pb-6 pl-[3.25rem] text-sm leading-relaxed text-slate-600 dark:text-slate-300">
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
      <Reveal delay={120} className="mt-12">
        <div className="flex flex-col items-center justify-between gap-6 rounded-3xl border border-slate-200/80 bg-slate-50 p-8 text-center shadow-sm sm:flex-row sm:p-10 sm:text-left dark:border-white/5 dark:bg-[#131E3A] dark:shadow-xl dark:shadow-black/30">
          <div>
            <h3 className="font-heading text-base font-bold text-slate-900 sm:text-lg dark:text-slate-50">
              Still evaluating campus options?
            </h3>
            <p className="mt-1 text-xs leading-relaxed text-slate-600 sm:text-sm dark:text-slate-300">
              Get a 20-minute walkthrough built around your board, student count
              and current systems.
            </p>
          </div>
          <div className="flex shrink-0 flex-wrap items-center justify-center gap-3">
            <a
              href="mailto:hello@educonnect.school"
              className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-xs font-semibold text-slate-700 transition-all hover:bg-slate-50 dark:border-white/10 dark:bg-[#1C294A] dark:text-slate-200 dark:hover:bg-[#22335C]"
            >
              <Mail size={15} />
              hello@educonnect.school
            </a>
            <a
              href="tel:+919876543210"
              className="inline-flex items-center gap-2 rounded-xl bg-[#99753a] px-4.5 py-2.5 text-xs font-bold text-white shadow-sm shadow-[#99753a]/20 transition-all hover:-translate-y-0.5 hover:bg-[#85632f] active:scale-[0.98] dark:shadow-md dark:shadow-black/40"
            >
              <Phone size={15} />
              Book a consultation
            </a>
          </div>
        </div>
      </Reveal>
    </section>
  );
}
