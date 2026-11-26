"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Check } from "lucide-react";
import { Badge, Button, Input, Spinner, Table } from "@/components/ui";
import { useToast } from "@/components/ui/toast";
import { errorMessage } from "@/lib/api/client";
import type { LadderRung } from "@/lib/exams/marking";
import { cleanGradeInput } from "@/lib/exams/marking";
import { figuresFor, ladderOf, percentCell } from "@/lib/exams/marksSheet";
import { passText } from "@/lib/exams/schoolExam";
import {
    amount,
    dayText,
    editFromRows,
    figureText,
    marksEntries,
    publishGate,
    scoreProblem,
    sheetCounts,
    type MarkEdit,
} from "@/lib/exams/view";
import { changeMark, publishPaper, savePaperMarks, setGradeMode } from "@/services";
import type { ExamPaperPlan } from "@/types";
import MarkHistoryDialog from "./MarkHistoryDialog";
import { EXAM_LIST_KEY, useExamDetail, useMarkingDefaults, usePaperSheet } from "./useExamPlan";

// The marks sheet for **one paper** - the screen a teacher sits in front of after the exam.
//
// One table, one row per child of the section, so the whole class is filled in on one
// screen. Each row shows its percentage, grade and Pass/Fail **as it is typed**, judged by
// the paper's own pass line and its own grading ladder. Enter moves to the next child.
//
// Three states, and the sheet is honest about which one it is in:
//
//   * **draft** - every row is an input; Save sends only the lines that changed, so
//     pressing Save twice writes nothing the second time. Families see nothing yet;
//   * **publishing** - one sitting at a time, with the gate's own words when it cannot go
//     ahead. Publishing tells each family **its own child's** marks;
//   * **published** - the scores are read-only. A correction is a different act: it asks
//     for the reason, writes an audit row and tells the family what changed.
//
// An absence is a state of its own - the child did not score zero, they did not sit it -
// and it is what keeps them out of the percentages.

type Row = MarkEdit & { index: number };

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
    const [edits, setEdits] = useState<
        Record<string, { score: string; absent: boolean; grade?: string }>
    >({});
    /** The Grade column's mode while this sheet is open (`null` = what the paper holds). */
    const [modePick, setModePick] = useState<"auto" | "na" | "manual" | null>(null);
    const [busy, setBusy] = useState<"save" | "publish" | "change" | null>(null);
    const [historyOpen, setHistoryOpen] = useState(false);
    const [fix, setFix] = useState<{
        studentId: string;
        score: string;
        absent: boolean;
        grade: string;
        reason: string;
    } | null>(null);

    const fixCard = useRef<HTMLDivElement>(null);
    // "Change" on a row brings the correction card below into view.
    const fixStudent = fix?.studentId;
    useEffect(() => {
        if (fixStudent) {
            fixCard.current?.scrollIntoView({ behavior: "smooth", block: "center" });
        }
    }, [fixStudent]);

    const paper: ExamPaperPlan | undefined = exam.data?.papers.find((item) => item.id === paperId);
    // An older paper has no ladder of its own; the school's is the fallback.
    const defaults = useMarkingDefaults(paper ? amount(paper.maxMarks) : null);
    const ladder = useMemo<LadderRung[]>(() => {
        const school = (defaults.data?.ladder ?? []).map((rung) => ({
            minPercent: Number(rung.minPercent),
            grade: rung.grade,
        }));
        return paper ? ladderOf(paper, school) : school;
    }, [paper, defaults.data]);

    const gradeMode = modePick ?? paper?.gradeMode ?? "auto";
    const manual = gradeMode === "manual";
    const rows: Row[] = useMemo(
        () =>
            editFromRows(sheet.data ?? []).map((row, index) => {
                // A typed grade only exists on a sheet the server holds as Manual.
                const held = paper?.gradeMode === "manual" ? (row.saved?.grade ?? "") : "";
                return {
                    ...row,
                    grade: held,
                    savedGrade: held,
                    ...(edits[row.studentId] ?? {}),
                    index,
                };
            }),
        [sheet.data, edits, paper?.gradeMode],
    );
    const counts = sheetCounts(rows);
    const modeChanged = modePick !== null && modePick !== (paper?.gradeMode ?? "auto");
    const gate = paper
        ? publishGate({ paper, edits: rows, canEdit: paper.canEdit, manualGrades: manual })
        : null;
    const published = Boolean(paper?.publishedAt);

    function setRow(
        studentId: string,
        patch: Partial<Pick<MarkEdit, "score" | "absent" | "grade">>,
    ) {
        const base = rows.find((row) => row.studentId === studentId);
        if (!base) return;
        setEdits((current) => ({
            ...current,
            [studentId]: {
                score: base.score,
                absent: base.absent,
                grade: base.grade,
                ...patch,
            },
        }));
    }

    function invalidate() {
        void queryClient.invalidateQueries({ queryKey: EXAM_LIST_KEY });
    }

    async function save() {
        const entries = marksEntries(rows);
        if (entries.length === 0 && !modeChanged) {
            toast.push("info", "Nothing has changed since the sheet was read.");
            return;
        }
        setBusy("save");
        try {
            const saved = await savePaperMarks(
                paperId,
                entries,
                modeChanged ? gradeMode : undefined,
            );
            setEdits({});
            setModePick(null);
            invalidate();
            toast.push(
                "success",
                `Saved ${saved.written} score${saved.written === 1 ? "" : "s"}${
                    saved.absent > 0 ? ` · ${saved.absent} absent` : ""
                } — the families will hear when you publish.`,
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
            invalidate();
            toast.push("success", "Published — each family has been sent its own child's marks.");
        } catch (cause) {
            toast.push("error", errorMessage(cause, "Could not publish the marks"));
        } finally {
            setBusy(null);
        }
    }

    async function submitFix() {
        if (!fix || !paper) return;
        if (!fix.absent && fix.score.trim() === "") {
            toast.push("error", "Enter the score, or tick Absent.");
            return;
        }
        const problem = fix.absent ? null : scoreProblem(fix.score, paper.maxMarks);
        if (problem) {
            toast.push("error", problem);
            return;
        }
        // Manual: every field of the card is needed.
        if (paper.gradeMode === "manual" && !fix.absent && !fix.grade.trim()) {
            toast.push("error", "Enter the grade — it is needed in Manual.");
            return;
        }
        const row = rows.find((item) => item.studentId === fix.studentId);
        const marksChanged =
            !!row &&
            (fix.absent !== (row.saved?.absent ?? false) ||
                (!fix.absent && amount(fix.score) !== amount(row.saved?.marksObtained ?? null)));
        const gradeChanged =
            paper.gradeMode === "manual" &&
            !fix.absent &&
            fix.grade.trim() !== (row?.saved?.grade ?? "").trim();
        if (!marksChanged && !gradeChanged) {
            toast.push("info", "Nothing has changed.");
            return;
        }
        if (marksChanged && !fix.reason.trim()) {
            toast.push("error", "Say why the mark is changing — it goes on the record.");
            return;
        }
        setBusy("change");
        try {
            if (gradeChanged) {
                await setGradeMode(paperId, "manual", [
                    { studentId: fix.studentId, grade: fix.grade.trim() },
                ]);
            }
            if (marksChanged) {
                await changeMark(paperId, fix.studentId, {
                    marksObtained: fix.absent ? null : amount(fix.score),
                    absent: fix.absent,
                    grade: paper.gradeMode === "manual" ? fix.grade.trim() || null : null,
                    reason: fix.reason.trim(),
                });
            }
            setFix(null);
            invalidate();
            await Promise.all([sheet.refetch(), exam.refetch()]);
            toast.push(
                "success",
                marksChanged
                    ? "Corrected — the change is on the record and the family is told what changed."
                    : "The Grade column is updated.",
            );
        } catch (cause) {
            toast.push("error", errorMessage(cause, "Could not save the correction"));
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
    const editable = !published && paper.canEdit;
    // After publishing the scores are fixed, but the Grade column can still be changed.
    const gradeEditable = paper.canEdit;
    const gradeDirty =
        published &&
        (modeChanged ||
            rows.some((row) => (row.grade ?? "").trim() !== (row.savedGrade ?? "").trim()));
    // Manual: every scored child needs a grade before it can be saved.
    const gradesMissing = manual
        ? rows.filter(
              (row) => !row.absent && amount(row.score) !== null && !(row.grade ?? "").trim(),
          ).length
        : 0;

    async function saveGrade() {
        setBusy("save");
        try {
            await setGradeMode(
                paperId,
                gradeMode,
                manual
                    ? rows
                          .filter((row) => !row.absent && (row.grade ?? "").trim())
                          .map((row) => ({
                              studentId: row.studentId,
                              grade: (row.grade ?? "").trim(),
                          }))
                    : [],
            );
            setEdits({});
            setModePick(null);
            invalidate();
            await Promise.all([sheet.refetch(), exam.refetch()]);
            toast.push("success", "The Grade column is updated.");
        } catch (cause) {
            toast.push("error", errorMessage(cause, "Could not change the Grade column"));
        } finally {
            setBusy(null);
        }
    }
    function focusNext(index: number) {
        document.getElementById(`marks-${index + 1}`)?.focus();
    }

    return (
        <div className="space-y-4">
            <BackLink onBack={onBack} />

            <div className="glass-tile flex flex-wrap items-center justify-between gap-3 rounded-2xl p-4 sm:p-5">
                <div className="min-w-0 space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                        <h3 className="text-base font-semibold tracking-tight">
                            {paper.title} · {paper.section}
                        </h3>
                        <Badge tone={published ? "green" : "muted"}>
                            {published ? "Published" : "Draft"}
                        </Badge>
                        <Badge tone="accent">Out of {figureText(paper.maxMarks)}</Badge>
                        <Badge tone="muted">Pass: {passText(paper)}</Badge>
                    </div>
                    <p className="text-muted-foreground text-xs">
                        {dayText(paper.examDate)} · {counts.marked} marked · {counts.absent} absent
                        · {counts.blank} blank
                    </p>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                    {published && paper.canEdit && (
                        <Button size="sm" variant="ghost" onClick={() => setHistoryOpen(true)}>
                            Correction history
                        </Button>
                    )}
                    {gradeDirty && (
                        <Button
                            size="sm"
                            variant="outline"
                            onClick={saveGrade}
                            loading={busy === "save"}
                            disabled={busy !== null || gradesMissing > 0}
                            title={
                                gradesMissing > 0
                                    ? `${gradesMissing} grade${gradesMissing === 1 ? " is" : "s are"} still empty.`
                                    : "Save the Grade column"
                            }
                        >
                            Save
                        </Button>
                    )}
                    {editable && (
                        <>
                            <Button
                                size="sm"
                                variant="outline"
                                onClick={save}
                                loading={busy === "save"}
                                disabled={busy !== null || (pending === 0 && !modeChanged)}
                            >
                                Save {pending > 0 ? `(${pending})` : ""}
                            </Button>
                            <Button
                                size="sm"
                                onClick={publish}
                                loading={busy === "publish"}
                                disabled={busy !== null || pending > 0 || gate?.allowed === false}
                                title={
                                    pending > 0
                                        ? "Save the changes first."
                                        : (gate?.reason ??
                                          "Each family is sent its own child's marks.")
                                }
                            >
                                Publish
                            </Button>
                        </>
                    )}
                </div>
            </div>

            {!paper.canEdit && (
                <p className="text-sm text-amber-600" role="status">
                    You can read this sheet but not change it — only the paper&apos;s subject
                    teacher, the class teacher of a class test, or the school&apos;s leadership can.
                </p>
            )}
            {editable && gate?.allowed === false && (
                <p className="text-muted-foreground text-xs">{gate.reason}</p>
            )}
            {published && (
                <p className="text-muted-foreground text-xs">
                    These marks have been published. To fix a mistake, press Change on a
                    student&apos;s row and say why. The change is saved with your reason, and that
                    student&apos;s family is told.
                </p>
            )}

            <Table
                columns={[
                    {
                        key: "n",
                        header: "#",
                        render: (row: Row) => (
                            <span className="text-muted-foreground text-xs tabular-nums">
                                {row.index + 1}
                            </span>
                        ),
                    },
                    {
                        key: "student",
                        header: "Student",
                        render: (row: Row) => (
                            <div className="min-w-0">
                                <p className="truncate text-sm font-medium">{row.name}</p>
                                <p className="text-muted-foreground text-xs">
                                    {row.admissionNumber ?? "—"}
                                    {row.saved?.changedAfterPublish ? " · corrected" : ""}
                                </p>
                            </div>
                        ),
                    },
                    {
                        key: "marks",
                        header: `Marks (out of ${figureText(paper.maxMarks)})`,
                        render: (row: Row) =>
                            editable ? (
                                <div className="w-28">
                                    <Input
                                        id={`marks-${row.index}`}
                                        aria-label={`Marks for ${row.name}`}
                                        type="number"
                                        min="0"
                                        step="0.5"
                                        placeholder="—"
                                        value={row.absent ? "" : row.score}
                                        disabled={row.absent}
                                        onChange={(event) =>
                                            setRow(row.studentId, { score: event.target.value })
                                        }
                                        onKeyDown={(event) => {
                                            if (event.key === "Enter") {
                                                event.preventDefault();
                                                focusNext(row.index);
                                            }
                                        }}
                                        error={scoreProblem(row.score, paper.maxMarks) ?? undefined}
                                    />
                                </div>
                            ) : (
                                <span className="text-sm tabular-nums">
                                    {row.absent
                                        ? "—"
                                        : figureText(row.saved?.marksObtained ?? null)}
                                </span>
                            ),
                    },
                    {
                        key: "absent",
                        header: "Absent",
                        render: (row: Row) =>
                            editable ? (
                                <input
                                    type="checkbox"
                                    className="size-4"
                                    aria-label={`${row.name} was absent`}
                                    checked={row.absent}
                                    onChange={(event) =>
                                        setRow(row.studentId, {
                                            absent: event.target.checked,
                                            score: event.target.checked ? "" : row.score,
                                        })
                                    }
                                />
                            ) : row.absent ? (
                                <Badge tone="amber">Absent</Badge>
                            ) : (
                                <span className="text-muted-foreground">—</span>
                            ),
                    },
                    {
                        key: "percent",
                        header: "%",
                        align: "right",
                        render: (row: Row) => (
                            <span className="text-sm tabular-nums">
                                {percentCell(figuresFor(row, paper, ladder).percentage)}
                            </span>
                        ),
                    },
                    {
                        key: "grade",
                        header: gradeEditable ? (
                            <span className="flex items-center gap-1.5">
                                Grade
                                <select
                                    aria-label="How the Grade column works"
                                    className="border-input bg-background h-7 rounded-md border px-1 text-xs font-semibold"
                                    value={gradeMode}
                                    onChange={(event) =>
                                        setModePick(event.target.value as typeof gradeMode)
                                    }
                                >
                                    <option value="na">NA</option>
                                    <option value="auto">Auto</option>
                                    <option value="manual">Manual</option>
                                </select>
                            </span>
                        ) : (
                            "Grade"
                        ),
                        render: (row: Row) => {
                            if (gradeMode === "na") {
                                return <span className="text-muted-foreground text-sm">NA</span>;
                            }
                            if (gradeMode === "manual") {
                                if (!gradeEditable) {
                                    return (
                                        <span className="text-sm">{row.saved?.grade ?? "—"}</span>
                                    );
                                }
                                return (
                                    <div className="w-20">
                                        <Input
                                            aria-label={`Grade for ${row.name}`}
                                            maxLength={2}
                                            className="uppercase"
                                            placeholder="—"
                                            value={row.absent ? "" : (row.grade ?? "")}
                                            disabled={row.absent}
                                            onChange={(event) =>
                                                setRow(row.studentId, {
                                                    grade: cleanGradeInput(event.target.value),
                                                })
                                            }
                                            error={
                                                !row.absent &&
                                                amount(row.score) !== null &&
                                                !(row.grade ?? "").trim()
                                                    ? "Required"
                                                    : undefined
                                            }
                                        />
                                    </div>
                                );
                            }
                            return (
                                <span className="text-sm">
                                    {figuresFor(row, paper, ladder).grade ?? "—"}
                                </span>
                            );
                        },
                    },
                    {
                        key: "result",
                        header: "Result",
                        render: (row: Row) => {
                            const found = figuresFor(row, paper, ladder);
                            if (found.state === "absent") return <Badge tone="amber">Absent</Badge>;
                            if (found.passed === null)
                                return <span className="text-muted-foreground">—</span>;
                            return (
                                <Badge tone={found.passed ? "green" : "red"}>
                                    {found.passed ? "Pass" : "Fail"}
                                </Badge>
                            );
                        },
                    },
                    {
                        key: "change",
                        header: "",
                        align: "right",
                        render: (row: Row) =>
                            published && paper.canEdit ? (
                                <Button
                                    size="sm"
                                    variant="ghost"
                                    onClick={() =>
                                        setFix({
                                            studentId: row.studentId,
                                            score: row.score,
                                            absent: row.absent,
                                            grade:
                                                paper.gradeMode === "manual"
                                                    ? (row.saved?.grade ?? "")
                                                    : "",
                                            reason: "",
                                        })
                                    }
                                >
                                    Change
                                </Button>
                            ) : null,
                    },
                ]}
                rows={rows}
                rowKey={(row) => row.studentId}
                empty="Nobody is on this paper's roll yet. Students are added to the class-section first."
            />

            {fix && (
                <div
                    ref={fixCard}
                    className="glass-tile space-y-3 rounded-2xl border border-amber-500/40 p-4"
                >
                    <p className="text-sm font-medium">
                        Correct the marks of{" "}
                        {rows.find((row) => row.studentId === fix.studentId)?.name ??
                            "this student"}
                    </p>
                    <div className="grid gap-3 sm:grid-cols-2">
                        <Input
                            label={`New score (out of ${figureText(paper.maxMarks)})`}
                            type="number"
                            min="0"
                            step="0.5"
                            value={fix.absent ? "" : fix.score}
                            disabled={fix.absent}
                            onChange={(event) => setFix({ ...fix, score: event.target.value })}
                        />
                        {paper.gradeMode === "manual" ? (
                            <Input
                                label="Grade (required)"
                                maxLength={2}
                                className="uppercase"
                                value={fix.absent ? "" : fix.grade}
                                disabled={fix.absent}
                                onChange={(event) =>
                                    setFix({ ...fix, grade: cleanGradeInput(event.target.value) })
                                }
                            />
                        ) : (
                            <div className="space-y-2">
                                <p className="text-sm leading-none font-medium">Grade</p>
                                <p className="text-muted-foreground flex h-9 items-center text-sm">
                                    {paper.gradeMode === "na" || fix.absent
                                        ? "NA"
                                        : (figuresFor(
                                              {
                                                  studentId: fix.studentId,
                                                  name: "",
                                                  admissionNumber: null,
                                                  section: null,
                                                  score: fix.score,
                                                  absent: false,
                                                  saved: null,
                                              },
                                              paper,
                                              ladder,
                                          ).grade ?? "—")}
                                </p>
                            </div>
                        )}
                        <label className="flex items-center gap-2 text-sm sm:col-span-2">
                            <input
                                type="checkbox"
                                className="size-4"
                                checked={fix.absent}
                                onChange={(event) =>
                                    setFix({ ...fix, absent: event.target.checked })
                                }
                            />
                            Absent (no score)
                        </label>
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

            <MarkHistoryDialog
                paperId={paperId}
                open={historyOpen}
                onClose={() => setHistoryOpen(false)}
            />
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
