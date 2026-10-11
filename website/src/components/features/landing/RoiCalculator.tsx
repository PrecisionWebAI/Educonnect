"use client";

import React, { useState } from "react";
import { ArrowRight, CheckCircle } from "lucide-react";
import Reveal from "./Reveal";

const APP_AUTH_URL = process.env.NEXT_PUBLIC_APP_URL || "http://localhost:3000";

export default function RoiCalculator() {
  const [students, setStudents] = useState(1200);

  const savingsNum = Math.round((students * 480) / 100000);
  const savingsDec = Math.round(((students * 480) % 100000) / 10000);
  const savingsStr = `₹${savingsNum}.${savingsDec}L`;
  const hoursSaved = Math.round(students * 0.45);
  const monthlyTier = Math.round(students * 24).toLocaleString();

  return (
    <section
      className="py-20 sm:py-24 px-4 sm:px-6 max-w-7xl mx-auto"
      id="calculator"
    >
      <div className="rounded-3xl p-8 sm:p-14 text-slate-900 dark:text-slate-50 relative overflow-hidden border border-slate-200/80 dark:border-white/5 bg-white/95 dark:bg-[#131E3A] shadow-xl shadow-slate-200/50 dark:shadow-2xl dark:shadow-black/50 transition-colors">
        <div className="relative z-10 grid grid-cols-1 lg:grid-cols-12 gap-10 items-center">
          {/* Left Explainer */}
          <div className="lg:col-span-6 space-y-4">
            <Reveal>
              <span className="px-3.5 py-1.5 rounded-full text-xs font-semibold uppercase tracking-wider bg-[#99753a]/10 text-[#99753a] border border-[#99753a]/25 dark:bg-[#99753a]/15 dark:text-[#99753a] dark:border-[#99753a]/30">
                Interactive Fee Calculator
              </span>
              <h2 className="text-3xl sm:text-4xl font-extrabold text-slate-900 dark:text-slate-50 tracking-tight leading-tight font-heading mt-3">
                Calculate Your School&apos;s Operational ROI &amp; Savings
              </h2>
              <p className="text-slate-600 dark:text-slate-300 text-base leading-relaxed mt-3">
                Drag the slider to match your school&apos;s total student
                enrollment. See instant calculations for projected
                administrative hours saved, fee leakage reduction, and
                predictable monthly platform costs.
              </p>
              <div className="pt-4 space-y-2.5 text-sm text-slate-700 dark:text-slate-300">
                <div className="flex items-center gap-2.5">
                  <CheckCircle className="text-[#99753a] shrink-0" size={18} />
                  <span>
                    Includes unlimited teacher, parent, and student accounts
                  </span>
                </div>
                <div className="flex items-center gap-2.5">
                  <CheckCircle className="text-[#99753a] shrink-0" size={18} />
                  <span>
                    Dedicated onboarding engineer and legacy data import
                  </span>
                </div>
                <div className="flex items-center gap-2.5">
                  <CheckCircle className="text-[#99753a] shrink-0" size={18} />
                  <span>Zero hidden SMS or payment gateway surcharges</span>
                </div>
              </div>
            </Reveal>
          </div>

          {/* Right: Interactive Slider & Dynamic Card */}
          <div className="lg:col-span-6">
            <Reveal delay={120}>
              <div className="p-6 sm:p-8 rounded-2xl border border-slate-200/80 dark:border-white/5 space-y-6 bg-slate-50/80 dark:bg-[#1C294A] shadow-sm transition-colors">
                {/* Slider Control */}
                <div>
                  <div className="flex justify-between items-center mb-3">
                    <label
                      className="text-sm font-semibold text-slate-800 dark:text-slate-200"
                      htmlFor="student-slider"
                    >
                      Student Enrollment
                    </label>
                    <span
                      className="px-3.5 py-1 rounded-lg text-sm font-bold bg-[#99753a] text-white shadow-sm shadow-[#99753a]/20 dark:shadow-md dark:shadow-black/40 transition-transform duration-150"
                      id="student-count-badge"
                    >
                      {students.toLocaleString()} Students
                    </span>
                  </div>
                  <input
                    className="w-full h-2.5 bg-slate-200 dark:bg-[#0B1221] rounded-lg appearance-none cursor-pointer accent-[#99753a] transition-all"
                    id="student-slider"
                    max="5000"
                    min="100"
                    step="50"
                    type="range"
                    value={students}
                    onChange={(e) => setStudents(Number(e.target.value))}
                  />
                  <div className="flex justify-between text-xs text-slate-500 dark:text-slate-400 mt-2 font-medium">
                    <span>100</span>
                    <span>1,000</span>
                    <span>2,500</span>
                    <span>5,000+</span>
                  </div>
                </div>

                {/* Calculated Results Grid */}
                <div className="grid grid-cols-3 gap-3 pt-2">
                  <div className="p-3.5 rounded-xl border border-slate-200/70 dark:border-white/5 text-center bg-white dark:bg-[#131E3A] shadow-sm">
                    <p className="text-xs text-slate-500 dark:text-slate-400 mb-1 font-medium">
                      Estimated Savings
                    </p>
                    <p className="text-xl sm:text-2xl font-black text-emerald-700/80 dark:text-emerald-400/80 transition-all font-heading">
                      {savingsStr}
                    </p>
                    <p className="text-[10px] text-slate-400 dark:text-slate-400 mt-0.5">
                      per academic year
                    </p>
                  </div>
                  <div className="p-3.5 rounded-xl border border-slate-200/70 dark:border-white/5 text-center bg-white dark:bg-[#131E3A] shadow-sm">
                    <p className="text-xs text-slate-500 dark:text-slate-400 mb-1 font-medium">
                      Admin Hours Saved
                    </p>
                    <p className="text-xl sm:text-2xl font-black text-[#99753a] transition-all font-heading">
                      {hoursSaved} hrs/mo
                    </p>
                    <p className="text-[10px] text-slate-400 dark:text-slate-400 mt-0.5">
                      desk paperwork
                    </p>
                  </div>
                  <div className="p-3.5 rounded-xl border border-slate-200/70 dark:border-white/5 text-center bg-white dark:bg-[#131E3A] shadow-sm">
                    <p className="text-xs text-slate-500 dark:text-slate-400 mb-1 font-medium">
                      Platform Tier
                    </p>
                    <p className="text-xl sm:text-2xl font-black text-slate-900 dark:text-slate-50 transition-all font-heading">
                      ₹{monthlyTier}/mo
                    </p>
                    <p className="text-[10px] text-slate-400 dark:text-slate-400 mt-0.5">
                      ₹24 / student
                    </p>
                  </div>
                </div>

                {/* Action Button */}
                <div className="pt-2">
                  <a
                    className="w-full py-3.5 px-4 rounded-xl font-bold text-white bg-[#99753a] hover:bg-[#85632f] shadow-md shadow-[#99753a]/20 dark:shadow-xl dark:shadow-black/40 flex items-center justify-center gap-2 transition-all hover:-translate-y-0.5 active:scale-[0.98] group text-sm"
                    href={APP_AUTH_URL}
                  >
                    <span>Request Custom Campus Quote</span>
                    <ArrowRight
                      className="transition-transform group-hover:translate-x-1"
                      size={18}
                    />
                  </a>
                </div>
              </div>
            </Reveal>
          </div>
        </div>
      </div>
    </section>
  );
}
