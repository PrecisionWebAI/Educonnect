"use client";

// ============================================================
// Steps 6–8: MarksStep · DistributionsStep · ConstraintsStep
// blueprint §1.6 · §1.7 · §1.8
// ============================================================

import { Input } from "@/components/ui";
import type { Difficulty, PaperConstraints } from "@/types/exam-builder";
import { DEFAULT_MARKS_BY_TYPE, QUESTION_TYPE_LABELS } from "@/types/exam-builder";
import type { PaperBuilderApi } from "../usePaperBuilder";

export function MarksStep({ builder }: { builder: PaperBuilderApi }) {
    const b = builder.state.blueprint;
    return (
        <div className="rounded-md border p-4">
            <p className="text-sm text-muted-foreground">
                Marks per question type (step 6). Edit any default; the live marks bar shows the
                running contract.
            </p>
            <div className="mt-2 grid gap-2">
                {b.map((sec) => (
                    <div key={sec.type} className="flex items-center gap-2 rounded border p-2">
                        <span className="w-52 text-sm font-medium">
                            {QUESTION_TYPE_LABELS[sec.type]}
                        </span>
                        <input
                            type="number"
                            min={1}
                            className="border-input h-8 w-16 rounded-md border bg-transparent px-2 text-sm"
                            value={String(sec.marksEach)}
                            onChange={(e) => {
                                const v = Math.max(1, Number(e.target.value));
                                builder.setBlueprint(
                                    b.map((s) =>
                                        s.type === sec.type ? { ...s, marksEach: v } : s,
                                    ),
                                );
                            }}
                        />
                        <span className="text-xs text-muted-foreground">
                            default: {DEFAULT_MARKS_BY_TYPE[sec.type]}
                        </span>
                    </div>
                ))}
            </div>
        </div>
    );
}

const DIFFS: Difficulty[] = ["Easy", "Medium", "Hard"];
const BLOOM_PRESET: { label: string; pct: number }[] = [
    { label: "Remember", pct: 20 },
    { label: "Understand", pct: 30 },
    { label: "Apply", pct: 30 },
    { label: "Analyze", pct: 20 },
];

export function DistributionsStep({ builder }: { builder: PaperBuilderApi }) {
    return (
        <div className="rounded-md border p-4">
            <p className="text-sm text-muted-foreground">
                Distribution targets (step 7). Percentages guide the generator inside chapter
                buckets when Coverage Modes B/C are active.
            </p>
            <div className="mt-2 grid gap-1 text-sm">
                <p>
                    Difficulty:{" "}
                    {DIFFS.map((d, i) => (
                        <span key={d}>
                            <b>{d}</b> {["30%", "50%", "20%"][i]}
                            {i < DIFFS.length - 1 ? " · " : ""}
                        </span>
                    ))}
                </p>
                <p>
                    Bloom:{" "}
                    {BLOOM_PRESET.map((b, i) => (
                        <span key={b.label}>
                            <b>{b.label}</b> {b.pct}%
                            {i < BLOOM_PRESET.length - 1 ? " · " : ""}
                        </span>
                    ))}
                </p>
            </div>
            <p className="mt-2 text-sm text-muted-foreground">
                Preset template for v1; the full distribution editor ships with the backend
                wiring. Current coverage mode: <b>{builder.state.coverage.mode}</b>.
            </p>
        </div>
    );
}

export function ConstraintsStep({
    constraints,
    onChange,
}: {
    constraints: PaperConstraints;
    onChange: (c: Partial<PaperConstraints>) => void;
}) {
    const toggles: { key: keyof PaperConstraints; label: string }[] = [
        { key: "noDuplicates", label: "No duplicate / near-duplicate questions" },
        { key: "noAnswerLeak", label: "No cross-answer leakage" },
        { key: "sourceOnly", label: "Source-only answers (Strict)" },
        { key: "avoidReuse", label: "Avoid questions used in previous papers" },
    ];
    return (
        <div className="rounded-md border p-4">
            {toggles.map(({ key, label }) => (
                <label key={key} className="flex items-center gap-2 py-1 text-sm">
                    <input
                        type="checkbox"
                        checked={Boolean(constraints[key])}
                        onChange={(e) => onChange({ [key]: e.target.checked })}
                    />
                    {label}
                </label>
            ))}
            <div className="mt-2 grid grid-cols-2 gap-3">
                <Input
                    label="Min application questions"
                    type="number"
                    min={0}
                    value={String(constraints.minApplication)}
                    onChange={(e) => onChange({ minApplication: Number(e.target.value) })}
                />
                <Input
                    label="Min diagram questions"
                    type="number"
                    min={0}
                    value={String(constraints.minDiagram)}
                    onChange={(e) => onChange({ minDiagram: Number(e.target.value) })}
                />
            </div>
        </div>
    );
}