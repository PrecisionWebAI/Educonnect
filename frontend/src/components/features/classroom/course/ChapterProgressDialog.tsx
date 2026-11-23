"use client";

import { useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
    Badge,
    Button,
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    Select,
} from "@/components/ui";
import { useToast } from "@/components/ui/toast";
import { errorMessage } from "@/lib/api/client";
import { titleCase } from "@/lib/format";
import { approveChapterProgress, rejectChapterProgress, saveChapterProgress } from "@/services";
import type { CourseChapter, CourseSubject } from "@/types";

type Choice = "Pending" | "Completed" | "Skipped";

function settled(chapter: CourseChapter): Choice {
    const base = chapter.proposedStatus ?? chapter.status;
    return base === "Completed" || base === "Skipped" ? base : "Pending";
}

/**
 * The **Completed** popup: every chapter, in order, with its status.
 *
 * `1. The French Revolution  [Pending v]` - the teacher picks Skipped or Completed and
 * saves; the change waits for the principal's approval and the counts move only then.
 * Finishing chapter 4 with 2 and 3 still pending skips 2 and 3 (the server does it; the
 * rows say "Will be skipped" before the save).
 */
export default function ChapterProgressDialog({
    subject,
    open,
    onOpenChange,
}: {
    subject: CourseSubject | null;
    open: boolean;
    onOpenChange: (open: boolean) => void;
}) {
    const queryClient = useQueryClient();
    const toast = useToast();
    const [choices, setChoices] = useState<Record<string, Choice>>({});
    const [busy, setBusy] = useState(false);

    const subjectId = subject?.classroomSubjectId ?? null;
    const chapters = useMemo(
        () => [...(subject?.chapters ?? [])].sort((a, b) => a.sequence - b.sequence),
        [subject?.chapters],
    );

    function handleOpenChange(next: boolean) {
        if (!next) setChoices({});
        onOpenChange(next);
    }

    if (!subject || !subjectId) return null;

    const approved = subject.chapterPlanStatus === "Approved";
    const shown = (chapter: CourseChapter): Choice =>
        choices[chapter.chapterId] ?? settled(chapter);
    const lastDone = Math.max(
        0,
        ...chapters.filter((chapter) => shown(chapter) === "Completed").map((c) => c.sequence),
    );
    const changed = chapters.filter(
        (chapter) => choices[chapter.chapterId] && choices[chapter.chapterId] !== settled(chapter),
    );

    async function run(action: () => Promise<unknown>, done: string, fallback: string) {
        setBusy(true);
        try {
            await action();
            await queryClient.invalidateQueries({ queryKey: ["course"] });
            await queryClient.invalidateQueries({ queryKey: ["classroom"] });
            setChoices({});
            toast.push("success", done);
        } catch (cause) {
            toast.push("error", errorMessage(cause, fallback));
        } finally {
            setBusy(false);
        }
    }

    return (
        <Dialog open={open} onOpenChange={handleOpenChange}>
            <DialogContent className="sm:max-w-xl">
                <DialogHeader>
                    <DialogTitle>
                        {titleCase(subject.name)} · Completed {subject.done}
                        {subject.total > 0 ? ` of ${subject.total}` : ""}
                    </DialogTitle>
                </DialogHeader>

                {chapters.length === 0 ? (
                    <p className="text-muted-foreground text-sm">
                        No chapters yet. Add them from the Total Chapters button first.
                    </p>
                ) : !approved ? (
                    <p className="text-muted-foreground text-sm">
                        The chapter list is not approved yet, so progress cannot be saved.
                    </p>
                ) : (
                    <>
                        <ul className="divide-y rounded-md border">
                            {chapters.map((chapter) => {
                                const value = shown(chapter);
                                const willSkip = value === "Pending" && chapter.sequence < lastDone;
                                return (
                                    <li
                                        key={chapter.chapterId}
                                        className="flex flex-wrap items-center gap-2 p-2 text-sm"
                                    >
                                        <span className="w-8 shrink-0 font-medium">
                                            {chapter.sequence}.
                                        </span>
                                        <span className="min-w-0 flex-1 truncate font-medium">
                                            {chapter.name}
                                        </span>
                                        {chapter.proposedStatus && !choices[chapter.chapterId] && (
                                            <Badge tone="amber">Awaiting approval</Badge>
                                        )}
                                        {willSkip && <Badge tone="amber">Will be skipped</Badge>}
                                        {subject.canSaveProgress ? (
                                            <div className="w-36">
                                                <Select
                                                    aria-label={`Status of chapter ${chapter.sequence}`}
                                                    value={value}
                                                    onChange={(event) =>
                                                        setChoices((current) => ({
                                                            ...current,
                                                            [chapter.chapterId]: event.target
                                                                .value as Choice,
                                                        }))
                                                    }
                                                >
                                                    <option value="Pending">Pending</option>
                                                    <option value="Skipped">Skipped</option>
                                                    <option value="Completed">Completed</option>
                                                </Select>
                                            </div>
                                        ) : (
                                            <Badge
                                                tone={
                                                    chapter.status === "Completed"
                                                        ? "green"
                                                        : chapter.status === "Skipped"
                                                          ? "amber"
                                                          : "muted"
                                                }
                                            >
                                                {chapter.status}
                                            </Badge>
                                        )}
                                    </li>
                                );
                            })}
                        </ul>

                        {subject.canSaveProgress && (
                            <div className="flex items-center justify-between gap-2">
                                <span className="text-muted-foreground text-sm">
                                    {changed.length === 0
                                        ? "Change a status, then save."
                                        : `${changed.length} change${changed.length === 1 ? "" : "s"} to save.`}
                                </span>
                                <Button
                                    disabled={busy || changed.length === 0}
                                    onClick={() =>
                                        run(
                                            () =>
                                                saveChapterProgress(
                                                    subjectId,
                                                    changed.map((chapter) => ({
                                                        chapterId: chapter.chapterId,
                                                        status: choices[chapter.chapterId],
                                                    })),
                                                ),
                                            subject.canApprove
                                                ? "Progress saved"
                                                : "Saved - waiting for the principal's approval",
                                            "Could not save progress.",
                                        )
                                    }
                                >
                                    Save
                                </Button>
                            </div>
                        )}

                        {subject.pendingApproval > 0 && !subject.canApprove && (
                            <p className="rounded-md border border-amber-300 bg-amber-50 p-2 text-sm text-amber-900">
                                {subject.pendingApproval} change
                                {subject.pendingApproval === 1 ? " is" : "s are"} waiting for the
                                principal&apos;s approval. The completed count changes only after it
                                is approved.
                            </p>
                        )}

                        {subject.pendingApproval > 0 && subject.canApprove && (
                            <div className="flex items-center justify-between gap-2 rounded-md border p-3">
                                <span className="text-sm font-medium">
                                    {subject.pendingApproval} saved change
                                    {subject.pendingApproval === 1 ? "" : "s"} waiting for approval.
                                </span>
                                <div className="flex gap-2">
                                    <Button
                                        disabled={busy}
                                        onClick={() =>
                                            run(
                                                () => approveChapterProgress(subjectId),
                                                "Progress approved",
                                                "Could not approve.",
                                            )
                                        }
                                    >
                                        Approve
                                    </Button>
                                    <Button
                                        variant="outline"
                                        disabled={busy}
                                        onClick={() =>
                                            run(
                                                () => rejectChapterProgress(subjectId),
                                                "Sent back to the teacher",
                                                "Could not send back.",
                                            )
                                        }
                                    >
                                        Send back
                                    </Button>
                                </div>
                            </div>
                        )}
                    </>
                )}
            </DialogContent>
        </Dialog>
    );
}
