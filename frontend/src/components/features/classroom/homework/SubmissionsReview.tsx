"use client";

import { useState } from "react";
import { Badge, Button, Input, type BadgeTone } from "@/components/ui";
import {
    Table as ShadcnTable,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import { useToast } from "@/components/ui/toast";
import { errorMessage } from "@/lib/api/client";
import {
    boardCounts,
    feedbackBody,
    gradeGate,
    handedInText,
    marksProblem,
    marksText,
    submissionChip,
} from "@/lib/homework/view";
import { gradeSubmission } from "@/services";
import type { SubmissionItem } from "@/types";

// The review board (Phase 9).
//
// One line per child per assignment, handed in or not. A row that **has** a submission
// can be graded here: a score, a remark, or both - the server records `graded_at` and
// tells that family once. A row with no submission (the child never handed anything in)
// says so and offers nothing to grade, which is the honest state rather than a disabled
// mystery.
//
// Lateness is a badge of its own: work handed in after the due date is still handed in,
// and hiding that behind "Submitted" would lose the one fact the teacher needs.

function SubmissionRow({ item, onGraded }: { item: SubmissionItem; onGraded: () => void }) {
    const toast = useToast();
    const [open, setOpen] = useState(false);
    const [marks, setMarks] = useState(
        marksText(item.marksAwarded) === "—" ? "" : marksText(item.marksAwarded),
    );
    const [feedback, setFeedback] = useState(item.feedback ?? "");
    const [busy, setBusy] = useState(false);

    const chip = submissionChip(item);
    const problem = marksProblem(marks);
    const gate = gradeGate({ marks, feedback, item });

    async function save() {
        if (!gate.allowed || item.id === null) {
            toast.push("error", gate.reason ?? "Nothing to grade.");
            return;
        }
        setBusy(true);
        try {
            const body = feedbackBody(marks, feedback);
            await gradeSubmission(item.id, body);
            toast.push(
                "success",
                `Marked ${item.student}${
                    body.marksAwarded !== null ? ` · ${body.marksAwarded}` : ""
                } — the family is told.`,
            );
            setOpen(false);
            onGraded();
        } catch (cause) {
            toast.push("error", errorMessage(cause, "Could not save the feedback"));
        } finally {
            setBusy(false);
        }
    }

    return (
        <>
            <TableRow>
                <TableCell>
                    <p className="truncate font-medium">{item.homeworkTitle}</p>
                    <p className="text-muted-foreground text-xs">{item.subject ?? "—"}</p>
                </TableCell>
                <TableCell>{item.student}</TableCell>
                <TableCell className="whitespace-nowrap">
                    <span className="text-sm">{handedInText(item)}</span>
                    {item.isLate && (
                        <Badge tone="red" className="ml-2">
                            Late
                        </Badge>
                    )}
                </TableCell>
                <TableCell>
                    <Badge tone={chip.tone as BadgeTone}>{chip.label}</Badge>
                </TableCell>
                <TableCell className="text-right tabular-nums">
                    {marksText(item.marksAwarded)}
                </TableCell>
                <TableCell>
                    <p className="text-muted-foreground max-w-56 truncate text-xs">
                        {item.feedback ?? "—"}
                    </p>
                </TableCell>
                <TableCell className="text-right">
                    {item.id !== null && (
                        <Button size="sm" variant="ghost" onClick={() => setOpen(!open)}>
                            {open ? "Close" : item.status === "Graded" ? "Change" : "Grade"}
                        </Button>
                    )}
                </TableCell>
            </TableRow>
            {open && item.id !== null && (
                <TableRow>
                    <TableCell colSpan={7} className="p-3">
                        <div className="grid gap-3 sm:grid-cols-3">
                            <Input
                                label="Score"
                                type="number"
                                min="0"
                                step="0.5"
                                value={marks}
                                onChange={(event) => setMarks(event.target.value)}
                                error={problem ?? undefined}
                                hint="Homework has no fixed maximum — leave it empty for a remark only."
                            />
                            <Input
                                label="Remark"
                                value={feedback}
                                onChange={(event) => setFeedback(event.target.value)}
                                placeholder="Neat work; redo question 4"
                            />
                            <div className="flex items-end gap-2">
                                <Button
                                    size="sm"
                                    onClick={save}
                                    loading={busy}
                                    disabled={!gate.allowed || busy}
                                    title={gate.reason ?? undefined}
                                >
                                    Save feedback
                                </Button>
                                <Button size="sm" variant="ghost" onClick={() => setOpen(false)}>
                                    Cancel
                                </Button>
                            </div>
                        </div>
                        {!gate.allowed && (
                            <p className="text-muted-foreground mt-2 text-xs">{gate.reason}</p>
                        )}
                    </TableCell>
                </TableRow>
            )}
        </>
    );
}

export default function SubmissionsReview({
    rows,
    onGraded,
}: {
    rows: SubmissionItem[];
    /** Called after a save, so the board re-reads the server's own words. */
    onGraded?: () => void;
}) {
    if (rows.length === 0) {
        return <p className="text-muted-foreground text-sm">Nothing is on this board yet.</p>;
    }
    const counts = boardCounts(rows);
    return (
        <div className="space-y-3">
            <p className="text-muted-foreground text-xs">
                {counts.handedIn} in{counts.late > 0 ? ` · ${counts.late} late` : ""} ·{" "}
                {counts.graded} graded · {counts.pending} not handed in
            </p>
            <div className="app-data-table">
                <ShadcnTable>
                    <TableHeader>
                        <TableRow>
                            <TableHead>Homework</TableHead>
                            <TableHead>Student</TableHead>
                            <TableHead>Submitted</TableHead>
                            <TableHead>Status</TableHead>
                            <TableHead className="text-right">Score</TableHead>
                            <TableHead>Remark</TableHead>
                            <TableHead />
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {rows.map((item) => (
                            <SubmissionRow
                                key={`${item.homeworkId}-${item.studentId}`}
                                item={item}
                                onGraded={() => onGraded?.()}
                            />
                        ))}
                    </TableBody>
                </ShadcnTable>
            </div>
        </div>
    );
}
