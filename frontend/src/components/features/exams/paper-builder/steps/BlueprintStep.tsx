"use client";

// ============================================================
// BlueprintStep — Step 2: Exam Blueprint (blueprint §1.5+§1.6+§1.7
// +§1.4 merged into ONE step). Runs top to bottom:
//   ① Exam Blueprint — sections × counts × marks, live balance
//   ② Marks Distribution — Default / Mark-Wise / Percentage-Wise; values
//      fill karke Save karne par hi ③ dikhta hai
//   ③ Marks / Percentage Coverage — saved distribution se derived
//      (unassigned hissa Random bucket ke roop me chart me bhi).
// ============================================================

import { Button, Select } from "@/components/ui";
import type { BlueprintSection, QuestionType } from "@/types/exam-builder";
import { QUESTION_TYPE_LABELS } from "@/types/exam-builder";
import type { PaperBuilderApi } from "../usePaperBuilder";
import { blueprintTotal, distributionToCoverage } from "../usePaperBuilder";
import DistributionStep from "./DistributionStep";
import CoverageCharts from "../widgets/CoverageCharts";

const TYPES: QuestionType[] = Object.keys(QUESTION_TYPE_LABELS) as QuestionType[];

export default function BlueprintStep({
    blueprint,
    totalMarks,
    onChange,
    builder,
}: {
    blueprint: BlueprintSection[];
    totalMarks: number;
    onChange: (b: BlueprintSection[]) => void;
    builder: PaperBuilderApi;
}) {
    function update(idx: number, patch: Partial<BlueprintSection>) {
        onChange(blueprint.map((s, i) => (i === idx ? { ...s, ...patch } : s)));
    }
    const total = blueprintTotal(blueprint);
    const bad = total !== totalMarks;
    const dist = builder.state.distribution;
    // ③ Coverage card sirf tab dikhta hai jab Marks Distribution save ho chuka ho
    const showCoverage = dist.mode !== "default" && dist.saved;
    const coveredMarks = distributionToCoverage(dist, totalMarks).totalAllocated;

    return (
        <div className="grid gap-4">
            {/* ① Exam Blueprint — section types × counts × marks */}
            <div className="rounded-md border p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="text-sm font-semibold">Exam Blueprint</p>
                    <span
                        className={`text-xs font-medium tabular-nums ${
                            bad ? "text-amber-700" : "text-emerald-700"
                        }`}
                    >
                        {total} vs {totalMarks} ({bad ? "Not matched" : "Matched"})
                    </span>
                </div>
                <div className="mt-2 grid gap-2">
                    <div className="flex items-center gap-2 px-2 text-xs font-medium text-muted-foreground">
                        <span className="flex-1">Question type</span>
                        <span className="w-16 text-center">Count</span>
                        <span className="w-4" />
                        <span className="w-16 text-center">Marks each</span>
                        <span className="w-24 text-right">Total</span>
                        <span className="w-8" />
                    </div>
                    {blueprint.map((sec, idx) => (
                        <div key={sec.type} className="flex items-center gap-2 rounded border p-2">
                            <div className="min-w-0 flex-1">
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
                            </div>
                            <input
                                type="number"
                                min={0}
                                aria-label="Count"
                                className="border-input h-8 w-16 rounded-md border bg-transparent px-2 text-sm"
                                value={String(sec.count)}
                                onChange={(e) => update(idx, { count: Math.max(0, Number(e.target.value)) })}
                            />
                            <span className="w-4 text-center text-xs text-muted-foreground">×</span>
                            <input
                                type="number"
                                min={1}
                                aria-label="Marks each"
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
                            onChange([...blueprint, { type: "Short", count: 1, marksEach: 2 }])
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
{/* ② Distribution — Default / Mark-Wise / Percentage-Wise (saved plan se coverage) */}
            <DistributionStep builder={builder} />

            {/* ③ Coverage — sirf tab dikhta hai jab teacher ne Marks Distribution
                fill karke save kiya ho (Default mode me koi coverage nahi) */}
            {showCoverage && (
                <div className="rounded-md border p-4">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                        <p className="text-sm font-semibold">
                            {dist.mode === "percent" ? "Percentage Coverage" : "Marks Coverage"}
                        </p>
                        <span className="text-xs text-muted-foreground tabular-nums">
                            {coveredMarks} of {totalMarks} marks
                        </span>
                    </div>

                    <div className="mt-3">
                        <CoverageCharts
                            builder={builder}
                            availableChapters={builder.state.basics.chapters}
                        />
                    </div>
                </div>
            )}
        </div>
    );
}
