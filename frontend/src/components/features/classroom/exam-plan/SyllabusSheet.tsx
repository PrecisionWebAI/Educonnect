"use client";

import { useState } from "react";
import { ArrowLeft } from "lucide-react";
import { Badge, Button, EmptyState, Spinner, Table } from "@/components/ui";
import { typeLabel } from "@/lib/exams/schoolExam";
import { dayText } from "@/lib/exams/view";
import type { ExamPaperPlan } from "@/types";
import SyllabusDialog from "./SyllabusDialog";
import { useExamDetail } from "./useExamPlan";

// The **Syllabus** screen of a School Exam: every subject of the date sheet, whether its
// syllabus is written, and a button to write it (the subject teacher for their own
// subject; the class teacher and leadership for any) or to read it. It is a separate
// screen from the Date Sheet on purpose: the class teacher sets the dates, the subject
// teachers write what is in them.

export default function SyllabusSheet({ examId, onBack }: { examId: string; onBack: () => void }) {
    const query = useExamDetail(examId);
    const [open, setOpen] = useState<ExamPaperPlan | null>(null);
    if (query.isPending) return <Spinner />;
    const exam = query.data;
    if (!exam) {
        return (
            <EmptyState
                icon="📄"
                title="This exam could not be read"
                body="It may have been removed, or it is not one you can see."
            />
        );
    }

    return (
        <div className="space-y-4">
            <button type="button" onClick={onBack} className="classroom-back-link">
                <ArrowLeft aria-hidden="true" className="size-4" />
                Back to the exams
            </button>

            <div className="glass-tile space-y-1 rounded-2xl p-4 sm:p-5">
                <h3 className="text-base font-semibold tracking-tight">{exam.name} · Syllabus</h3>
                <p className="text-muted-foreground text-sm">
                    {typeLabel(exam.examType)} — each subject teacher writes what will come in their
                    subject.
                </p>
            </div>

            <Table
                columns={[
                    {
                        key: "subject",
                        header: "Subject",
                        render: (paper: ExamPaperPlan) => (
                            <div className="min-w-0">
                                <p className="font-medium">{paper.subject}</p>
                                <p className="text-muted-foreground text-xs">
                                    {paper.assignedTeacherName ?? "No teacher assigned"}
                                </p>
                            </div>
                        ),
                    },
                    {
                        key: "date",
                        header: "Date",
                        render: (paper: ExamPaperPlan) => (
                            <span className="text-sm">{dayText(paper.examDate)}</span>
                        ),
                    },
                    {
                        key: "state",
                        header: "Syllabus",
                        render: (paper: ExamPaperPlan) => (
                            <Badge tone={paper.hasSyllabus ? "green" : "muted"}>
                                {paper.hasSyllabus ? "Written" : "Not written"}
                            </Badge>
                        ),
                    },
                    {
                        key: "actions",
                        header: "",
                        align: "right",
                        render: (paper: ExamPaperPlan) =>
                            paper.canSyllabus ? (
                                <Button size="sm" variant="outline" onClick={() => setOpen(paper)}>
                                    {paper.hasSyllabus ? "Edit" : "Write"}
                                </Button>
                            ) : (
                                <Button
                                    size="sm"
                                    variant="ghost"
                                    disabled={!paper.hasSyllabus}
                                    onClick={() => setOpen(paper)}
                                >
                                    View
                                </Button>
                            ),
                    },
                ]}
                rows={exam.papers}
                rowKey={(paper) => paper.id}
                empty="No subject is on this date sheet."
            />

            <SyllabusDialog
                paperId={open?.id ?? null}
                subject={open?.subject ?? ""}
                editable={Boolean(open?.canSyllabus)}
                onClose={() => setOpen(null)}
            />
        </div>
    );
}
