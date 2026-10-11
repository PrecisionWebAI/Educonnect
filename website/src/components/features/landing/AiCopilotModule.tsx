"use client";

import React, { useEffect, useState } from "react";
import { Bot, Sparkles } from "lucide-react";
import TiltCard from "./TiltCard";
import { cn } from "@/lib/utils";

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

export default function AiCopilotModule({
  className,
}: { className?: string } = {}) {
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
    <TiltCard
      className={cn(
        "bg-white/95 dark:bg-[#1C294A] p-8 sm:p-10 rounded-3xl relative overflow-hidden flex flex-col justify-between border border-slate-200/80 dark:border-white/5 shadow-md shadow-slate-200/50 dark:shadow-xl dark:shadow-black/40 hover:shadow-2xl hover:dark:shadow-black/60 hover:-translate-y-1 transition-all group h-full",
        className,
      )}
    >
      <div className="max-w-xl z-10">
        <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-[#99753a]/10 text-[#99753a] text-xs font-semibold mb-4 border border-[#99753a]/25 dark:bg-[#99753a]/15 dark:text-[#99753a] dark:border-[#99753a]/30">
          <Sparkles
            className="group-hover:rotate-45 transition-transform duration-300 text-[#99753a]"
            size={15}
          />
          <span>Campus AI Copilot</span>
        </div>
        <h3 className="text-2xl sm:text-3xl text-slate-900 dark:text-slate-50 font-bold mb-3 font-heading">
          AI Assistant Copilot
        </h3>
        <p className="text-slate-600 dark:text-slate-300 mb-6 leading-relaxed">
          Your 24/7 administrative partner. Automate routine parent queries,
          draft personalized reports, and summarize meeting notes instantly with
          institutional safety.
        </p>
      </div>

      {/* Interactive Dynamic Typing & Prompt Dispatch Preview */}
      <div className="z-10 p-5 rounded-2xl bg-slate-50/80 dark:bg-[#131E3A] border border-slate-200/70 dark:border-white/5 shadow-sm">
        <div className="flex items-center gap-3 text-slate-800 dark:text-slate-100 text-sm mb-4 bg-white dark:bg-[#0B1221] p-3.5 rounded-xl border border-slate-200/60 dark:border-white/5">
          <Bot className="text-[#99753a] shrink-0" size={20} />
          <span className="italic font-medium min-h-[1.5rem] flex items-center">
            <span
              className="transition-opacity duration-300 text-slate-800 dark:text-slate-100"
              style={{ opacity: visible ? 1 : 0 }}
            >
              {current.text}
            </span>
            <span className="typewriter-cursor text-[#99753a]" />
          </span>
        </div>
        <div className="p-3.5 rounded-xl bg-white/80 dark:bg-[#0B1221] border border-slate-200/50 dark:border-white/5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500/70" />
            <span
              className="text-xs text-slate-700 dark:text-slate-300 font-medium transition-opacity duration-300"
              style={{ opacity: visible ? 1 : 0 }}
            >
              {current.status}
            </span>
          </div>
          <span className="text-xs text-[#99753a] font-semibold px-2 py-0.5 rounded bg-[#99753a]/10 border border-[#99753a]/20 dark:bg-[#99753a]/15 dark:border-[#99753a]/25">
            Processed in 1.2s
          </span>
        </div>
      </div>
    </TiltCard>
  );
}
