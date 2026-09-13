"use client";

// ============================================================
// QuestionCard — one question row with review actions
// (blueprint §1.14): Edit · Regenerate · Delete · Lock · Swap image.
// ============================================================

import { Badge, Button } from "@/components/ui";
import type { QuestionDraft } from "@/types/exam-builder";

export default function QuestionCard({
    question,
    onEdit = undefined,
    onRegenerate = undefined,
    onDelete = undefined,
    onToggleLock = undefined,
    onSwapImage = undefined,
}: {
    question: QuestionDraft;
    onEdit?: (q: QuestionDraft) => void;
    onRegenerate?: (q: QuestionDraft) => void;
    onDelete?: (q: QuestionDraft) => void;
    onToggleLock?: (q: QuestionDraft) => void;
    onSwapImage?: (q: QuestionDraft) => void;
}) {
    return (
        <div className="flex items-start justify-between rounded-md border p-3">
            <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                    <Badge tone={question.origin === "teacher" ? "violet" : "accent"}>
                        {question.origin === "teacher" ? "Custom" : "AI"}
                    </Badge>
                    <Badge tone="teal">{question.type}</Badge>
                    <Badge
                        tone={
                            question.difficulty === "Easy"
                                ? "green"
                                : question.difficulty === "Medium"
                                    ? "amber"
                                    : "red"
                        }
                    >
                        {question.difficulty}
                    </Badge>
                    <span className="text-xs font-medium">{question.marks} marks</span>
                    <span className="text-xs text-muted-foreground">
                        {question.chapter} · {question.topic}
                    </span>
                    {question.locked && <Badge tone="muted">🔒 Locked</Badge>}
                    {question.image && (
                        <Badge tone="teal">🖼 {question.image.kind}</Badge>
                    )}
                </div>
                <p className="mt-1 text-sm">{question.text}</p>
                {question.image && (
                    <p className="text-xs text-muted-foreground">
                        Image: {question.image.caption}
                        {question.image.answerKeyImage ? " · with answer-key image" : ""}
                    </p>
                )}
            </div>
            <div className="flex gap-1">
                {onEdit && (
                    <Button variant="ghost" size="sm" onClick={() => onEdit(question)}>
                        ✏️ Edit
                    </Button>
                )}
                {onRegenerate && (
                    <Button variant="ghost" size="sm" onClick={() => onRegenerate(question)}>
                        🔄 Regenerate
                    </Button>
                )}
                {onToggleLock && (
                    <Button variant="ghost" size="sm" onClick={() => onToggleLock(question)}>
                        {question.locked ? "🔓 Unlock" : "🔒 Lock"}
                    </Button>
                )}
                {onSwapImage && (
                    <Button variant="ghost" size="sm" onClick={() => onSwapImage(question)}>
                        {question.image ? "🖼 Swap image" : "🖼 Add image"}
                    </Button>
                )}
                {onDelete && (
                    <Button
                        variant="danger"
                        size="sm"
                        onClick={() => onDelete(question)}
                    >
                        🗑
                    </Button>
                )}
            </div>
        </div>
    );
}