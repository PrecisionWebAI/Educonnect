"use client";

import { useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Check, Undo2 } from "lucide-react";
import { Badge, Button, Input, Spinner } from "@/components/ui";
import { useToast } from "@/components/ui/toast";
import { errorMessage } from "@/lib/api/client";
import {
    amount,
    editFromRows,
    figureText,
    marksEntries,
    paperWhenText,
    publishGate,
    scoreProblem,
    sheetCounts,
    type MarkEdit,
} from "@/lib/exams/view";
import { changeMark, publishPaper, savePaperMarks } from "@/services";
import type { ExamPaperPlan } from "@/types";
import { EXAM_LIST_KEY, useExamDetail, usePaperSheet } from "./useExamPlan";

// The marks sheet for **one paper** (Phase 8) - the screen a teacher actually sits
// in front of after the exam.
//
// Three states, and the sheet is honest about which one it is in:
//
//   * **draft** - every row is an input; Save sends only the lines that changed
//     (`marksEntries`), so pressing Save twice writes nothing the second time;
//   * **publishing** - one sitting at a time, with the gate's own words when it
//     cannot go ahead (no mark entered, a score above the maximum, already out);
//   * **published** - the scores are read-only. A correction is a different act:
//     `changeMark` writes an audit row in the same transaction and tells the
//     family, so it asks for the reason and keeps it.
//
// An absence is a state of its own - the child did not score zero, they did not
// sit it - and it is what keeps them out of the averages and the ranks.

export default function MarksGrid({
    examId,
    paperId,
    onBack,
}: {
    examId: string;
    paperId: string;
    onBack: () => void;
}) {
    const queryClient = useQueryClient();
    const toast = useToast();
    const exam = useExamDetail(examId);
    const sheet = usePaperSheet(paperId);
    /** Only what this person typed; the rest is the server's own row. */
    const [edits, setEdits] = useState<Record<string, { score: string; absent: boolean }>>({});
    const [busy, setBusy] = useState<"save" | "publish" | "change" | null>(null);
    const [confirming, setConfirming] = useState(false);
    const [fix, setFix] = useState<{ studentId: string; score: string; reason: string } | null>(
        null,
    );

    const paper: ExamPaperPlan | undefined = exam.data?.papers.find((item) => item.id === paperId);
    const rows: MarkEdit[] = useMemo(
        () =>
            editFromRows(sheet.data ?? []).map((row) => ({
                ...row,
                ...(edits[row.studentId] ?? {}),
            })),
        [sheet.data, edits],
    );
    const counts = sheetCounts(rows);
    const gate = paper ? publishGate({ paper, edits: rows, canEdit: paper.canEdit }) : null;
    const published = Boolean(paper?.publishedAt);

    function setRow(studentId: string, patch: Partial<Pick<MarkEdit, "score" | "absent">>) {
        const base = rows.find((row) => row.studentId === studentId);
        if (!base) return;
        setEdits((current) => ({
            ...current,
            [studentId]: { score: base.score, absent: base.absent, ...patch },
        }));
    }

    function invalidate() {
        void queryClient.invalidateQueries({ queryKey: EXAM_LIST_KEY });
    }

    async function save() {
        const entries = marksEntries(rows);
        if (entries.length === 0) {
            toast.push("info", "Nothing has changed since the sheet was read.");
            return;
        }
        setBusy("save");
        try {
            const saved = await savePaperMarks(paperId, entries);
            setEdits({});
            invalidate();
            toast.push(
                "success",
                `Saved ${saved.written} score${saved.written === 1 ? "" : "s"}${
                    saved.absent > 0 ? ` · ${saved.absent} absent` : ""
                }`,
            );
        } catch (cause) {
            toast.push("error", errorMessage(cause, "Could not save the marks"));
        } finally {
            setBusy(null);
        }
    }

    async function publish() {
        setBusy("publish");
        try {
            await publishPaper(paperId);
            setConfirming(false);
            invalidate();
            toast.push("success", "Published — the families can see these marks.");
        } catch (cause) {
            toast.push("error", errorMessage(cause, "Could not publish the marks"));
        } finally {
            setBusy(null);
        }
    }

    async function submitFix() {
        if (!fix) return;
        const problem = scoreProblem(fix.score, paper?.maxMarks ?? 0);
        if (problem) {
            toast.push("error", problem);
            return;
        }
        if (!fix.reason.trim()) {
            toast.push("error", "Say why the mark is changing — it goes on the record.");
            return;
        }
        setBusy("change");
        try {
            await changeMark(paperId, fix.studentId, {
                marksObtained: fix.score.trim() === "" ? null : amount(fix.score),
                absent: fix.score.trim() === "",
                reason: fix.reason.trim(),
            });
            setFix(null);
            invalidate();
            toast.push(
                "success",
                "Corrected — the change is on the record and the family is told.",
            );
        } catch (cause) {
            toast.push("error", errorMessage(cause, "Could not correct the mark"));
        } finally {
            setBusy(null);
        }
    }

    if (sheet.isPending || exam.isPending) return <Spinner />;

    if (!paper) {
        return (
            <div className="space-y-3">
                <BackLink onBack={onBack} />
                <p className="text-muted-foreground text-sm">
                    This paper is no longer part of the exam.
                </p>
            </div>
        );
    }

    const pending = marksEntries(rows).length;

    return (
        <div className="space-y-4">
            <BackLink onBack={onBack} />

            <div className="glass-tile flex flex-wrap items-center justify-between gap-3 rounded-2xl p-4 sm:p-5">
                <div className="min-w-0 space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                        <h3 className="text-base font-semibold tracking-tight">{paper.subject}</h3>
                        <Badge tone={published ? "green" : "muted"}>
                            {published ? "Published" : "Draft"}
                        </Badge>
                        <Badge tone="accent">Out of {figureText(paper.maxMarks)}</Badge>
                    </div>
                    <p className="text-muted-foreground text-xs">
                        {paperWhenText(paper)} · {counts.marked} marked · {counts.absent} absent ·{" "}
                        {counts.blank} blank
                    </p>
                </div>

                {!published && paper.canEdit && (
                    <div className="flex flex-wrap items-center gap-2">
                        <Button
                            size="sm"
                            variant="outline"
                            onClick={save}
                            loading={busy === "save"}
                            disabled={busy !== null || pending === 0}
                        >
                            Save {pending > 0 ? `(${pending})` : ""}
                        </Button>
                        {confirming ? (
                            <>
                                <Button
                                    size="sm"
                                    onClick={publish}
                                    loading={busy === "publish"}
                                    disabled={busy !== null}
                                >
                                    Yes, publish to families
                                </Button>
                                <Button
                                    size="sm"
                                    variant="ghost"
                                    onClick={() => setConfirming(false)}
                                    disabled={busy !== null}
                                >
                                    Cancel
                                </Button>
                            </>
                        ) : (
                            <Button
                                size="sm"
                                onClick={() => setConfirming(true)}
                                disabled={busy !== null || gate?.allowed === false}
                                title={
                                    gate?.reason ?? "Families can see these marks once published."
                                }
                            >
                                Publish
                            </Button>
                        )}
                    </div>
                )}
            </div>

            {!paper.canEdit && (
                <p className="text-sm text-amber-600" role="status">
                    You can read this sheet but not change it — only the paper&apos;s subject
                    teacher or the office can.
                </p>
            )}
            {!published && paper.canEdit && gate?.allowed === false && (
                <p className="text-muted-foreground text-xs">{gate.reason}</p>
            )}
            {published && (
                <p className="text-muted-foreground text-xs">
                    {rows.length === 0 ? (
                        <p className="text-muted-foreground text-sm">
                            Nobody is on this paper&apos;s roll yet. Students are added to the
                            class-section first.
                        </p>
                    ) : (
                        <div className="space-y-2">
                            {rows.map((row) => {
                                const problem = scoreProblem(row.score, paper.maxMarks);
                                const editable = !published && paper.canEdit;
                                return (
                                    <div
                                        key={row.studentId}
                                        className="glass-tile flex flex-wrap items-center gap-3 rounded-2xl px-4 py-3"
                                    >
                                        <div className="min-w-0 flex-1">
                                            <p className="truncate text-sm font-medium">
                                                {row.name}
                                            </p>
                                            <p className="text-muted-foreground text-xs">
                                                {row.admissionNumber ?? "—"}
                                                {row.section ? ` · ${row.section}` : ""}
                                                {row.saved?.changedAfterPublish
                                                    ? " · corrected"
                                                    : ""}
                                            </p>
                                        </div>

                                        <div className="w-28">
                                            <Input
                                                aria-label={`Score for ${row.name}`}
                                                type="number"
                                                min="0"
                                                step="0.5"
                                                placeholder="—"
                                                value={row.absent ? "" : row.score}
                                                disabled={!editable || row.absent}
                                                onChange={(event) =>
                                                    setRow(row.studentId, {
                                                        score: event.target.value,
                                                    })
                                                }
                                                error={problem ?? undefined}
                                            />
                                        </div>

                                        {editable ? (
                                            <Button
                                                size="sm"
                                                variant={row.absent ? "danger" : "ghost"}
                                                onClick={() =>
                                                    setRow(row.studentId, {
                                                        absent: !row.absent,
                                                        score: row.absent ? row.score : "",
                                                    })
                                                }
                                            >
                                                {row.absent ? (
                                                    <>
                                                        <Undo2
                                                            aria-hidden="true"
                                                            className="mr-1 size-3.5"
                                                        />
                                                        Absent
                                                    </>
                                                ) : (
                                                    "Mark absent"
                                                )}
                                            </Button>
                                        ) : (
                                            <Badge tone={row.absent ? "amber" : "muted"}>
                                                {row.absent
                                                    ? "Absent"
                                                    : figureText(row.saved?.marksObtained ?? null)}
                                            </Badge>
                                        )}

                                        {published && paper.canEdit && !row.absent && (
                                            <Button
                                                size="sm"
                                                variant="ghost"
                                                onClick={() =>
                                                    setFix({
                                                        studentId: row.studentId,
                                                        score: row.score,
                                                        reason: "",
                                                    })
                                                }
                                            >
                                                Change
                                            </Button>
                                        )}
                                    </div>
                                );
                            })}
                        </div>
                    )}
                    These marks are out. A correction is recorded: it asks for the reason, writes an
                    audit row and tells the family.
                </p>
            )}

            {fix && (
                <div className="glass-tile space-y-3 rounded-2xl border border-amber-500/40 p-4">
                    <p className="text-sm font-medium">Correct one published mark</p>
                    <div className="grid gap-3 sm:grid-cols-2">
                        <Input
                            label={`New score (out of ${figureText(paper.maxMarks)})`}
                            type="number"
                            min="0"
                            step="0.5"
                            value={fix.score}
                            onChange={(event) => setFix({ ...fix, score: event.target.value })}
                            hint="Leave it empty only if the child's mark is being withdrawn."
                        />
                        <Input
                            label="Why is it changing?"
                            value={fix.reason}
                            onChange={(event) => setFix({ ...fix, reason: event.target.value })}
                            placeholder="Re-totalled after rechecking"
                        />
                    </div>
                    <div className="flex justify-end gap-2">
                        <Button size="sm" variant="ghost" onClick={() => setFix(null)}>
                            Cancel
                        </Button>
                        <Button size="sm" loading={busy === "change"} onClick={submitFix}>
                            <Check aria-hidden="true" className="mr-1 size-4" />
                            Record the correction
                        </Button>
                    </div>
                </div>
            )}
        </div>
    );
}

/** The back link every drill-down screen in this tab shares. */
function BackLink({ onBack }: { onBack: () => void }) {
    return (
        <button type="button" onClick={onBack} className="classroom-back-link">
            <ArrowLeft aria-hidden="true" className="size-4" />
            Back to the date sheet
        </button>
    );
}
