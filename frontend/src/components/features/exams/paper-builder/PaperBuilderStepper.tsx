"use client";

// ============================================================
// PaperBuilderStepper — card-style step tiles (image wala look).
// Har step ek dark rounded card: number + title, subtle border.
// Active card highlighted, done cards ✓ tick, upcoming dim.
// ============================================================

import { PAPER_STEPS } from "@/types/exam-builder";

export default function PaperBuilderStepper({
    activeId,
    onSelect,
    isValid,
}: {
    activeId: string;
    onSelect: (id: string) => void;
    isValid: (id: string) => boolean;
}) {
    const activeIdx = PAPER_STEPS.findIndex((s) => s.id === activeId);

    return (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
            {PAPER_STEPS.map((s, i) => {
                const ok = isValid(s.id);
                const isActive = s.id === activeId;
                const isDone = i < activeIdx && ok;
                return (
                    <button
                        key={s.id}
                        type="button"
                        onClick={() => onSelect(s.id)}
                        title={ok ? "Complete" : "Needs attention"}
                        className={`rounded-xl border p-4 text-left transition-colors ${
                            isActive
                                ? "border-primary bg-primary/10 ring-1 ring-primary"
                                : isDone
                                  ? "border-emerald-500/40 bg-emerald-500/5 hover:bg-emerald-500/10"
                                  : "border-border bg-card hover:bg-muted"
                        }`}
                    >
                        <span
                            className={`text-sm font-semibold ${
                                isActive
                                    ? "text-primary"
                                    : isDone
                                      ? "text-emerald-600"
                                      : "text-muted-foreground"
                            }`}
                        >
                            {isDone ? "✓ " : ""}
                            {s.title}
                        </span>
                    </button>
                );
            })}
        </div>
    );
}