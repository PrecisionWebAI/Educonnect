"use client";

// ============================================================
// BlueprintStep — blueprint §1.5 (Step 5: Exam Blueprint)
// Type counts × marks with live validation vs Total Marks.
// ============================================================

import { Button, Input, Select } from "@/components/ui";
import type { BlueprintSection, QuestionType } from "@/types/exam-builder";
import { QUESTION_TYPE_LABELS } from "@/types/exam-builder";
import { blueprintTotal } from "../usePaperBuilder";

const TYPES: QuestionType[] = Object.keys(QUESTION_TYPE_LABELS) as QuestionType[];

export default function BlueprintStep({
    blueprint,
    totalMarks,
    onChange,
}: {
    blueprint: BlueprintSection[];
    totalMarks: number;
    onChange: (b: BlueprintSection[]) => void;
}) {
    function update(idx: number, patch: Partial<BlueprintSection>) {
        onChange(blueprint.map((s, i) => (i === idx ? { ...s, ...patch } : s)));
    }
    const total = blueprintTotal(blueprint);
    const bad = total !== totalMarks;

    return (
        <div className="rounded-md border p-4">
            <p className="text-sm text-muted-foreground">
                Blueprint auto-validation: counts × marks must total {totalMarks} ({total}) —{" "}
                <span className={bad ? "text-amber-700" : "text-emerald-700"}>
                    {bad ? "⚠ not balanced yet" : "✅ balanced"}
                </span>
                .
            </p>
            <div className="mt-2 grid gap-2">
                {blueprint.map((sec, idx) => (
                    <div key={sec.type} className="flex items-center gap-2 rounded border p-2">
                        <Select
                            value={sec.type}
                            onChange={(e) => update(idx, { type: e.target.value as QuestionType })}
                        >
                            {TYPES.map((t) => (
                                <option key={t} value={t}>
                                    {QUESTION_TYPE_LABELS[t]}
                                </option>
                            ))}
                        </Select>
                        <input
                            type="number"
                            min={0}
                            className="border-input h-8 w-16 rounded-md border bg-transparent px-2 text-sm"
                            value={String(sec.count)}
                            onChange={(e) => update(idx, { count: Math.max(0, Number(e.target.value)) })}
                        />
                        <span className="text-xs text-muted-foreground">×</span>
                        <input
                            type="number"
                            min={1}
                            className="border-input h-8 w-16 rounded-md border bg-transparent px-2 text-sm"
                            value={String(sec.marksEach)}
                            onChange={(e) =>
                                update(idx, { marksEach: Math.max(1, Number(e.target.value)) })
                            }
                        />
                        <span className="w-24 text-right text-xs font-medium">
                            = {sec.count * sec.marksEach}
                        </span>
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => onChange(blueprint.filter((_, i) => i !== idx))}
                        >
                            ✕
                        </Button>
                    </div>
                ))}
            </div>
            <div className="mt-2 modal-actions">
                <Button
                    variant="outline"
                    size="sm"
                    onClick={() =>
                        onChange([
                            ...blueprint,
                            { type: "Short", count: 1, marksEach: 2 },
                        ])
                    }
                >
                    + Add section type
                </Button>
                <Button
                    variant="ghost"
                    size="sm"
                    disabled={!bad}
                    title="Scale counts/marks proportionally toward the target"
                    onClick={() => {
                        const target = totalMarks;
                        const cur = blueprintTotal(blueprint);
                        if (cur === 0) return;
                        const ratio = target / cur;
                        onChange(
                            blueprint.map((s) => ({
                                ...s,
                                count: Math.max(1, Math.round(s.count * ratio)),
                            })),
                        );
                    }}
                >
                    Smart Rebalance
                </Button>
            </div>
        </div>
    );
}