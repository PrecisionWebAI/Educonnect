"use client";

// ============================================================
// BlueprintStep — Step 2: Exam Blueprint (blueprint §1.5+§1.6+§1.7
// +§1.4 merged into ONE step). Runs top to bottom:
//   ① Exam Blueprint — sections × counts × marks, live balance
//   ② Distribution — marks or % per chapter + topic splits with
//      Random buckets at chapter level and topic level
//   ③ Coverage Module — auto-derived from the Distribution plan.
// ============================================================

import { Button, Select } from "@/components/ui";
import type { BlueprintSection, QuestionType } from "@/types/exam-builder";
import { QUESTION_TYPE_LABELS } from "@/types/exam-builder";
import type { PaperBuilderApi } from "../usePaperBuilder";
import {
    blueprintTotal,
    chapterLevelRandom,
    distributionAllocated,
    distributionToCoverage,
} from "../usePaperBuilder";
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

    return (
        <div className="grid gap-4">
            {/* ① Exam Blueprint — section types × counts × marks */}
            <div className="rounded-md border p-4">
                <p className="text-sm font-semibold">Exam Blueprint</p>
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
{/* ② Distribution — marks/% per chapter with two-level Random */}
            <DistributionStep builder={builder} />

            {/* ③ Coverage Module — derived from the Distribution plan */}
            <div className="rounded-md border p-4">
                <p className="text-sm font-semibold">Coverage Module</p>
                <p className="mt-1 text-sm text-muted-foreground">
                    Auto-derived from the Distribution plan above — percentages convert to marks
                    of {totalMarks}.
                </p>

                <div className="mt-3 grid gap-1 text-sm">
                    {builder.state.distribution.chapters.map((c) => {
                        const target =
                            builder.state.distribution.mode === "marks"
                                ? c.assigned
                                : Math.round((c.assigned / 100) * totalMarks);
                        const pct = totalMarks > 0 ? Math.round((target / totalMarks) * 100) : 0;
                        return (
                            <div
                                key={c.chapter}
                                className="flex items-center justify-between gap-3 rounded border p-1.5"
                            >
                                <span className="truncate font-medium">{c.chapter}</span>
                                <span className="text-muted-foreground tabular-nums">
                                    {target} marks ({pct}%)
                                </span>
                            </div>
                        );
                    })}
                    {distributionAllocated(builder.state.distribution) === 0 && (
                        <p className="text-xs text-muted-foreground">
                            Nothing assigned yet — all {totalMarks} marks will come from the
                            Random bucket.
                        </p>
                    )}
                    <ChapterRandomRow builder={builder} totalMarks={totalMarks} />
                </div>

                <div className="mt-3">
                    <CoverageCharts
                        builder={builder}
                        availableChapters={builder.state.basics.chapters}
                    />
                </div>
            </div>
        </div>
    );
}
function ChapterRandomRow({
    builder,
    totalMarks,
}: {
    builder: PaperBuilderApi;
    totalMarks: number;
}) {
    const dist = builder.state.distribution;
    const merged = distributionToCoverage(dist, totalMarks);
    const chapRandom = chapterLevelRandom(dist, totalMarks);
    const randomInMarks =
        dist.mode === "marks" ? chapRandom : Math.round((chapRandom / 100) * totalMarks);
    const overflow = distributionAllocated(dist) > (dist.mode === "marks" ? totalMarks : 100);

    if (overflow) {
        return (
            <p className="text-xs text-red-500">
                ⚠ Distribution exceeds {dist.mode === "marks" ? totalMarks : 100}
                {dist.mode === "marks" ? " marks" : "%"} — fix the Distribution plan above.
            </p>
        );
    }
    if (distributionAllocated(dist) === 0) return null;
    return (
        <div className="flex items-center justify-between gap-3 rounded border border-dashed p-1.5">
            <span className="font-medium">Random (unassigned)</span>
            <span className="tabular-nums">
                {randomInMarks} marks · {chapRandom}
                {dist.mode === "percent" ? "%" : ""} · coverage {merged.totalAllocated}/
                {totalMarks}
            </span>
        </div>
    );
}