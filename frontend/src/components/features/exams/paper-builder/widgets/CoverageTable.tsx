"use client";

// ============================================================
// CoverageTable — per-chapter coverage editor for blueprint §1.4
// Mode B = marks-wise, Mode C = percentage-wise (converted live).
// ============================================================

import { Button, Select } from "@/components/ui";
import type { CoverageMode, CoveragePlan } from "@/types/exam-builder";
import { coverageToMarks } from "../usePaperBuilder";

// TEMP: hard-coded demo chapters for the Auto-mode preview.
// Remove once real chapter selection feeds the distribution.
const DEMO_AUTO_DISTRIBUTION = [
    { chapter: "Ch 1 — Microorganisms", marks: 8, total: 30 },
    { chapter: "Ch 2 — Metals & Non-metals", marks: 10, total: 30 },
    { chapter: "Ch 3 — Force & Pressure", marks: 6, total: 30 },
    { chapter: "Ch 4 — Light", marks: 6, total: 30 },
];

export default function CoverageTable({
    plan,
    totalMarks,
    availableChapters,
    onModeChange,
    onAddChapter,
    onUpdateChapter,
    onRemoveChapter,
}: {
    plan: CoveragePlan;
    totalMarks: number;
    availableChapters: string[];
    onModeChange: (m: CoverageMode) => void;
    onAddChapter: (chapter: string) => void;
    onUpdateChapter: (idx: number, c: Partial<CoveragePlan["chapters"][number]>) => void;
    onRemoveChapter: (chapter: string) => void;
}) {
    const converted = coverageToMarks(plan.mode, plan.chapters, totalMarks);
    const allocated = converted.reduce((s, c) => s + c.targetMarks, 0);
    const isPercent = plan.mode === "percent";
    const unit = isPercent ? "%" : "marks";

    return (
        <div className="rounded-md border p-4">
            <div className="flex items-center justify-between gap-2">
                <span className="text-sm font-medium">Coverage mode</span>
                <Select
                    value={plan.mode}
                    onChange={(e) => onModeChange(e.target.value as CoverageMode)}
                >
                    <option value="auto">Auto (default — simple flow)</option>
                    <option value="marks">Marks-wise per chapter (Mode B)</option>
                    <option value="percent">Percentage-wise per chapter (Mode C)</option>
                </Select>
            </div>

            {plan.mode !== "auto" && (
                <>
                    <Select
                        className="mt-3"
                        label="Add chapter"
                        value=""
                        onChange={(e) => {
                            if (e.target.value) {
                                onAddChapter(e.target.value);
                                (e.target as HTMLSelectElement).value = "";
                            }
                        }}
                    >
                        <option value="">Select chapter…</option>
                        {availableChapters
                            .filter((c) => !plan.chapters.some((pc) => pc.chapter === c))
                            .map((c) => (
                                <option key={c} value={c}>
                                    {c}
                                </option>
                            ))}
                    </Select>

                    {plan.chapters.length === 0 ? (
                        <p className="mt-3 text-sm text-muted-foreground">
                            Add at least one chapter and allocate marks (total must equal{" "}
                            {totalMarks}).
                        </p>
                    ) : (
                        <div className="mt-3 grid gap-2">
                            {plan.chapters.map((ch, idx) => {
                                const mc = converted[idx];
                                return (
                                    <div
                                        key={ch.chapter}
                                        className="flex items-center gap-2 rounded border p-2"
                                    >
                                        <span className="w-40 text-sm font-medium">
                                            {ch.chapter}
                                        </span>
                                        <input
                                            type="number"
                                            className="border-input h-8 w-24 rounded-md border bg-transparent px-2 text-sm"
                                            value={String(mc.targetMarks)}
                                            min={0}
                                            onChange={(e) =>
                                                onUpdateChapter(idx, {
                                                    auto: false,
                                                    targetMarks: Math.max(0, Number(e.target.value)),
                                                })
                                            }
                                        />
                                        <span className="text-xs text-muted-foreground">{unit}</span>
                                        <Button
                                            variant="ghost"
                                            size="sm"
                                            onClick={() => onRemoveChapter(ch.chapter)}
                                        >
                                            ✕
                                        </Button>
                                    </div>
                                );
                            })}
                            <div
                                className={`text-sm ${allocated === totalMarks ? "text-emerald-700" : "text-amber-700"}`}
                            >
                                Allocated: <b>{allocated}</b>{" "}
                                {allocated === totalMarks ? "✅" : `of ${totalMarks}`}
                            </div>
                        </div>
                    )}
                </>
            )}

            {plan.mode === "auto" && (
                <>
                    <p className="mt-3 text-sm text-muted-foreground">
                        No per-chapter plan — the system distributes marks automatically across the
                        selected chapters. This is the original simple flow.
                    </p>

                    {/* TEMP: hard-coded demo preview of the auto distribution.
                        Remove once real chapter selection feeds this. */}
                    <div className="mt-3 rounded-md border border-dashed p-3">
                        <p className="text-muted-foreground text-xs font-medium uppercase tracking-wide">
                            Demo preview — auto distribution
                            <span className="bg-amber-100 text-amber-800 ml-2 rounded-full px-2 py-0.5 text-[10px] font-medium normal-case">
                                Demo data
                            </span>
                        </p>
                        <div className="mt-2 grid gap-1.5">
                            {DEMO_AUTO_DISTRIBUTION.map((d) => (
                                <div
                                    key={d.chapter}
                                    className="flex items-center gap-2 text-sm"
                                >
                                    <span className="w-44 shrink-0 text-muted-foreground">
                                        {d.chapter}
                                    </span>
                                    <div className="bg-muted h-2 flex-1 overflow-hidden rounded-full">
                                        <div
                                            className="bg-primary h-full rounded-full"
                                            style={{ width: `${(d.marks / d.total) * 100}%` }}
                                        />
                                    </div>
                                    <span className="w-20 shrink-0 text-right font-medium tabular-nums">
                                        {d.marks} marks
                                    </span>
                                </div>
                            ))}
                        </div>
                        <p className="text-muted-foreground mt-2 text-xs">
                            Shown with sample chapters — once chapters are selected in Step 1, the
                            {totalMarks} marks are split proportionally across them.
                        </p>
                    </div>
                </>
            )}
        </div>
    );
}