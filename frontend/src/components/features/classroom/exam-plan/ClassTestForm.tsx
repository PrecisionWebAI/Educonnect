"use client";

import { useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import { Badge, Button, Input, Modal, Select, Spinner, Textarea } from "@/components/ui";
import { DatePicker } from "@/components/ui/date-picker";
import { useToast } from "@/components/ui/toast";
import { titleCase } from "@/lib/format";
import { errorMessage } from "@/lib/api/client";
import {
    blankClassTestDraft,
    classTestCreateBody,
    classTestDraftFromExam,
    classTestPatch,
    classTestProblems,
    duplicatesFrom,
    type ClassTestDraft,
    type DuplicateTest,
} from "@/lib/exams/classTest";
import { followTotal, type LadderRung } from "@/lib/exams/marking";
import { amount, dayText, figureText } from "@/lib/exams/view";
import { createClassTest, getSyllabus, updateClassTest } from "@/services";
import { useApiQuery } from "@/lib/api/use-api-query";
import type { ExamPlan } from "@/types";
import PassLineFields from "./PassLineFields";
import { EXAM_LIST_KEY, useMarkingDefaults } from "./useExamPlan";

// Schedule (or edit) one class test - the form of the **Class Test** tab.
//
//   Type  Class Test (always)      Subject  (this section's own courses)
//   Date  Total Marks              (always this section - no section picker)
//   Test Taken By  [Assigned teacher | any teacher -> Temporary]
//   Pass by [Marks | Grade]        Note for family
//
// Rules live in `lib/exams/classTest` and `lib/exams/marking` (unit-tested); the server
// repeats them. A test cannot be saved until the pass line is complete, and a
// `409 DUPLICATE_EXAM` is answered with a popup listing the test that already exists -
// "Create anyway" resends with `confirm_duplicate`.

function ClassTestFormBody({
    exam,
    classroomId,
    className,
    subjects,
    teachers,
    savedSyllabus,
    onClose,
}: {
    /** The test being edited, or `null` for a new one. */
    exam: ExamPlan | null;
    classroomId: string;
    /** "Class 10" - the class whose sections can sit the test. */
    className: string;
    /** This section's own subjects (the test's subject is chosen from these). */
    subjects: { id: string; name: string; teacherId?: string | null }[];
    teachers: { employeeId: string; name: string }[];
    /** The syllabus saved on the test being edited ("" for a new one). */
    savedSyllabus: string;
    onClose: () => void;
}) {
    const queryClient = useQueryClient();
    const toast = useToast();
    const [draft, setDraft] = useState<ClassTestDraft>(() =>
        exam
            ? classTestDraftFromExam(exam, savedSyllabus)
            : blankClassTestDraft({ classroomId, subjectId: subjects[0]?.id }),
    );
    const [problems, setProblems] = useState<string[]>([]);
    const [saving, setSaving] = useState(false);
    const [duplicates, setDuplicates] = useState<DuplicateTest[] | null>(null);

    const total = amount(draft.total);
    // The grades do not depend on the total: ask with 100 until a total is typed, so the
    // Passing grade list is never empty.
    const defaults = useMarkingDefaults(total !== null && total > 0 ? total : 100);
    const ladder = useMemo<LadderRung[]>(
        () =>
            (defaults.data?.ladder ?? []).map((rung) => ({
                minPercent: Number(rung.minPercent),
                grade: rung.grade,
            })),
        [defaults.data],
    );
    const schoolPercent = Number(defaults.data?.passPercent ?? 33);

    const anchor = subjects.find((subject) => subject.id === draft.subjectId);
    const assignedId = anchor?.teacherId ?? "";
    const assignedName = teachers.find((teacher) => teacher.employeeId === assignedId)?.name;
    // Assigned (S) when nobody else is picked or the picked one *is* the assigned teacher;
    // anything else is a Temporary teacher (T) - the same cards as the Timetable.
    const isAssigned = draft.takenBy === "" ? Boolean(assignedId) : draft.takenBy === assignedId;
    const takerKnown = draft.takenBy !== "" || Boolean(assignedId);

    function patch(changes: Partial<ClassTestDraft>) {
        setDraft((current) => ({ ...current, ...changes }));
    }

    function changeTotal(text: string) {
        // The pass marks follow the total until the teacher types their own number.
        setDraft((current) => ({
            ...current,
            total: text,
            passLine: followTotal(current.passLine, amount(text), schoolPercent),
        }));
    }

    async function save(confirmDuplicate: boolean) {
        const found = classTestProblems(draft, ladder, { needsTaker: !assignedId });
        if (found.length > 0) {
            setProblems(found);
            toast.push("error", found[0]);
            return;
        }
        setProblems([]);
        setSaving(true);
        try {
            if (exam) {
                const changes = classTestPatch(draft, exam, { confirmDuplicate, savedSyllabus });
                if (Object.keys(changes).length === 0) {
                    toast.push("info", "Nothing was changed.");
                    onClose();
                    return;
                }
                await updateClassTest(exam.id, changes);
                toast.push("success", "Class test updated — the families have been told.");
            } else {
                await createClassTest(classTestCreateBody(draft, { confirmDuplicate }));
                toast.push("success", "Class test scheduled — the families have been told.");
            }
            await queryClient.invalidateQueries({ queryKey: EXAM_LIST_KEY });
            setDuplicates(null);
            onClose();
        } catch (cause) {
            const existing = duplicatesFrom(cause);
            if (existing) {
                setDuplicates(existing);
            } else {
                const message = errorMessage(cause, "Could not save the class test");
                setProblems([message]);
                toast.push("error", message);
            }
        } finally {
            setSaving(false);
        }
    }

    return (
        <div className="space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
                <button type="button" onClick={onClose} className="classroom-back-link">
                    <ArrowLeft aria-hidden="true" className="size-4" />
                    Back to the class tests
                </button>
                <span className="text-muted-foreground text-xs">
                    {className} · {exam ? "editing" : "new"}
                </span>
            </div>

            <div className="glass-tile space-y-4 rounded-2xl p-4 sm:p-5">
                <div className="grid gap-3 sm:grid-cols-2">
                    <Input label="Type" value="Class Test" disabled readOnly />
                    <Select
                        label="Subject"
                        value={draft.subjectId}
                        disabled={Boolean(exam)}
                        onChange={(event) => patch({ subjectId: event.target.value, takenBy: "" })}
                    >
                        {subjects.length === 0 && <option value="">No subjects yet</option>}
                        {subjects.map((subject) => (
                            <option key={subject.id} value={subject.id}>
                                {titleCase(subject.name)}
                            </option>
                        ))}
                    </Select>
                </div>

                <div className="grid gap-3 sm:grid-cols-3">
                    <DatePicker
                        label="Date"
                        value={draft.examDate}
                        onChange={(value) => patch({ examDate: value })}
                    />
                    <Input
                        label="Total Marks"
                        type="number"
                        min={0}
                        step="0.01"
                        inputMode="decimal"
                        value={draft.total}
                        onChange={(event) => changeTotal(event.target.value)}
                    />
                    <div className="space-y-2">
                        <Select
                            label="Test Taken By"
                            value={draft.takenBy}
                            onChange={(event) => patch({ takenBy: event.target.value })}
                        >
                            <option value="">
                                {assignedId
                                    ? `Assigned teacher${assignedName ? ` — ${titleCase(assignedName)}` : ""}`
                                    : "Pick a teacher"}
                            </option>
                            {teachers.map((teacher) => (
                                <option key={teacher.employeeId} value={teacher.employeeId}>
                                    {titleCase(teacher.name)}
                                </option>
                            ))}
                        </Select>
                        {takerKnown && (
                            <p className="flex items-center gap-1.5 text-xs">
                                <i
                                    className={`tt-badge tt-badge-static ${
                                        isAssigned ? "tt-badge-s" : "tt-badge-t"
                                    }`}
                                >
                                    {isAssigned ? "S" : "T"}
                                </i>
                                <span className="text-muted-foreground">
                                    {isAssigned ? "Assigned teacher" : "Temporary teacher"}
                                </span>
                            </p>
                        )}
                        {!assignedId && (
                            <p className="text-muted-foreground text-xs">
                                No teacher is assigned to this subject in Course — pick any teacher
                                to take this test (a temporary teacher).
                            </p>
                        )}
                    </div>
                </div>

                <PassLineFields
                    total={draft.total}
                    value={draft.passLine}
                    onChange={(passLine) => patch({ passLine })}
                    ladder={ladder}
                />

                <Textarea
                    label="Syllabus"
                    value={draft.syllabus}
                    onChange={(event) => patch({ syllabus: event.target.value })}
                    rows={3}
                    maxLength={5000}
                    placeholder="What will come in this test — chapters, topics, anything. Free text."
                />
                <Textarea
                    label="Note for Family"
                    value={draft.familyNote}
                    onChange={(event) => patch({ familyNote: event.target.value })}
                    rows={2}
                    placeholder="What the guardian and the student should know about this test."
                />
            </div>

            {problems.length > 0 && (
                <ul className="space-y-1 text-[0.8rem] font-medium text-red-500" role="alert">
                    {problems.map((problem) => (
                        <li key={problem}>{problem}</li>
                    ))}
                </ul>
            )}

            <div className="flex justify-end gap-2">
                <Button variant="ghost" onClick={onClose} disabled={saving}>
                    Cancel
                </Button>
                <Button variant="primary" onClick={() => save(false)} disabled={saving}>
                    {saving ? "Saving…" : exam ? "Save changes" : "Schedule class test"}
                </Button>
            </div>

            <Modal
                open={duplicates !== null}
                title="A test already exists"
                onClose={() => setDuplicates(null)}
            >
                <div className="space-y-3 text-sm">
                    <p>
                        A test for the same section, subject and date is already on the schedule. Do
                        you want to create this one anyway?
                    </p>
                    <ul className="space-y-2">
                        {(duplicates ?? []).map((item) => (
                            <li
                                key={`${item.examId}-${item.section}`}
                                className="glass-tile rounded-xl p-3"
                            >
                                <p className="font-medium">
                                    {item.subject} · {item.section}
                                </p>
                                <p className="text-muted-foreground text-xs">
                                    {dayText(item.examDate)} · {figureText(item.totalMarks)} marks
                                    {item.createdBy ? ` · added by ${item.createdBy}` : ""}
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
                            {saving ? "Saving…" : "Create anyway"}
                        </Button>
                    </div>
                </div>
            </Modal>
        </div>
    );
}

/** Opens the form; when a test is being edited its saved syllabus is read first. */
export default function ClassTestForm(
    props: Parameters<typeof ClassTestFormBody>[0] extends infer P
        ? Omit<P & object, "savedSyllabus">
        : never,
) {
    const first = props.exam?.papers[0]?.id ?? null;
    const saved = useApiQuery(["exams", "syllabus", first], () => getSyllabus(first ?? ""), {
        enabled: first !== null,
    });
    if (first !== null && saved.isPending) return <Spinner />;
    return <ClassTestFormBody {...props} savedSyllabus={saved.data?.syllabusText ?? ""} />;
}
