"use client";

// ============================================================
// QuestionEditorModal — add/edit a teacher custom question
// (blueprint §1.9) with AI-recommended marks pre-filled.
// ============================================================

import { useState } from "react";
import { Button, Input, Modal, Select, Textarea } from "@/components/ui";
import type { Difficulty, QuestionDraft, QuestionType } from "@/types/exam-builder";
import { QUESTION_TYPE_LABELS } from "@/types/exam-builder";
import { recommendMarks } from "@/services/exam-builder.service";

const DIFFICULTIES: Difficulty[] = ["Easy", "Medium", "Hard"];

export default function QuestionEditorModal({
    open,
    editing = undefined,
    totalMarks,
    aiBudget,
    availableChapters,
    onClose,
    onSave,
}: {
    open: boolean;
    editing?: QuestionDraft;
    totalMarks: number;
    aiBudget: number;
    availableChapters: string[];
    onClose: () => void;
    onSave: (q: QuestionDraft) => void;
}) {
    const [form, setForm] = useState({
        type: "Short" as QuestionType,
        text: "",
        options: "",
        answer: "",
        difficulty: "Medium" as Difficulty,
        topic: "",
        chapter: "",
        marks: 2,
    });

    const [prevOpen, setPrevOpen] = useState(false);
    if (open && !prevOpen) {
        setPrevOpen(true);
        setForm({
            type: editing?.type ?? "Short",
            text: editing?.text ?? "",
            options: editing?.options?.join(" | ") ?? "",
            answer: editing?.answer ?? "",
            difficulty: editing?.difficulty ?? "Medium",
            topic: editing?.topic ?? "",
            chapter: editing?.chapter ?? "",
            marks: editing?.marks ?? 2,
        });
    } else if (!open && prevOpen) {
        setPrevOpen(false);
    }
function recommended() {
        return recommendMarks(form.type, form.difficulty, form.text.length);
    }

    function handleSave() {
        onSave({
            id: editing?.id ?? `tc${Date.now().toString()}`,
            type: form.type,
            text: form.text.trim(),
            options: form.options.trim()
                ? form.options.split("|").map((o) => o.trim())
                : undefined,
            answer: form.answer.trim(),
            difficulty: form.difficulty,
            bloom: "Understand",
            marks: Math.max(1, form.marks),
            topic: form.topic.trim() || "General",
            chapter: form.chapter.trim() || (availableChapters[0] ?? "Chapter"),
            sourceRefs: [],
            locked: editing?.locked ?? false,
            origin: "teacher",
            recommendedMarks: recommended(),
            markingScheme: editing?.markingScheme,
        });
        onClose();
    }

    return (
        <Modal
            open={open}
            title={editing ? "Edit question" : "Add custom question"}
            onClose={onClose}
        >
            <div className="form-grid">
                <Select
                    label="Type"
                    value={form.type}
                    onChange={(e) => setForm({ ...form, type: e.target.value as QuestionType })}
                >
                    {Object.entries(QUESTION_TYPE_LABELS).map(([v, label]) => (
                        <option key={v} value={v}>
                            {label}
                        </option>
                    ))}
                </Select>
                <Select
                    label="Difficulty"
                    value={form.difficulty}
                    onChange={(e) =>
                        setForm({ ...form, difficulty: e.target.value as Difficulty })
                    }
                >
                    {DIFFICULTIES.map((d) => (
                        <option key={d} value={d}>
                            {d}
                        </option>
                    ))}
                </Select>
                <Textarea
                    label="Question text"
                    rows={3}
                    value={form.text}
                    onChange={(e) => setForm({ ...form, text: e.target.value })}
                />
                {form.type === "MCQ" ||
                form.type === "MultipleSelect" ||
                form.type === "Match" ? (
                    <Input
                        label="Options (separate with |)"
                        value={form.options}
                        onChange={(e) => setForm({ ...form, options: e.target.value })}
                    />
                ) : null}
                <Input
                    label="Expected answer"
                    value={form.answer}
                    onChange={(e) => setForm({ ...form, answer: e.target.value })}
                />
                <Input
                    label="Topic"
                    value={form.topic}
                    onChange={(e) => setForm({ ...form, topic: e.target.value })}
                />
                <Select
                    label="Chapter"
                    value={form.chapter}
                    onChange={(e) => setForm({ ...form, chapter: e.target.value })}
                >
                    {availableChapters.length === 0 && <option value="">No chapters yet</option>}
                    {availableChapters.map((c) => (
                        <option key={c} value={c}>
                            {c}
                        </option>
                    ))}
                </Select>
                <div>
                    <label className="text-sm font-medium">
                        Marks (AI recommends <b>{recommended()}</b>)
                    </label>
                    <input
                        type="number"
                        min={1}
                        max={totalMarks}
                        className="border-input mt-1 h-9 w-full rounded-md border bg-transparent px-3 text-sm"
                        value={form.marks}
                        onChange={(e) => setForm({ ...form, marks: Number(e.target.value) })}
                    />
                    <p className="text-xs text-muted-foreground">
                        AI budget left: {Math.max(0, aiBudget)} marks
                    </p>
                </div>
            </div>
            <div className="modal-actions">
                <Button variant="ghost" onClick={onClose}>
                    Cancel
                </Button>
                <Button
                    variant="primary"
                    disabled={form.text.trim().length === 0}
                    onClick={handleSave}
                >
                    {editing ? "Save changes" : "Add question"}
                </Button>
            </div>
        </Modal>
    );
}