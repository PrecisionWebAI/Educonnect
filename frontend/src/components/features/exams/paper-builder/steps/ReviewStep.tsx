"use client";

// ============================================================
// ReviewStep — blueprint §1.14 (Step 11: Teacher Review)
// After generation, the teacher keeps full control: LOCK · DELETE ·
// ADD a custom question · attach an image (any of the §1.10 ways) ·
// regenerate. Custom questions and images are added HERE, at the end.
// ============================================================

import { useState } from "react";
import { Button, Modal } from "@/components/ui";
import { useToast } from "@/components/ui/toast";
import { addCustomQuestion, updateQuestion } from "@/services/exam-builder.service";
import type { Difficulty, QuestionDraft } from "@/types/exam-builder";
import type { PaperBuilderApi } from "../usePaperBuilder";
import QuestionCard from "../widgets/QuestionCard";
import QuestionEditorModal from "../widgets/QuestionEditorModal";
import ImagePicker from "../widgets/ImagePicker";

export default function ReviewStep({ builder }: { builder: PaperBuilderApi }) {
    const { push } = useToast();
    const [editing, setEditing] = useState<QuestionDraft | undefined>(undefined);
    const [adding, setAdding] = useState(false);
    const [imageTarget, setImageTarget] = useState<QuestionDraft | undefined>(undefined);
    const s = builder.state;
    const all = [...s.customQuestions, ...s.generatedQuestions];

    // ---- Backend persistence (File 19/20) ----
    // Local state pehle update hota hai (UI instant), phir backend call.
    // Draft server par nahi hai (paperId nahi) to sirf local rahega —
    // is beech UI block nahi karte, kyunki generate hone se pehle
    // paperId milta hi nahi.

    async function persistCustom(q: QuestionDraft, isEdit: boolean) {
        const paperId = s.paperId;
        if (!paperId) return;
        if (isEdit) {
            // PATCH: marks/text/answer/topic/chapter (backend ka QuestionPatch)
            const res = await updateQuestion(paperId, q.id, {
                mark: q.marks,
                text: q.text,
                answer: q.answer,
                topic: q.topic,
                chapter: q.chapter,
                locked: q.locked,
            });
            if (res.source === "mock") push("error", res.error ?? "Save failed");
            else push("success", "Question updated on server");
            return;
        }
        const res = await addCustomQuestion(paperId, q);
        if (res.source === "mock") push("error", res.error ?? "Save failed");
        else push("success", "Question saved to paper (part B)");
    }

    async function persistLock(q: QuestionDraft) {
        const paperId = s.paperId;
        if (!paperId) return;
        const res = await updateQuestion(paperId, q.id, { locked: !q.locked });
        if (res.source === "mock") push("error", res.error ?? "Lock save failed");
    }

    // Regenerate: backend ek job banata hai (slow). Yahan sirf trigger +
    // local flag; poora progress Step 9 (Generate) mein dikhta hai.
    async function persistRegenerate(q: QuestionDraft) {
        const paperId = s.paperId;
        if (!paperId) return;
        const res = await updateQuestion(paperId, q.id, { regenerate: true });
        if (res.source === "mock") push("error", res.error ?? "Regenerate failed");
        else push("info", "Regeneration queued — progress Step 9 mein dekho");
    }

    // Blueprint §1.14 — Rebalance / Check Blueprint dashboard
    const diffCount = { Easy: 0, Medium: 0, Hard: 0 } as Record<string, number>;
    all.forEach((q) => (diffCount[q.difficulty] = (diffCount[q.difficulty] ?? 0) + 1));
    const typeCount = all.reduce<Record<string, number>>((acc, q) => {
        acc[q.type] = (acc[q.type] ?? 0) + 1;
        return acc;
    }, {});
    const coverageChecks = builder.coverageChecks;

    return (
        <div className="grid gap-3">
            <div className="rounded-md border p-3 text-sm">
                <p className="mb-2 font-medium">Rebalance / Check Blueprint</p>
                <div className="grid gap-x-6 gap-y-1 md:grid-cols-2">
                    <p>
                        Total: <b>{builder.totalPlanned}</b>/{s.basics.totalMarks}{" "}
                        {builder.balanced ? "✅" : "⚠"}
                    </p>
                    <p>
                        Difficulty:{" "}
                        {(Object.keys(diffCount) as Difficulty[]).map((d) => {
                            const pct = all.length ? Math.round((diffCount[d] / all.length) * 100) : 0;
                            return `${d} ${pct}% `;
                        })}
                        {all.length > 0 ? "✅" : ""}
                    </p>
                    <p>
                        Types:{" "}
                        {Object.entries(typeCount)
                            .map(([t, n]) => `${t} ${n}`)
                            .join(" · ") || "—"}
                    </p>
                    <p>
                        Teacher vs AI: Custom {s.customQuestions.length} · AI{" "}
                        {s.generatedQuestions.length}
                    </p>
                </div>
                {coverageChecks.length > 0 && coverageChecks.some((c) => c.target > 0) && (
                    <div className="mt-2 border-t pt-2">
                        <p className="text-xs font-medium">Coverage per chapter:</p>
                        {coverageChecks.map((c) => (
                            <p key={c.chapter} className="text-xs">
                                {c.chapter}: target {c.target}, got {c.got}{" "}
                                {c.ok ? "✅" : "⚠ → [Rebalance]"}
                            </p>
                        ))}
                    </div>
                )}
            </div>
            <div className="flex items-center justify-between gap-2">
                <p className="text-sm text-muted-foreground">
                    {all.length} question(s) · {builder.totalPlanned}/{builder.state.basics.totalMarks}{" "}
                    marks {builder.balanced ? "✅" : "⚠"}. Lock questions to keep them across
                    regenerations.
                </p>
                <Button
                    variant="primary"
                    size="sm"
                    onClick={() => {
                        setEditing(undefined);
                        setAdding(true);
                    }}
                >
                    + Add My Question
                </Button>
            </div>
            {all.length === 0 ? (
                <p className="rounded-md border p-4 text-sm text-muted-foreground">
                    Nothing here yet — generate a draft in Step 9, or add one of your own with
                    "+ Add My Question". Add an image on any question with the 🖼 button.
                </p>
            ) : (
                <div className="grid gap-2">
                    {all.map((q) => (
                        <QuestionCard
                            key={q.id}
                            question={q}
                            onEdit={setEditing}
                            onRegenerate={(x) => {
                                builder.regenerateQuestion(x.id);
                                void persistRegenerate(x);
                            }}
                            onDelete={(x) =>
                                x.origin === "teacher"
                                    ? builder.removeCustomQuestion(x.id)
                                    : builder.deleteQuestion(x.id)
                            }
                            onToggleLock={(x) => {
                                builder.toggleLock(x.id);
                                void persistLock(x);
                            }}
                            onSwapImage={(x) => setImageTarget(x)}
                        />
                    ))}
                </div>
            )}
            <QuestionEditorModal
                open={adding || Boolean(editing)}
                editing={editing}
                totalMarks={builder.state.basics.totalMarks}
                aiBudget={builder.aiBudget}
                availableChapters={builder.state.basics.chapters}
                onClose={() => {
                    setAdding(false);
                    setEditing(undefined);
                }}
                onSave={(q) => {
                    if (q.origin === "teacher") {
                        if (editing) {
                            builder.removeCustomQuestion(editing.id);
                            builder.addCustomQuestion({ ...q, id: editing.id });
                            void persistCustom({ ...q, id: editing.id }, true);
                        } else {
                            builder.addCustomQuestion(q);
                            void persistCustom(q, false);
                        }
                    } else {
                        builder.upsertQuestion(q);
                        if (editing) void persistCustom(q, true);
                    }
                }}
            />
            {imageTarget && (
                <Modal
                    open
                    title="Attach image to question"
                    onClose={() => setImageTarget(undefined)}
                >
                    <p className="mb-3 text-sm text-muted-foreground">
                        {imageTarget.origin === "teacher" ? "Custom" : "AI"} ·{" "}
                        {imageTarget.text.slice(0, 90)}…
                    </p>
                    <ImagePicker
                        questionId={imageTarget.id}
                        current={imageTarget.image}
                        onAttach={(id, image) => {
                            builder.upsertQuestion({ ...imageTarget, image });
                            setImageTarget(undefined);
                        }}
                    />
                </Modal>
            )}
            <div className="modal-actions">
                <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                        // keep locked, regenerate the rest
                        const keep = builder.state.generatedQuestions.filter((q) => q.locked);
                        builder.setGenerated(keep);
                    }}
                >
                    Keep locked only
                </Button>
            </div>
        </div>
    );
}