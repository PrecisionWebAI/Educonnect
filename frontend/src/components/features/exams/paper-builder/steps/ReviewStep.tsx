"use client";

// ============================================================
// ReviewStep — blueprint §1.14 (Step 14: Teacher Review)
// Full question list with review actions: edit, regenerate,
// delete, lock, swap image.
// ============================================================

import { useState } from "react";
import { Button } from "@/components/ui";
import type { QuestionDraft } from "@/types/exam-builder";
import type { PaperBuilderApi } from "../usePaperBuilder";
import QuestionCard from "../widgets/QuestionCard";
import QuestionEditorModal from "../widgets/QuestionEditorModal";

export default function ReviewStep({ builder }: { builder: PaperBuilderApi }) {
    const [editing, setEditing] = useState<QuestionDraft | undefined>(undefined);
    const all = [...builder.state.customQuestions, ...builder.state.generatedQuestions];

    return (
        <div className="grid gap-3">
            <p className="text-sm text-muted-foreground">
                {all.length} question(s) · {builder.totalPlanned}/{builder.state.basics.totalMarks}{" "}
                marks {builder.balanced ? "✅" : "⚠"}. Lock questions to keep them across
                regenerations.
            </p>
            {all.length === 0 ? (
                <p className="rounded-md border p-4 text-sm text-muted-foreground">
                    Nothing to review yet — generate a draft in Step 12.
                </p>
            ) : (
                <div className="grid gap-2">
                    {all.map((q) => (
                        <QuestionCard
                            key={q.id}
                            question={q}
                            onEdit={setEditing}
                            onRegenerate={(x) => builder.regenerateQuestion(x.id)}
                            onDelete={(x) =>
                                x.origin === "teacher"
                                    ? builder.removeCustomQuestion(x.id)
                                    : builder.deleteQuestion(x.id)
                            }
                            onToggleLock={(x) => builder.toggleLock(x.id)}
                            onSwapImage={(x) => {
                                const image = {
                                    ...x.image,
                                    kind: "source" as const,
                                    caption: `${x.image?.caption ?? "image"} (swapped)`,
                                    fileUrl: `demo://swap/${x.id}`,
                                    questionImage: true,
                                };
                                builder.upsertQuestion({ ...x, image });
                            }}
                        />
                    ))}
                </div>
            )}
            <QuestionEditorModal
                open={Boolean(editing)}
                editing={editing}
                totalMarks={builder.state.basics.totalMarks}
                aiBudget={builder.aiBudget}
                availableChapters={builder.state.basics.chapters}
                onClose={() => setEditing(undefined)}
                onSave={(q) => {
                    if (editing && q.origin === "teacher") {
                        builder.removeCustomQuestion(editing.id);
                        builder.addCustomQuestion({ ...q, id: editing.id });
                    } else {
                        builder.upsertQuestion(q);
                    }
                }}
            />
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