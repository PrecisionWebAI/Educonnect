"use client";

import React, { useEffect, useState } from "react";
import { Bot, Sparkles } from "lucide-react";
import TiltCard from "./TiltCard";

const PROMPTS = [
    {
        text: '"Draft an email to parents regarding tomorrow\'s schedule change…"',
        status: "Live schedule dispatch generator active",
    },
    {
        text: '"Analyze Q2 fee reconciliation anomalies across Grade 9 & 10…"',
        status: "Audit intelligence reconciling accounts",
    },
    {
        text: '"Generate 10th Grade CBSE Mathematics Mock Paper with solution key…"',
        status: "Smart curriculum generator active",
    },
    {
        text: '"Summarize today\'s campus attendance variances across Bus Routes #1-8…"',
        status: "Real-time telemetry diagnostics synced",
    },
];

export default function AiCopilotModule() {
    const [index, setIndex] = useState(0);
    const [visible, setVisible] = useState(true);

    useEffect(() => {
        const interval = setInterval(() => {
            setVisible(false);
            setTimeout(() => {
                setIndex((prev) => (prev + 1) % PROMPTS.length);
                setVisible(true);
            }, 350);
        }, 4500);

        return () => clearInterval(interval);
    }, []);

    const current = PROMPTS[index];

    return (
        <TiltCard className="md:col-span-2 crystalline-glass p-8 rounded-3xl relative overflow-hidden flex flex-col justify-between border border-white/80 dark:border-white/10 group">
            <div className="max-w-xl z-10">
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-500/10 dark:bg-sky-400/15 text-blue-700 dark:text-sky-300 text-xs font-semibold mb-4 border border-blue-500/20 dark:border-sky-400/30 font-mono">
                    <Sparkles className="group-hover:rotate-45 transition-transform duration-300 text-blue-600 dark:text-sky-400" size={15} />
                    <span>Flagship Intelligence</span>
                </div>
                <h3 className="text-2xl sm:text-3xl text-slate-900 dark:text-white font-bold mb-3 font-heading">
                    AI Assistant Copilot
                </h3>
                <p className="text-slate-600 dark:text-slate-300 mb-6 leading-relaxed">
                    Your 24/7 administrative partner. Automate routine parent queries, draft personalized
                    reports, and summarize meeting notes instantly.
                </p>
            </div>

            {/* Interactive Dynamic Typing & Prompt Dispatch Preview */}
            <div className="z-10 p-5 rounded-2xl bg-white/90 dark:bg-slate-900/85 border border-slate-200/80 dark:border-white/10 shadow-sm">
                <div className="flex items-center gap-3 text-slate-800 dark:text-slate-100 text-sm mb-4 bg-slate-50 dark:bg-slate-800/60 p-3.5 rounded-xl border border-slate-200/60 dark:border-white/5">
                    <Bot className="text-blue-600 dark:text-sky-400 shrink-0" size={20} />
                    <span className="italic font-medium min-h-[1.5rem] flex items-center">
                        <span
                            className="transition-opacity duration-300"
                            style={{ opacity: visible ? 1 : 0 }}
                        >
                            {current.text}
                        </span>
                        <span className="typewriter-cursor text-blue-600 dark:text-sky-400" />
                    </span>
                </div>
                <div className="p-3.5 rounded-xl bg-slate-50/60 dark:bg-slate-800/40 border border-slate-200/50 dark:border-white/5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
                    <div className="flex items-center gap-2.5">
                        <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 live-beacon" />
                        <span
                            className="text-xs text-slate-800 dark:text-slate-200 font-semibold transition-opacity duration-300 font-mono"
                            style={{ opacity: visible ? 1 : 0 }}
                        >
                            {current.status}
                        </span>
                    </div>
                    <span className="text-xs text-blue-700 dark:text-sky-300 font-bold px-2 py-0.5 rounded bg-blue-500/10 dark:bg-sky-400/20 font-mono">
                        Processed in 1.2s
                    </span>
                </div>
            </div>
        </TiltCard>
    );
}
