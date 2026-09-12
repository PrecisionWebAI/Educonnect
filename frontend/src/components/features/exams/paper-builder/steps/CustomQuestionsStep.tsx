"use client";

// ============================================================
// CustomQuestionsStep — blueprint §1.9 (Step 9)
// Teacher custom questions + recommended marks + list.
// ============================================================

import { useState } from "react";
import { Button, Badge } from "@/components/ui";
import type { QuestionDraft } from "@/types/exam-builder";
import type { PaperBuilderApi } from "../usePaperBuilder";
import QuestionEditorModal from "../widgets/QuestionEditorModal";
import QuestionCard from "../widgets/QuestionCard";

export default function CustomQuestionsStep({ builder }: { builder: PaperBuilderApi }) {
    const [modal, setModal] = useState(false);
    const [editing, setEditing] = useState<QuestionDraft | undefined>(undefined);
    const chapters = builder.state.basics.chapters.length
        ? builder.state.basics.chapters
        : builder.state.coverage.chapters.map((c) => c.chapter);

    return (
        <div className="grid gap-3">
            <div className="flex items-center justify-between">
                <p className="text-sm text-muted-foreground">
                    {builder.state.customQuestions.length} custom question(s) —{" "}
                    {builder.customMarks} mark(s) used of {builder.state.basics.totalMarks}.
                </p>
                <Button
                    variant="primary"
                    size="sm"
                    onClick={() => {
                        setEditing(undefined);
                        setModal(true);
                    }}
                >
                    + Add Question (Mine)
                </Button>
            </div>

            {builder.state.customQuestions.length === 0 ? (
                <p className="rounded-md border p-4 text-sm text-muted-foreground">
                    No custom questions yet. Add your own question (the AI suggests marks; the
                    live bar re-balances the AI budget automatically).
                </p>
            ) : (
                <div className="grid gap-2">
                    {builder.state.customQuestions.map((q) => (
                        <QuestionCard
                            key={q.id}
                            question={q}
                            onEdit={(x) => {
                                setEditing(x);
                                setModal(true);
                            }}
                            onDelete={(x) => builder.removeCustomQuestion(x.id)}
                        />
                    ))}
                </div>
            )}

            <QuestionEditorModal
                open={modal}
                editing={editing}
                totalMarks={builder.state.basics.totalMarks}
                aiBudget={builder.aiBudget}
                availableChapters={chapters}
                onClose={() => setModal(false)}
                onSave={(q) => {
                    if (editing) {
                        builder.removeCustomQuestion(editing.id);
                        builder.addCustomQuestion({ ...q, id: editing.id });
                    } else {
                        builder.addCustomQuestion(q);
                    }
                }}
            />
        </div>
    );
}