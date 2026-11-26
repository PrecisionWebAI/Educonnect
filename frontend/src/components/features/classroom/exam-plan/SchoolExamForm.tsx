"use client";

import { useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import { Badge, Button, Input, Modal, Select, Textarea } from "@/components/ui";
import { DatePicker } from "@/components/ui/date-picker";
import { useToast } from "@/components/ui/toast";
import { errorMessage } from "@/lib/api/client";
import { duplicatesFrom, type DuplicateTest } from "@/lib/exams/classTest";
import { followTotal, type LadderRung } from "@/lib/exams/marking";
import { titleCase } from "@/lib/format";
import {
    SCHOOL_EXAM_TYPES,
    blankSchoolExamDraft,
    schoolExamCreateBody,
    schoolExamDraftFromExam,
    schoolExamProblems,
    schoolExamUpdateBody,
    type SchoolExamDraft,
    type SchoolRowDraft,
} from "@/lib/exams/schoolExam";
import { amount, dayText, figureText } from "@/lib/exams/view";
import { createSchoolExam, publishDateSheet, updateSchoolExam } from "@/services";
import type { ExamPlan } from "@/types";
import PassLineFields from "./PassLineFields";
import { EXAM_LIST_KEY, useMarkingDefaults } from "./useExamPlan";

// The **Date Sheet** of a School Exam: one row for every subject of this section.
//
//   Type [Unit Test | Periodic Test | Mid Term Test | Half Yearly | Annual | Pre-Board |
//         Practical | Custom -> type the name]            Note for Family
//   [x] Mathematics   Date   Total Marks   Pass by [Marks | Grade]
//   [x] Science       Date   Total Marks   Pass by [Marks | Grade]
//
// No first/last day and no clock time - only a date per subject. The syllabus is a
// separate button (the subject teacher writes it). Saving keeps a **draft**: families see
// nothing and nobody is told until the class teacher publishes it.

export default function SchoolExamForm({
    exam,
    classroomId,
    className,
    subjects,
    teachers,
    onClose,
}: {
    /** The date sheet being changed, or `null` for a new one. */
    exam: ExamPlan | null;
    classroomId: string;
    className: string;
    /** Every subject of this section - the rows of the sheet. */
    subjects: { id: string; name: string; teacherId?: string | null }[];
    /** Teachers who can take a paper (the "Taken By" dropdown). */
    teachers: { employeeId: string; name: string }[];
    onClose: () => void;
}) {
    const queryClient = useQueryClient();
    const toast = useToast();
    // The ladder and the school's pass percentage do not depend on a subject's total.
    const defaults = useMarkingDefaults(100);
    const ladder = useMemo<LadderRung[]>(
        () =>
            (defaults.data?.ladder ?? []).map((rung) => ({
                minPercent: Number(rung.minPercent),
                grade: rung.grade,
            })),
        [defaults.data],
    );
    const schoolPercent = Number(defaults.data?.passPercent ?? 33);

    const [draft, setDraft] = useState<SchoolExamDraft>(() =>
        exam ? schoolExamDraftFromExam(exam, subjects) : blankSchoolExamDraft(subjects),
    );
    // The sheet as saved: the form starts from it and moves on after every save, so Save
    // is live only while there is something new to save.
    const [current, setCurrent] = useState<ExamPlan | null>(exam);
    const [baseline, setBaseline] = useState(() => JSON.stringify(draft));
    const dirty = JSON.stringify(draft) !== baseline;
    const [duplicates, setDuplicates] = useState<DuplicateTest[] | null>(null);
    const [problems, setProblems] = useState<string[]>([]);
    const [saving, setSaving] = useState(false);

    function patchRow(subjectId: string, changes: Partial<SchoolRowDraft>) {
        setDraft((current) => ({
            ...current,
            rows: current.rows.map((row) =>
                row.subjectId === subjectId ? { ...row, ...changes } : row,
            ),
        }));
    }

    const assignedOf = (subjectId: string) =>
        subjects.find((subject) => subject.id === subjectId)?.teacherId ?? "";
    const assignedName = (subjectId: string) => {
        const id = assignedOf(subjectId);
        const name = teachers.find((teacher) => teacher.employeeId === id)?.name;
        return name ? titleCase(name) : "";
    };

    function changeTotal(row: SchoolRowDraft, text: string) {
        patchRow(row.subjectId, {
            total: text,
            passLine: followTotal(row.passLine, amount(text), schoolPercent),
        });
    }

    async function save(confirmDuplicate = false) {
        const found = schoolExamProblems(draft, ladder);
        if (found.length > 0) {
            setProblems(found);
            toast.push("error", found[0]);
            return;
        }
        setProblems([]);
        setSaving(true);
        try {
            if (current) {
                const saved = await updateSchoolExam(
                    current.id,
                    schoolExamUpdateBody(draft, current, { confirmDuplicate }),
                );
                setCurrent(saved);
                toast.push(
                    "success",
                    current.datesheetPublishedAt
                        ? "Date sheet updated — the families have been told what changed."
                        : "Date sheet saved.",
                );
            } else {
                const saved = await createSchoolExam(
                    schoolExamCreateBody(draft, classroomId, { confirmDuplicate }),
                );
                setCurrent(saved);
                toast.push(
                    "success",
                    "Date sheet saved as a draft — families cannot see it until you publish it.",
                );
            }
            setBaseline(JSON.stringify(draft));
            setDuplicates(null);
            await queryClient.invalidateQueries({ queryKey: EXAM_LIST_KEY });
        } catch (cause) {
            const existing = duplicatesFrom(cause);
            if (existing) {
                setDuplicates(existing);
            } else {
                const message = errorMessage(cause, "Could not save the date sheet");
                setProblems([message]);
                toast.push("error", message);
            }
        } finally {
            setSaving(false);
        }
    }

    async function publishNow() {
        if (!current) return;
        if (
            !window.confirm(
                "Publish this date sheet? The families can see it from now on and will be told.",
            )
        )
            return;
        setSaving(true);
        try {
            await publishDateSheet(current.id);
            await queryClient.invalidateQueries({ queryKey: EXAM_LIST_KEY });
            toast.push("success", "Date sheet published — the families have been told.");
            onClose();
        } catch (cause) {
            const message = errorMessage(cause, "Could not publish the date sheet");
            setProblems([message]);
            toast.push("error", message);
        } finally {
            setSaving(false);
        }
    }

    return (
        <div className="space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
                <button type="button" onClick={onClose} className="classroom-back-link">
                    <ArrowLeft aria-hidden="true" className="size-4" />
                    Back to the exams
                </button>
                <span className="text-muted-foreground text-xs">
                    {className} · {current ? "editing the date sheet" : "new date sheet"}
                </span>
            </div>

            <div className="glass-tile space-y-4 rounded-2xl p-4 sm:p-5">
                <div className="grid gap-3 sm:grid-cols-2">
                    <Select
                        label="Type"
                        value={draft.examType}
                        onChange={(event) =>
                            setDraft((current) => ({ ...current, examType: event.target.value }))
                        }
                    >
                        <option value="">Select</option>
                        {SCHOOL_EXAM_TYPES.map((type) => (
                            <option key={type.value} value={type.value}>
                                {type.label}
                            </option>
                        ))}
                    </Select>
                    {draft.examType === "custom" && (
                        <Input
                            label="Name of the exam"
                            value={draft.customName}
                            maxLength={80}
                            onChange={(event) =>
                                setDraft((current) => ({
                                    ...current,
                                    customName: event.target.value,
                                }))
                            }
                            placeholder="e.g. Science Fair Test"
                        />
                    )}
                </div>
                <Textarea
                    label="Note for Family"
                    value={draft.familyNote}
                    onChange={(event) =>
                        setDraft((current) => ({ ...current, familyNote: event.target.value }))
                    }
                    rows={2}
                    placeholder="What the guardian and the student should know about this exam."
                />
            </div>

            <div className="space-y-3">
                <h3 className="text-sm font-semibold">Date sheet</h3>
                {draft.rows.length === 0 && (
                    <p className="text-muted-foreground text-sm">
                        This section has no subjects yet. Add them in the Course tab first.
                    </p>
                )}
                {draft.rows.map((row) => (
                    <div key={row.subjectId} className="glass-tile space-y-3 rounded-2xl p-4">
                        <label className="flex items-center gap-2 text-sm font-medium">
                            <input
                                type="checkbox"
                                className="size-4"
                                checked={row.included}
                                onChange={(event) =>
                                    patchRow(row.subjectId, { included: event.target.checked })
                                }
                            />
                            {row.subjectName}
                        </label>
                        {row.included && (
                            <div className="space-y-3">
                                <div className="grid gap-3 sm:grid-cols-3">
                                    <DatePicker
                                        label="Date"
                                        value={row.examDate}
                                        onChange={(value) =>
                                            patchRow(row.subjectId, { examDate: value })
                                        }
                                    />
                                    <Input
                                        label="Total Marks"
                                        type="number"
                                        min={0}
                                        step="0.01"
                                        inputMode="decimal"
                                        value={row.total}
                                        onChange={(event) => changeTotal(row, event.target.value)}
                                    />
                                    <div className="space-y-2">
                                        <Select
                                            label="Taken By"
                                            value={row.takenBy}
                                            onChange={(event) =>
                                                patchRow(row.subjectId, {
                                                    takenBy: event.target.value,
                                                })
                                            }
                                        >
                                            <option value="">
                                                {assignedOf(row.subjectId)
                                                    ? `Assigned teacher${
                                                          assignedName(row.subjectId)
                                                              ? ` — ${assignedName(row.subjectId)}`
                                                              : ""
                                                      }`
                                                    : "Assigned teacher"}
                                            </option>
                                            {teachers.map((teacher) => (
                                                <option
                                                    key={teacher.employeeId}
                                                    value={teacher.employeeId}
                                                >
                                                    {titleCase(teacher.name)}
                                                </option>
                                            ))}
                                        </Select>
                                        {(row.takenBy !== "" || assignedOf(row.subjectId)) && (
                                            <p className="flex items-center gap-1.5 text-xs">
                                                <i
                                                    className={`tt-badge tt-badge-static ${
                                                        row.takenBy === "" ||
                                                        row.takenBy === assignedOf(row.subjectId)
                                                            ? "tt-badge-s"
                                                            : "tt-badge-t"
                                                    }`}
                                                >
                                                    {row.takenBy === "" ||
                                                    row.takenBy === assignedOf(row.subjectId)
                                                        ? "S"
                                                        : "T"}
                                                </i>
                                                <span className="text-muted-foreground">
                                                    {row.takenBy === "" ||
                                                    row.takenBy === assignedOf(row.subjectId)
                                                        ? "Assigned teacher"
                                                        : "Temporary teacher"}
                                                </span>
                                            </p>
                                        )}
                                    </div>
                                </div>
                                <PassLineFields
                                    total={row.total}
                                    value={row.passLine}
                                    onChange={(passLine) => patchRow(row.subjectId, { passLine })}
                                    ladder={ladder}
                                />
                            </div>
                        )}
                    </div>
                ))}
            </div>

            {problems.length > 0 && (
                <ul className="space-y-1 text-[0.8rem] font-medium text-red-500" role="alert">
                    {problems.map((problem) => (
                        <li key={problem}>{problem}</li>
                    ))}
                </ul>
            )}

            <Modal
                open={duplicates !== null}
                title="An exam already exists"
                onClose={() => setDuplicates(null)}
            >
                <div className="space-y-3 text-sm">
                    <p>
                        A paper for the same section, subject and date is already on the schedule.
                        Do you want to save this date sheet anyway?
                    </p>
                    <ul className="space-y-2">
                        {(duplicates ?? []).map((item) => (
                            <li
                                key={`${item.examId}-${item.subject}-${item.examDate}`}
                                className="glass-tile rounded-xl p-3"
                            >
                                <p className="font-medium">
                                    {titleCase(item.subject)} · {item.section}
                                </p>
                                <p className="text-muted-foreground text-xs">
                                    {dayText(item.examDate)} · {figureText(item.totalMarks)} marks
                                    {item.createdBy
                                        ? ` · added by ${titleCase(item.createdBy)}`
                                        : ""}
                                </p>
                                <Badge tone="muted">{item.status}</Badge>
                            </li>
                        ))}
                    </ul>
                    <div className="modal-actions">
                        <Button
                            variant="ghost"
                            onClick={() => setDuplicates(null)}
                            disabled={saving}
                        >
                            Cancel
                        </Button>
                        <Button variant="primary" onClick={() => save(true)} disabled={saving}>
                            {saving ? "Saving…" : "Save anyway"}
                        </Button>
                    </div>
                </div>
            </Modal>

            <div className="flex justify-end gap-2">
                <Button variant="ghost" onClick={onClose} disabled={saving}>
                    {dirty ? "Cancel" : "Close"}
                </Button>
                <Button variant="primary" onClick={() => save(false)} disabled={saving || !dirty}>
                    {saving ? "Saving…" : current ? "Save changes" : "Save date sheet"}
                </Button>
                {/* A saved draft is ready to publish; unsaved changes must be saved first. */}
                {current && current.canManage && !current.datesheetPublishedAt && (
                    <Button
                        variant="outline"
                        onClick={publishNow}
                        disabled={saving || dirty}
                        title={dirty ? "Save the changes first." : "Tell the families"}
                    >
                        Publish
                    </Button>
                )}
            </div>
        </div>
    );
}
