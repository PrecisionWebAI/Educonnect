"use client";

import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import { Button, Select, Spinner, Textarea } from "@/components/ui";
import { useToast } from "@/components/ui/toast";
import { errorMessage } from "@/lib/api/client";
import { useApiQuery } from "@/lib/api/use-api-query";
import { titleCase } from "@/lib/format";
import { getSyllabus, setSyllabus } from "@/services";
import type { ExamPaperPlan, ExamPlan } from "@/types";
import { EXAM_LIST_KEY } from "./useExamPlan";

// Create (or change) the syllabus of one subject of a date sheet - free text.
//
//   Exam [Half Yearly]      Subject [Mathematics]
//   Syllabus written by [Assigned teacher - Meera | any other teacher -> Temporary]
//   Syllabus  ................................................
//
// The assigned subject teacher writes it by default; another teacher can be picked for
// this one (the same S / T badge as "Test Taken By" on a class test). Everybody reads it
// from the **Open** view of the exam.

export default function SyllabusForm({
    exams,
    teachers,
    onClose,
}: {
    /** This section's date sheets (not archived). */
    exams: ExamPlan[];
    teachers: { employeeId: string; name: string }[];
    onClose: () => void;
}) {
    const [examId, setExamId] = useState(exams[0]?.id ?? "");
    const exam = exams.find((item) => item.id === examId);
    const writable = (exam?.papers ?? []).filter((paper) => paper.canSyllabus);
    const [paperId, setPaperId] = useState("");
    const paper = writable.find((item) => item.id === paperId) ?? writable[0];

    return (
        <div className="space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
                <button type="button" onClick={onClose} className="classroom-back-link">
                    <ArrowLeft aria-hidden="true" className="size-4" />
                    Back to the exams
                </button>
                <span className="text-muted-foreground text-xs">New syllabus</span>
            </div>

            <div className="glass-tile space-y-4 rounded-2xl p-4 sm:p-5">
                {exams.length === 0 ? (
                    <p className="text-muted-foreground text-sm">
                        Create the date sheet first — a syllabus belongs to an exam.
                    </p>
                ) : (
                    <div className="grid gap-3 sm:grid-cols-2">
                        <Select
                            label="Exam"
                            value={examId}
                            onChange={(event) => {
                                setExamId(event.target.value);
                                setPaperId("");
                            }}
                        >
                            {exams.map((item) => (
                                <option key={item.id} value={item.id}>
                                    {titleCase(item.name)}
                                </option>
                            ))}
                        </Select>
                        <Select
                            label="Subject"
                            value={paper?.id ?? ""}
                            onChange={(event) => setPaperId(event.target.value)}
                        >
                            {writable.length === 0 && (
                                <option value="">No subject you can write</option>
                            )}
                            {writable.map((item) => (
                                <option key={item.id} value={item.id}>
                                    {titleCase(item.subject)}
                                </option>
                            ))}
                        </Select>
                    </div>
                )}

                {paper && (
                    <Fields key={paper.id} paper={paper} teachers={teachers} onClose={onClose} />
                )}
                {exam && writable.length === 0 && (
                    <p className="text-muted-foreground text-sm">
                        Only a subject&apos;s teacher, the teacher picked for it, the class teacher
                        or the school&apos;s leadership can write its syllabus.
                    </p>
                )}
            </div>
        </div>
    );
}

function Fields({
    paper,
    teachers,
    onClose,
}: {
    paper: ExamPaperPlan;
    teachers: { employeeId: string; name: string }[];
    onClose: () => void;
}) {
    const queryClient = useQueryClient();
    const toast = useToast();
    const saved = useApiQuery(["exams", "syllabus", paper.id], () => getSyllabus(paper.id));
    if (saved.isPending) return <Spinner />;
    return (
        <Editor
            paper={paper}
            teachers={teachers}
            initial={saved.data?.syllabusText ?? ""}
            onSaved={async () => {
                await Promise.all([
                    queryClient.invalidateQueries({ queryKey: ["exams", "syllabus", paper.id] }),
                    queryClient.invalidateQueries({ queryKey: EXAM_LIST_KEY }),
                ]);
                toast.push("success", "Syllabus saved.");
                onClose();
            }}
        />
    );
}

function Editor({
    paper,
    teachers,
    initial,
    onSaved,
}: {
    paper: ExamPaperPlan;
    teachers: { employeeId: string; name: string }[];
    initial: string;
    onSaved: () => Promise<void>;
}) {
    const toast = useToast();
    const assignedId = paper.assignedTeacherId ?? "";
    const assignedName = paper.assignedTeacherName;
    // "" = the assigned teacher; anything else is a temporary writer.
    const [by, setBy] = useState(
        paper.syllabusIsTemporary ? (paper.syllabusByEmployeeId ?? "") : "",
    );
    const [text, setText] = useState(initial);
    const [saving, setSaving] = useState(false);
    const isAssigned = by === "" || by === assignedId;

    async function save() {
        setSaving(true);
        try {
            await setSyllabus(paper.id, text, by === "" ? null : by);
            await onSaved();
        } catch (cause) {
            toast.push("error", errorMessage(cause, "Could not save the syllabus"));
        } finally {
            setSaving(false);
        }
    }

    return (
        <div className="space-y-4">
            <div className="space-y-2">
                <Select
                    label="Syllabus Written By"
                    value={by}
                    onChange={(event) => setBy(event.target.value)}
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
                {(by !== "" || assignedId) && (
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
            </div>

            <Textarea
                label="Syllabus"
                value={text}
                onChange={(event) => setText(event.target.value)}
                rows={6}
                maxLength={5000}
                placeholder="What will come in this subject's exam — chapters, topics, anything. Free text."
            />

            <div className="flex justify-end gap-2">
                <Button onClick={save} loading={saving} disabled={saving}>
                    Save syllabus
                </Button>
            </div>
        </div>
    );
}
