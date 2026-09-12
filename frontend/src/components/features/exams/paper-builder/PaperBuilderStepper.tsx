"use client";

// ============================================================
// PaperBuilderStepper — grouped step chips (§1.0's 16 steps)
// Shows ✓ done, • current, and lock state for invalid steps.
// ============================================================

import type { PaperBuilderStep } from "@/types/exam-builder";
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
    const groups = [...new Set(PAPER_STEPS.map((s) => s.group))];
    const active = PAPER_STEPS.find((s) => s.id === activeId);

    return (
        <div className="rounded-md border p-3">
            <p className="mb-2 text-sm font-medium">
                Step {active?.stepNo ?? 1} of {PAPER_STEPS.length} — {active?.title ?? ""}
            </p>
            <div className="grid gap-2">
                {groups.map((g) => (
                    <div key={g} className="flex flex-wrap items-center gap-1">
                        <span className="text-muted-foreground mr-1 w-20 text-xs font-semibold uppercase">
                            {g}
                        </span>
                        {PAPER_STEPS.filter((s) => s.group === g).map((s) => {
                            const ok = isValid(s.id);
                            const isActive = s.id === activeId;
                            return (
                                <button
                                    key={s.id}
                                    type="button"
                                    onClick={() => onSelect(s.id)}
                                    className={`rounded-full border px-2 py-0.5 text-xs transition-colors ${
                                        isActive
                                            ? "bg-primary text-primary-foreground border-primary"
                                            : ok
                                                ? "border-emerald-300 text-emerald-700 hover:bg-emerald-50"
                                                : "text-muted-foreground border-border hover:bg-muted"
                                    }`}
                                    title={ok ? "Complete" : "Needs attention"}
                                >
                                    {ok && !isActive ? "✓ " : ""}
                                    {s.stepNo}. {s.title}
                                </button>
                            );
                        })}
                    </div>
                ))}
            </div>
        </div>
    );
}