"use client";

// ============================================================
// QuestionCard — one question in the post-generation review list.
//
// The rule this card enforces: a question must be UNLOCKED before it can be
// changed. While locked, Edit / "Regenerate with AI" / "Write my own" are all
// withheld (with a tooltip saying why) and the only way forward is Unlock. Once
// unlocked the teacher picks one of two routes: ask the AI for a fresh version,
// or write the question themselves.
//
// Questions are numbered per origin, so a teacher-authored one reads
// "Custom Question 2" instead of a bare "Custom" chip.
// ============================================================

import { Badge, Button } from "@/components/ui";
import type { QuestionDraft } from "@/types/exam-builder";

/** Tooltip on every action that a locked question refuses. */
const LOCKED_HINT = "Unlock this question first to change it";

export default function QuestionCard({
    question,
    index,
    busy = false,
    onEdit = undefined,
    onRegenerate = undefined,
    onWriteOwn = undefined,
    onDelete = undefined,
    onToggleLock = undefined,
    onSwapImage = undefined,
}: {
    question: QuestionDraft;
    /** 1-based position among questions of the same origin → "Custom Question 2". */
    index: number;
    /** A regeneration is queued or running, so mutating actions pause. */
    busy?: boolean;
    onEdit?: (q: QuestionDraft) => void;
    onRegenerate?: (q: QuestionDraft) => void;
    onWriteOwn?: (q: QuestionDraft) => void;
    onDelete?: (q: QuestionDraft) => void;
    onToggleLock?: (q: QuestionDraft) => void;
    onSwapImage?: (q: QuestionDraft) => void;
}) {
    const isTeacher = question.origin === "teacher";
    const frozen = question.locked || busy;

    return (
        <div
            className={`flex items-start justify-between gap-3 rounded-md border border-l-4 p-3 ${
                isTeacher
                    ? "border-l-violet-400 dark:border-l-violet-500/70"
                    : "border-l-sky-400 dark:border-l-sky-500/70"
            }`}
        >
            <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                    <Badge tone={isTeacher ? "violet" : "accent"}>
                        {isTeacher ? "Custom" : "AI"} Question {index}
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
                    <span className="text-muted-foreground text-xs">
                        {question.chapter} · {question.topic}
                    </span>
                    {question.locked && <Badge tone="muted">Locked</Badge>}
                    {busy && <Badge tone="amber">Regenerating</Badge>}
                    {question.image && <Badge tone="teal">Image: {question.image.kind}</Badge>}
                </div>
                <p className="mt-1 text-sm">{question.text}</p>
                {question.image && (
                    <p className="text-muted-foreground text-xs">
                        {question.image.caption}
                        {question.image.answerKeyImage ? " · with answer-key image" : ""}
                    </p>
                )}
            </div>
            <div className="flex shrink-0 flex-col items-end gap-2">
                {question.locked ? (
                    // Locked: the only change allowed is the unlock itself.
                    onToggleLock && (
                        <Button
                            variant="outline"
                            size="sm"
                            title="Unlock this question to change it"
                            onClick={() => onToggleLock(question)}
                        >
                            Unlock
                        </Button>
                    )
                ) : (
                    <>
                        <div className="flex gap-1">
                            {onRegenerate && (
                                <Button
                                    variant="primary"
                                    size="sm"
                                    title={
                                        busy
                                            ? "A regeneration is already running"
                                            : "Ask the AI for a fresh version of this question"
                                    }
                                    disabled={busy}
                                    onClick={() => onRegenerate(question)}
                                >
                                    Regenerate with AI
                                </Button>
                            )}
                            {onWriteOwn && (
                                <Button
                                    variant="outline"
                                    size="sm"
                                    title="Replace this question with your own version"
                                    disabled={busy}
                                    onClick={() => onWriteOwn(question)}
                                >
                                    Write my own
                                </Button>
                            )}
                        </div>
                        <div className="flex flex-wrap justify-end gap-1">
                            {onEdit && (
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    title={frozen ? LOCKED_HINT : "Edit this question"}
                                    disabled={busy}
                                    onClick={() => onEdit(question)}
                                >
                                    Edit
                                </Button>
                            )}
                            {onSwapImage && (
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    disabled={busy}
                                    onClick={() => onSwapImage(question)}
                                >
                                    {question.image ? "Swap image" : "Add image"}
                                </Button>
                            )}
                            {onToggleLock && (
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    title="Freeze this question so regeneration skips it"
                                    disabled={busy}
                                    onClick={() => onToggleLock(question)}
                                >
                                    Lock
                                </Button>
                            )}
                            {onDelete && (
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    className="text-red-600 dark:text-red-400"
                                    title="Delete this question"
                                    disabled={busy}
                                    onClick={() => onDelete(question)}
                                >
                                    Delete
                                </Button>
                            )}
                        </div>
                    </>
                )}
            </div>
        </div>
    );
}