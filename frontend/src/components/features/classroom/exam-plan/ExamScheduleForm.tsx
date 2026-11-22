"use client";

import { useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Plus, Trash2 } from "lucide-react";
import { Button, Input, MultiSelect, Select, Spinner, Textarea } from "@/components/ui";
import { DatePicker } from "@/components/ui/date-picker";
import { useToast } from "@/components/ui/toast";
import { useApiQuery } from "@/lib/api/use-api-query";
import { useClassCatalog } from "@/hooks/use-class-catalog";
import { errorMessage } from "@/lib/api/client";
import {
    blankDraft,
    blankPaper,
    draftBody,
    draftFromExam,
    draftProblems,
    type ExamDraft,
    type ExamScopeWord,
    type PaperDraft,
} from "@/lib/exams/view";
import { createExam, getSectionCourse, updateExam } from "@/services";
import type { ExamPlan } from "@/types";
import { EXAM_LIST_KEY } from "./useExamPlan";

// The schedule form - one screen for both kinds of exam (Phase 8).
//
// A **class** exam is written from the section's own page: the class and the room
// are this page's, so every row inherits them and picks one of **this section's own
// subjects**. A **school** exam is the office's: each new row names a class and a
// subject *by name*, and the server makes one paper per section that already has that
// subject - sections that do not are reported back, never invented. A saved exam opens
// as one row per section paper, each labelled "Class 9-A · Mathematics".
//
// Validation runs in `lib/exams/view` (`draftProblems`), so the button explains
// itself before a round trip answers 422 - and the same rules are unit-tested.
// Saving sends **draft** or **scheduled**: a draft tells nobody, scheduling is what
// puts the date sheet in front of families.

const EXAM_TYPES = [
    "Unit test",
    "Periodic test",
    "Mid-term",
    "Half-yearly",
    "Annual",
    "Pre-board",
    "Practical",
];

export default function ExamScheduleForm({
    scope,
    exam,
    sectionId,
    classroomId,
    classId,
    className,
    subjects,
    onClose,
}: {
    scope: ExamScopeWord;
    /** The exam being corrected, or `null` for a new one. */
    exam: ExamPlan | null;
    sectionId: string;
    classroomId: string;
    classId: string | null;
    className: string;
    subjects: { id: string; name: string }[];
    onClose: () => void;
}) {
    const queryClient = useQueryClient();
    const toast = useToast();
    const catalog = useClassCatalog();
    const [draft, setDraft] = useState<ExamDraft>(() =>
        exam
            ? draftFromExam(exam)
            : blankDraft(scope, {
                  papers: [blankPaper({ classId: scope === "school" ? "" : (classId ?? "") })],
              }),
    );
    const [problems, setProblems] = useState<string[]>([]);
    const [saving, setSaving] = useState<"draft" | "scheduled" | null>(null);

    // The syllabus picker reads the Course tab's plan: a subject's chapters, in the
    // order the class will reach them.
    const course = useApiQuery(["course", "section", sectionId], () => getSectionCourse(sectionId));

    // Class exam: this section's subjects. School exam: a name suggestion list only -
    // the server decides which sections have the subject.
    const subjectOptions = useMemo(
        () => subjects.map((subject) => ({ value: subject.id, label: subject.name })),
        [subjects],
    );

    const classOptions = useMemo(
        () => catalog.classes.map((item) => ({ value: item.id, label: item.name })),
        [catalog.classes],
    );

    function chaptersOf(subjectId: string) {
        const subject = course.data?.subjects.find((item) => item.classroomSubjectId === subjectId);
        return (subject?.chapters ?? []).map((chapter) => ({
            value: chapter.chapterId,
            label: chapter.name,
        }));
    }

    function patch(changes: Partial<ExamDraft>) {
        setDraft((current) => ({ ...current, ...changes }));
    }

    function patchPaper(key: string, changes: Partial<PaperDraft>) {
        setDraft((current) => ({
            ...current,
            papers: current.papers.map((paper) =>
                paper.key === key ? { ...paper, ...changes } : paper,
            ),
        }));
    }

    function addPaper() {
        setDraft((current) => ({
            ...current,
            papers: [
                ...current.papers,
                blankPaper({
                    classId: scope === "school" ? "" : (classId ?? ""),
                    examDate: current.papers[current.papers.length - 1]?.examDate ?? "",
                }),
            ],
        }));
    }

    function removePaper(key: string) {
        setDraft((current) => ({
            ...current,
            papers: current.papers.filter((paper) => paper.key !== key),
        }));
    }

    async function submit(status: "draft" | "scheduled") {
        const found = draftProblems(draft);
        if (found.length > 0) {
            setProblems(found);
            toast.push("error", found[0]);
            return;
        }
        setProblems([]);
        setSaving(status);
        try {
            const body = draftBody(draft, { classId, classroomId });
            const saved = exam
                ? await updateExam(exam.id, { ...body, status })
                : await createExam(body, status);
            await queryClient.invalidateQueries({ queryKey: EXAM_LIST_KEY });
            toast.push(
                "success",
                status === "draft"
                    ? "Saved as a draft — nobody has been told yet."
                    : "Exam scheduled — the families have the date sheet.",
            );
            const skipped = saved.skipped ?? [];
            if (skipped.length > 0) {
                // A named subject reached every section that has it; say who it missed.
                toast.push(
                    "info",
                    `No paper for ${skipped.map((item) => `${item.section} (${item.subject})`).join(", ")} — add the subject in that section's Course tab first.`,
                );
            }
            onClose();
        } catch (cause) {
            const message = errorMessage(cause, "Could not save the exam");
            setProblems([message]);
            toast.push("error", message);
        } finally {
            setSaving(null);
        }
    }

    if (catalog.loading) return <Spinner />;

    return (
        <div className="space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
                <button type="button" onClick={onClose} className="classroom-back-link">
                    <ArrowLeft aria-hidden="true" className="size-4" />
                    Back to the exams
                </button>
                <span className="text-muted-foreground text-xs">
                    {scope === "school" ? "School-wide" : className} · {exam ? "editing" : "new"}
                </span>
            </div>

            <div className="glass-tile space-y-4 rounded-2xl p-4 sm:p-5">
                <div className="grid gap-3 sm:grid-cols-3">
                    <Input
                        label="Exam name"
                        value={draft.name}
                        onChange={(event) => patch({ name: event.target.value })}
                        placeholder="Mid-Term 2026"
                    />
                    <Input
                        label="Term"
                        value={draft.term}
                        onChange={(event) => patch({ term: event.target.value })}
                        placeholder="Term 1"
                    />
                    <Select
                        label="Type"
                        value={draft.examType}
                        onChange={(event) => patch({ examType: event.target.value })}
                    >
                        <option value="">Not set</option>
                        {EXAM_TYPES.map((type) => (
                            <option key={type} value={type}>
                                {type}
                            </option>
                        ))}
                    </Select>
                </div>

                <div className="grid gap-3 sm:grid-cols-2">
                    <DatePicker
                        label="First day"
                        value={draft.startDate}
                        onChange={(value) => patch({ startDate: value })}
                    />
                    <DatePicker
                        label="Last day"
                        value={draft.endDate}
                        onChange={(value) => patch({ endDate: value })}
                    />
                </div>

                <Textarea
                    label="Note for the families"
                    value={draft.note}
                    onChange={(event) => patch({ note: event.target.value })}
                    rows={2}
                    placeholder="Syllabus, room changes, anything the date sheet should say."
                />
            </div>

            <div className="space-y-3">
                <div className="flex items-center justify-between">
                    <h3 className="text-sm font-semibold">Date sheet</h3>
                    <Button size="sm" variant="outline" type="button" onClick={addPaper}>
                        <Plus aria-hidden="true" className="mr-1 size-4" />
                        Add a paper
                    </Button>
                </div>

                {draft.papers.map((paper, index) => (
                    <div key={paper.key} className="glass-tile space-y-3 rounded-2xl p-4">
                        <div className="flex items-center justify-between">
                            <span className="text-muted-foreground text-xs font-medium">
                                Paper {index + 1}
                            </span>
                            <Button
                                size="sm"
                                variant="ghost"
                                type="button"
                                title="Remove this paper"
                                aria-label={`Remove paper ${index + 1}`}
                                onClick={() => removePaper(paper.key)}
                            >
                                <Trash2 aria-hidden="true" className="size-4" />
                            </Button>
                        </div>

                        <div className="grid gap-3 sm:grid-cols-3">
                            {scope === "school" && (
                                <Select
                                    label="Class"
                                    value={paper.classId}
                                    onChange={(event) =>
                                        patchPaper(paper.key, { classId: event.target.value })
                                    }
                                >
                                    <option value="">Pick a class</option>
                                    {classOptions.map((option) => (
                                        <option key={option.value} value={option.value}>
                                            {option.label}
                                        </option>
                                    ))}
                                </Select>
                            )}
                            {paper.label ? (
                                <div className="text-sm">
                                    <p className="font-medium">Paper</p>
                                    <p className="mt-2">
                                        {paper.label}
                                        {paper.paperGroupId && (
                                            <span className="text-muted-foreground ml-2 text-xs">
                                                shared question paper
                                            </span>
                                        )}
                                    </p>
                                </div>
                            ) : scope === "school" ? (
                                <>
                                    <Input
                                        label="Subject"
                                        list={`subjects-${paper.key}`}
                                        value={paper.subjectName}
                                        onChange={(event) =>
                                            patchPaper(paper.key, {
                                                subjectName: event.target.value,
                                            })
                                        }
                                        placeholder="e.g. Mathematics"
                                    />
                                    <datalist id={`subjects-${paper.key}`}>
                                        {subjectOptions.map((option) => (
                                            <option key={option.value} value={option.label} />
                                        ))}
                                    </datalist>
                                </>
                            ) : (
                                <Select
                                    label="Subject"
                                    value={paper.classroomSubjectId}
                                    onChange={(event) =>
                                        patchPaper(paper.key, {
                                            classroomSubjectId: event.target.value,
                                            chapterIds: [],
                                        })
                                    }
                                >
                                    <option value="">Pick a subject</option>
                                    {subjectOptions.map((option) => (
                                        <option key={option.value} value={option.value}>
                                            {option.label}
                                        </option>
                                    ))}
                                </Select>
                            )}
                            <DatePicker
                                label="Date"
                                value={paper.examDate}
                                onChange={(value) => patchPaper(paper.key, { examDate: value })}
                            />
                        </div>

                        <div className="grid gap-3 sm:grid-cols-5">
                            <Input
                                label="Starts"
                                type="time"
                                value={paper.startTime}
                                onChange={(event) =>
                                    patchPaper(paper.key, { startTime: event.target.value })
                                }
                            />
                            <Input
                                label="Ends"
                                type="time"
                                value={paper.endTime}
                                onChange={(event) =>
                                    patchPaper(paper.key, { endTime: event.target.value })
                                }
                            />
                            <Input
                                label="Out of"
                                type="number"
                                min="0"
                                step="0.5"
                                value={paper.maxMarks}
                                onChange={(event) =>
                                    patchPaper(paper.key, { maxMarks: event.target.value })
                                }
                            />
                            <Input
                                label="Passing"
                                type="number"
                                min="0"
                                step="0.5"
                                value={paper.passingMarks}
                                onChange={(event) =>
                                    patchPaper(paper.key, { passingMarks: event.target.value })
                                }
                            />
                            <Input
                                label="Room"
                                value={paper.room}
                                onChange={(event) =>
                                    patchPaper(paper.key, { room: event.target.value })
                                }
                            />
                        </div>

                        <div className="grid gap-3 sm:grid-cols-2">
                            {paper.paperGroupId ? (
                                <p className="text-muted-foreground self-end text-xs">
                                    The syllabus belongs to the shared question paper — change it
                                    from the date sheet.
                                </p>
                            ) : paper.classroomSubjectId ? (
                                <MultiSelect
                                    label="Syllabus"
                                    options={chaptersOf(paper.classroomSubjectId)}
                                    value={paper.chapterIds}
                                    onChange={(chapterIds) => patchPaper(paper.key, { chapterIds })}
                                    placeholder="No chapters planned yet"
                                />
                            ) : (
                                <Input
                                    label="Syllabus (chapter names)"
                                    value={paper.chapterNames}
                                    onChange={(event) =>
                                        patchPaper(paper.key, { chapterNames: event.target.value })
                                    }
                                    placeholder="Algebra, Geometry — each section must have them"
                                />
                            )}
                            <Input
                                label="Note"
                                value={paper.note}
                                onChange={(event) =>
                                    patchPaper(paper.key, { note: event.target.value })
                                }
                                placeholder="Optional"
                            />
                        </div>
                    </div>
                ))}
            </div>

            {problems.length > 0 && (
                <div className="rounded-2xl border border-red-500/40 bg-red-500/5 p-3" role="alert">
                    <p className="text-sm font-medium text-red-600 dark:text-red-400">
                        This exam cannot be saved yet
                    </p>
                    <ul className="mt-1 list-disc space-y-0.5 pl-5 text-xs text-red-600 dark:text-red-400">
                        {problems.map((problem) => (
                            <li key={problem}>{problem}</li>
                        ))}
                    </ul>
                </div>
            )}

            <div className="flex flex-wrap justify-end gap-2">
                <Button variant="ghost" type="button" onClick={onClose}>
                    Cancel
                </Button>
                <Button
                    variant="outline"
                    type="button"
                    onClick={() => submit("draft")}
                    loading={saving === "draft"}
                    disabled={saving !== null}
                >
                    Save as draft
                </Button>
                <Button
                    type="button"
                    onClick={() => submit("scheduled")}
                    loading={saving === "scheduled"}
                    disabled={saving !== null}
                >
                    Schedule it
                </Button>
            </div>
        </div>
    );
}
