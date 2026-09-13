"use client";

// ============================================================
// QualityStep — blueprint §1.13 (Step 13: AI Quality Check)
// Demo checks derived live from state until the backend
// quality endpoint ships.
// ============================================================

import { Badge, Button } from "@/components/ui";
import { QUESTION_TYPE_LABELS } from "@/types/exam-builder";
import type { PaperBuilderApi } from "../usePaperBuilder";

export default function QualityStep({ builder }: { builder: PaperBuilderApi }) {
    const s = builder.state;
    const generated = s.generatedQuestions;

    const counts = generated.reduce<Record<string, number>>((acc, q) => {
        acc[q.type] = (acc[q.type] ?? 0) + 1;
        return acc;
    }, {});
    const checks: { id: string; label: string; status: "pass" | "fail" | "warn"; reason?: string }[] =
        [
            {
                id: "contract",
                label: "Marks Contract balanced",
                status: builder.balanced ? "pass" : "fail",
                reason: builder.balanced
                    ? `${builder.totalPlanned} of ${s.basics.totalMarks}`
                    : `off by ${Math.abs(builder.balance)}`,
            },
            {
                id: "blueprint",
                label: "Blueprint types match generated questions",
                status: s.blueprint.every(
                    (sec) => (counts[sec.type] ?? 0) > 0 || sec.count === 0,
                )
                    ? "pass"
                    : "warn",
                reason: "Some blueprint sections have no questions yet",
            },
            {
                id: "dupes",
                label: "No duplicate question texts",
                status: new Set(generated.map((q) => q.text)).size === generated.length
                    ? "pass"
                    : "fail",
            },
            {
                id: "answers",
                label: "Every question has an expected answer",
                status: generated.every((q) => (q.answer ?? "").trim().length > 0)
                    ? "pass"
                    : "warn",
            },
            {
                id: "marksDifficulty",
                label: "Marks ↔ difficulty alignment",
                status: (() => {
                    // blueprint §1.13 heuristic: Easy ≤2 · Medium ≤4 · Hard unbounded
                    const bad = generated.filter(
                        (q) =>
                            (q.difficulty === "Easy" && q.marks > 2) ||
                            (q.difficulty === "Medium" && q.marks > 4),
                    );
                    return bad.length === 0 ? "pass" : "warn";
                })(),
                reason: "Easy > 2 marks or Medium > 4 marks looks misaligned",
            },
            {
                id: "imageSanity",
                label: "Image sanity (visual questions carry an image)",
                status: (() => {
                    const visual = new Set(["Diagram", "Map", "Graph", "LabelDiagram"]);
                    const missing = generated.filter(
                        (q) => visual.has(q.type) && !q.image?.fileUrl && !q.image?.storageKey,
                    );
                    return missing.length === 0
                        ? "pass"
                        : missing.length === generated.length && generated.length > 0
                            ? "warn"
                            : "fail";
                })(),
                reason: "Label/image match — regenerate or attach a source diagram",
            },
            {
                id: "coverage",
                label: "Chapter coverage honoured",
                status: builder.coverageChecks.every((c) => c.ok) ? "pass" : "warn",
                reason: "Per-chapter marks vs plan (Modes B/C)",
            },
        ];
    const failing = checks.filter((c) => c.status === "fail").length;

    return (
        <div className="grid gap-3">
            <div className="flex items-center justify-between">
                <Badge tone={failing === 0 ? "green" : "red"}>
                    {failing === 0 ? "All checks passed" : `${failing} check(s) failed`}
                </Badge>
                <Button
                    variant="outline"
                    size="sm"
                    onClick={() => builder.setGenerated([...generated])} // re-runs derived checks
                >
                    Re-run checks
                </Button>
            </div>
            <div className="grid gap-2">
                {checks.map((c) => (
                    <div key={c.id} className="flex items-center gap-2 rounded border p-2 text-sm">
                        <Badge
                            tone={c.status === "pass" ? "green" : c.status === "warn" ? "amber" : "red"}
                        >
                            {c.status === "pass" ? "✅ Pass" : c.status === "warn" ? "⚠ Warn" : "✖ Fail"}
                        </Badge>
                        <span>{c.label}</span>
                        {c.reason && (
                            <span className="text-muted-foreground text-xs">— {c.reason}</span>
                        )}
                    </div>
                ))}
            </div>
            <p className="text-muted-foreground text-xs">
                {generated.length} AI question(s) ·{" "}
                {Object.entries(counts)
                    .map(([t, n]) => `${n}× ${QUESTION_TYPE_LABELS[t as never] ?? t}`)
                    .join(", ") || "none yet"}
            </p>
        </div>
    );
}