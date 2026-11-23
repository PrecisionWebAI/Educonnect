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
    Input,
} from "@/components/ui";
import { useToast } from "@/components/ui/toast";
import { errorMessage } from "@/lib/api/client";
import { titleCase } from "@/lib/format";
import {
    approveChapterPlan,
    createChapter,
    deleteChapter,
    rejectChapterPlan,
    submitChapterPlan,
    updateChapter,
} from "@/services";
import type { CourseSubject } from "@/types";

const PLAN_LABEL: Record<CourseSubject["chapterPlanStatus"], string> = {
    Draft: "Draft",
    Submitted: "Waiting for approval",
    Approved: "Approved",
};

/**
 * The **Total Chapters** popup: only the list of chapters - nothing about progress.
 *
 * The teacher presses "Add chapter" as often as needed; each press adds a numbered box
 * (1, 2, 3...). "Save chapters" stores them, "Submit for approval" sends the finished
 * list to the principal's office, which approves it or sends it back with a reason.
 * Progress (Pending / Skipped / Completed) lives in the Completed popup.
 */
export default function ChapterPlanDialog({
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
    const [newNames, setNewNames] = useState<string[]>([]);
    const [busy, setBusy] = useState(false);
    const [editing, setEditing] = useState<{ id: string; name: string } | null>(null);
    const [sendingBack, setSendingBack] = useState(false);
    const [reason, setReason] = useState("");

    const subjectId = subject?.classroomSubjectId ?? null;
    const chapters = useMemo(
        () => [...(subject?.chapters ?? [])].sort((a, b) => a.sequence - b.sequence),
        [subject?.chapters],
    );

    function handleOpenChange(next: boolean) {
        if (!next) {
            setNewNames([]);
            setEditing(null);
            setSendingBack(false);
            setReason("");
        }
        onOpenChange(next);
    }

    if (!subject || !subjectId) return null;
    const planState = subject.chapterPlanStatus;
    const editable = subject.canEditPlan;

    async function run(action: () => Promise<unknown>, done: string, fallback: string) {
        setBusy(true);
        try {
            await action();
            await queryClient.invalidateQueries({ queryKey: ["course"] });
            await queryClient.invalidateQueries({ queryKey: ["classroom"] });
            toast.push("success", done);
            return true;
        } catch (cause) {
            toast.push("error", errorMessage(cause, fallback));
            return false;
        } finally {
            setBusy(false);
        }
    }

    /** Save every typed row, in order, so the numbers stay 1, 2, 3... */
    async function saveNew() {
        const names = newNames.map((value) => value.trim()).filter(Boolean);
        if (names.length === 0) return;
        const ok = await run(
            async () => {
                for (const value of names) {
                    await createChapter(subjectId as string, { name: value });
                }
            },
            names.length === 1 ? "Chapter added" : `${names.length} chapters added`,
            "Could not save the chapters.",
        );
        if (ok) setNewNames([]);
    }

    async function rename() {
        if (!editing || !editing.name.trim()) return;
        const ok = await run(
            () => updateChapter(editing.id, { name: editing.name.trim() }),
            "Chapter renamed",
            "Could not rename the chapter.",
        );
        if (ok) setEditing(null);
    }

    async function sendBack() {
        const ok = await run(
            () => rejectChapterPlan(subjectId as string, reason.trim()),
            "Sent back to the teacher",
            "Could not send the list back.",
        );
        if (ok) {
            setSendingBack(false);
            setReason("");
        }
    }

    const unsaved = newNames.some((value) => value.trim());

    return (
        <Dialog open={open} onOpenChange={handleOpenChange}>
            <DialogContent className="sm:max-w-xl">
                <DialogHeader>
                    <div className="flex flex-wrap items-center justify-between gap-2">
                        <DialogTitle>{titleCase(subject.name)} · Chapters</DialogTitle>
                        <Badge
                            tone={
                                planState === "Approved"
                                    ? "green"
                                    : planState === "Submitted"
                                      ? "amber"
                                      : "muted"
                            }
                        >
                            {PLAN_LABEL[planState]}
                        </Badge>
                    </div>
                </DialogHeader>

                {subject.chapterPlanReapproval && (
                    <p className="rounded-md border border-amber-300 bg-amber-50 p-2 text-sm text-amber-900">
                        Your changes are waiting for the principal&apos;s approval. The list that
                        was approved earlier stays in use until then.
                    </p>
                )}

                {planState === "Draft" && subject.chapterPlanRejectReason && (
                    <p className="rounded-md border border-amber-300 bg-amber-50 p-2 text-sm text-amber-900">
                        Sent back: {subject.chapterPlanRejectReason}
                    </p>
                )}

                {chapters.length > 0 && (
                    <ul className="divide-y rounded-md border">
                        {chapters.map((chapter) => (
                            <li
                                key={chapter.chapterId}
                                className="flex items-center gap-2 p-2 text-sm"
                            >
                                <span className="w-8 shrink-0 font-medium">
                                    {chapter.sequence}.
                                </span>
                                {editing?.id === chapter.chapterId ? (
                                    <div className="flex flex-1 items-center gap-2">
                                        <Input
                                            value={editing.name}
                                            onChange={(event) =>
                                                setEditing({
                                                    id: editing.id,
                                                    name: event.target.value,
                                                })
                                            }
                                            aria-label="Chapter name"
                                        />
                                        <Button size="sm" onClick={rename} disabled={busy}>
                                            Save
                                        </Button>
                                        <Button
                                            size="sm"
                                            variant="ghost"
                                            onClick={() => setEditing(null)}
                                        >
                                            Cancel
                                        </Button>
                                    </div>
                                ) : (
                                    <span className="min-w-0 flex-1 truncate font-medium">
                                        {chapter.name}
                                    </span>
                                )}
                                {editable && !editing && (
                                    <span className="flex gap-1">
                                        <Button
                                            size="sm"
                                            variant="ghost"
                                            onClick={() =>
                                                setEditing({
                                                    id: chapter.chapterId,
                                                    name: chapter.name,
                                                })
                                            }
                                        >
                                            Edit
                                        </Button>
                                        <Button
                                            size="sm"
                                            variant="danger"
                                            disabled={busy}
                                            onClick={() =>
                                                run(
                                                    () => deleteChapter(chapter.chapterId),
                                                    "Chapter removed",
                                                    "Could not delete the chapter.",
                                                )
                                            }
                                        >
                                            Delete
                                        </Button>
                                    </span>
                                )}
                            </li>
                        ))}
                    </ul>
                )}

                {chapters.length === 0 && !editable && (
                    <p className="text-muted-foreground text-sm">No chapters added yet.</p>
                )}

                {editable && (
                    <div className="space-y-2">
                        {newNames.map((value, index) => (
                            <div key={index} className="flex items-end gap-2">
                                <div className="flex-1">
                                    <Input
                                        label={`Chapter ${chapters.length + index + 1}`}
                                        value={value}
                                        autoFocus
                                        placeholder="Chapter name"
                                        onChange={(event) =>
                                            setNewNames((current) =>
                                                current.map((item, at) =>
                                                    at === index ? event.target.value : item,
                                                ),
                                            )
                                        }
                                    />
                                </div>
                                <Button
                                    variant="ghost"
                                    aria-label="Remove this row"
                                    onClick={() =>
                                        setNewNames((current) =>
                                            current.filter((_, at) => at !== index),
                                        )
                                    }
                                >
                                    ✕
                                </Button>
                            </div>
                        ))}
                        <div className="flex flex-wrap items-center gap-2">
                            <Button
                                variant="outline"
                                disabled={busy}
                                onClick={() => setNewNames((current) => [...current, ""])}
                            >
                                Add chapter
                            </Button>
                            {newNames.length > 0 && (
                                <Button
                                    disabled={busy || newNames.every((value) => !value.trim())}
                                    onClick={saveNew}
                                >
                                    Save chapters
                                </Button>
                            )}
                        </div>
                    </div>
                )}

                {subject.canSubmitPlan && (
                    <div className="flex items-center justify-between gap-2">
                        <span className="text-muted-foreground text-sm">
                            Submit once the list is complete.
                        </span>
                        <Button
                            disabled={busy || unsaved}
                            title={unsaved ? "Save the new chapters first" : undefined}
                            onClick={() =>
                                run(
                                    () => submitChapterPlan(subjectId),
                                    "Submitted for approval",
                                    "Could not submit the list.",
                                )
                            }
                        >
                            Submit for approval
                        </Button>
                    </div>
                )}

                {planState === "Submitted" && subject.canApprove && (
                    <div className="space-y-2 rounded-md border p-3">
                        <p className="text-sm font-medium">
                            This chapter list is waiting for approval.
                        </p>
                        {sendingBack ? (
                            <div className="flex items-end gap-2">
                                <div className="flex-1">
                                    <Input
                                        label="What should the teacher change?"
                                        value={reason}
                                        onChange={(event) => setReason(event.target.value)}
                                    />
                                </div>
                                <Button
                                    variant="danger"
                                    disabled={busy || !reason.trim()}
                                    onClick={sendBack}
                                >
                                    Send back
                                </Button>
                                <Button variant="ghost" onClick={() => setSendingBack(false)}>
                                    Cancel
                                </Button>
                            </div>
                        ) : (
                            <div className="flex gap-2">
                                <Button
                                    disabled={busy}
                                    onClick={() =>
                                        run(
                                            () => approveChapterPlan(subjectId),
                                            "Chapter list approved",
                                            "Could not approve.",
                                        )
                                    }
                                >
                                    Approve
                                </Button>
                                <Button variant="outline" onClick={() => setSendingBack(true)}>
                                    Send back
                                </Button>
                            </div>
                        )}
                    </div>
                )}

                {planState === "Submitted" && !subject.canApprove && (
                    <p className="text-muted-foreground text-sm">
                        The principal&apos;s office is reviewing this list.
                    </p>
                )}
            </DialogContent>
        </Dialog>
    );
}
