"use client";

import React, { useState } from "react";
import { ArrowRight, CheckCircle } from "lucide-react";

const APP_AUTH_URL = process.env.NEXT_PUBLIC_APP_URL || "http://localhost:3000";

export default function RoiCalculator() {
    const [students, setStudents] = useState(1200);

    const savingsNum = Math.round((students * 480) / 100000);
    const savingsDec = Math.round(((students * 480) % 100000) / 10000);
    const savingsStr = `₹${savingsNum}.${savingsDec}L`;
    const hoursSaved = Math.round(students * 0.45);
    const monthlyTier = Math.round(students * 24).toLocaleString();

    return (
        <section className="py-14 sm:py-16 px-4 sm:px-6 max-w-7xl mx-auto" id="calculator">
            <div
                className="glass-frosted-dark rounded-3xl p-8 sm:p-14 text-slate-900 dark:text-white relative overflow-hidden border border-white/80 dark:border-white/10 shadow-2xl transition-colors glint-surface"
                style={{
                    backdropFilter: "blur(40px) saturate(200%)",
                }}
            >
                <div
                    className="absolute -right-20 -bottom-20 w-80 h-80 rounded-full blur-3xl pointer-events-none opacity-40 dark:opacity-60 animate-ambient-2"
                    style={{
                        background: "radial-gradient(circle, rgba(13, 148, 136, 0.4) 0%, transparent 70%)",
                    }}
                />
                <div
                    className="absolute -left-20 -top-20 w-80 h-80 rounded-full blur-3xl pointer-events-none opacity-30 dark:opacity-40 animate-ambient-3"
                    style={{
                        background: "radial-gradient(circle, rgba(37, 99, 235, 0.35) 0%, transparent 70%)",
                    }}
                />

                <div className="relative z-10 grid grid-cols-1 lg:grid-cols-12 gap-10 items-center">
                    {/* Left Explainer */}
                    <div className="lg:col-span-6 space-y-4">
                        <span className="px-3.5 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-emerald-500/15 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-300 border border-emerald-500/30 font-mono">
                            Interactive Fee Calculator
                        </span>
                        <h2 className="text-3xl sm:text-4xl font-extrabold text-slate-900 dark:text-white tracking-tight leading-tight font-heading">
                            Calculate Your School&apos;s Operational ROI &amp; Savings
                        </h2>
                        <p className="text-slate-600 dark:text-slate-300 text-sm sm:text-base leading-relaxed">
                            Drag the slider to match your school&apos;s total student enrollment. See instant
                            calculations for projected administrative hours saved, fee leakage reduction, and
                            predictable monthly platform costs.
                        </p>
                        <div className="pt-4 space-y-2.5 text-xs sm:text-sm text-slate-700 dark:text-slate-200">
                            <div className="flex items-center gap-2 hover:translate-x-1 transition-transform">
                                <CheckCircle className="text-emerald-500 dark:text-emerald-400 shrink-0" size={18} />
                                <span>Includes unlimited teacher, parent, and student accounts</span>
                            </div>
                            <div className="flex items-center gap-2 hover:translate-x-1 transition-transform">
                                <CheckCircle className="text-emerald-500 dark:text-emerald-400 shrink-0" size={18} />
                                <span>Dedicated onboarding engineer and legacy data import</span>
                            </div>
                            <div className="flex items-center gap-2 hover:translate-x-1 transition-transform">
                                <CheckCircle className="text-emerald-500 dark:text-emerald-400 shrink-0" size={18} />
                                <span>Zero hidden SMS or payment gateway surcharges</span>
                            </div>
                        </div>
                    </div>

                    {/* Right: Interactive Slider & Dynamic Glass Card */}
                    <div className="lg:col-span-6">
                        <div
                            className="p-6 sm:p-8 rounded-2xl border border-white/80 dark:border-white/10 shadow-xl space-y-6 bg-white/85 dark:bg-slate-900/80 backdrop-blur-2xl transition-colors"
                        >
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
                                        className="px-3.5 py-1 rounded-lg text-sm font-extrabold bg-blue-600 text-white dark:bg-blue-500 dark:text-white shadow-md font-mono transition-transform duration-150"
                                        id="student-count-badge"
                                    >
                                        {students.toLocaleString()} Students
                                    </span>
                                </div>
                                <input
                                    className="w-full h-2.5 bg-slate-200 dark:bg-slate-800 rounded-lg appearance-none cursor-pointer accent-blue-600 dark:accent-sky-400 transition-all"
                                    id="student-slider"
                                    max="5000"
                                    min="100"
                                    step="50"
                                    type="range"
                                    value={students}
                                    onChange={(e) => setStudents(Number(e.target.value))}
                                />
                                <div className="flex justify-between text-[11px] text-slate-500 dark:text-slate-400 mt-1.5 font-medium font-mono">
                                    <span>100</span>
                                    <span>1,000</span>
                                    <span>2,500</span>
                                    <span>5,000+</span>
                                </div>
                            </div>

                            {/* Calculated Results Grid */}
                            <div className="grid grid-cols-3 gap-3 pt-2">
                                <div className="p-3.5 rounded-xl border border-slate-200/80 dark:border-white/10 text-center bg-white/90 dark:bg-slate-800/80 shadow-sm transition-all hover:scale-105">
                                    <p className="text-[11px] text-slate-500 dark:text-slate-400 mb-1 font-medium">
                                        Estimated Savings
                                    </p>
                                    <p className="text-xl sm:text-2xl font-black text-emerald-600 dark:text-emerald-400 transition-all font-heading">
                                        {savingsStr}
                                    </p>
                                    <p className="text-[9px] text-slate-400 dark:text-slate-500 mt-0.5">
                                        per academic year
                                    </p>
                                </div>
                                <div className="p-3.5 rounded-xl border border-slate-200/80 dark:border-white/10 text-center bg-white/90 dark:bg-slate-800/80 shadow-sm transition-all hover:scale-105">
                                    <p className="text-[11px] text-slate-500 dark:text-slate-400 mb-1 font-medium">
                                        Admin Hours Saved
                                    </p>
                                    <p className="text-xl sm:text-2xl font-black text-blue-600 dark:text-sky-400 transition-all font-heading">
                                        {hoursSaved} hrs/mo
                                    </p>
                                    <p className="text-[9px] text-slate-400 dark:text-slate-500 mt-0.5">
                                        desk paperwork
                                    </p>
                                </div>
                                <div className="p-3.5 rounded-xl border border-slate-200/80 dark:border-white/10 text-center bg-white/90 dark:bg-slate-800/80 shadow-sm transition-all hover:scale-105">
                                    <p className="text-[11px] text-slate-500 dark:text-slate-400 mb-1 font-medium">
                                        Platform Tier
                                    </p>
                                    <p className="text-xl sm:text-2xl font-black text-slate-900 dark:text-white transition-all font-heading">
                                        ₹{monthlyTier}/mo
                                    </p>
                                    <p className="text-[9px] text-slate-400 dark:text-slate-500 mt-0.5">
                                        ₹24 / student
                                    </p>
                                </div>
                            </div>

                            {/* Action Button */}
                            <div className="pt-2">
                                <a
                                    className="w-full py-3.5 px-4 rounded-xl font-bold text-white bg-blue-600 hover:bg-blue-700 flex items-center justify-center gap-2 transition-all hover:-translate-y-0.5 shadow-lg shadow-blue-600/30 active:scale-[0.98] group font-mono"
                                    href={APP_AUTH_URL}
                                >
                                    <span>Request Custom Campus Quote</span>
                                    <ArrowRight className="transition-transform group-hover:translate-x-1" size={18} />
                                </a>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </section>
    );
}
