"use client";

import { ArrowLeft, CalendarDays, Pencil } from "lucide-react";
import { Badge, Button, EmptyState, Spinner, Table } from "@/components/ui";
import {
    dateRangeText,
    examStatusChip,
    paperProgress,
    paperWhenText,
    scopeLabel,
} from "@/lib/exams/view";
import type { ExamPaperPlan, ExamPlan } from "@/types";
import { useExamDetail } from "./useExamPlan";

// One exam, and every sitting in it (Phase 8).
//
// The date sheet is the sheet of paper a school actually pins up: subject, date,
// hours, room, what it is out of and the chapters it covers. Each row opens the
// marks sheet for that paper; `Published` is the state families can see, so the
// row says it before it says how many marks are in.
//
// A school-wide exam is planned once by the office and each class sits its own
// paper per subject, so this page draws **its own class's** papers and counts the
// rest - it never pretends another class's paper is this room's to fill in.

export default function DateSheet({
    examId,
    classId,
    onBack,
    onOpenMarks,
    onOpenResults,
    onEdit,
}: {
    examId: string;
    /** The class this page is standing in - a school exam's other papers are not ours. */
    classId?: string | null;
    onBack: () => void;
    onOpenMarks: (paperId: string) => void;
    onOpenResults: () => void;
    onEdit: (exam: ExamPlan) => void;
}) {
    const query = useExamDetail(examId);
    if (query.isPending) return <Spinner />;

    const exam = query.data;
    if (!exam) {
        return (
            <EmptyState
                icon="📄"
                title="This exam could not be read"
                body="It may have been removed, or it belongs to a class you do not teach."
            />
        );
    }

    const ownPapers =
        exam.scope === "school" && classId
            ? exam.papers.filter((paper) => paper.classId === classId)
            : exam.papers;
    const otherPapers = exam.papers.length - ownPapers.length;
    const status = examStatusChip(exam.status);
    const canEdit = exam.papers.some((paper) => paper.canEdit);

    return (
        <div className="space-y-4">
            <div className="flex items-center justify-between gap-3">
                <button type="button" onClick={onBack} className="classroom-back-link">
                    <ArrowLeft aria-hidden="true" className="size-4" />
                    Back to the exams
                </button>
                <div className="flex flex-wrap gap-2">
                    <Button size="sm" variant="outline" onClick={onOpenResults}>
                        Results
                    </Button>
                    {canEdit && (
                        <Button size="sm" variant="ghost" onClick={() => onEdit(exam)}>
                            <Pencil aria-hidden="true" className="mr-1 size-4" />
                            Edit the date sheet
                        </Button>
                    )}
                </div>
            </div>

            <div className="glass-tile space-y-2 rounded-2xl p-4 sm:p-5">
                <div className="flex flex-wrap items-center gap-2">
                    <CalendarDays aria-hidden="true" className="text-primary size-4" />
                    <h3 className="text-base font-semibold tracking-tight">{exam.name}</h3>
                    <Badge tone={status.tone}>{status.label}</Badge>
                    <Badge tone="muted">{scopeLabel(exam.scope)}</Badge>
                </div>
                <p className="text-muted-foreground text-sm">
                    {dateRangeText(exam.startDate, exam.endDate)}
                    {exam.term ? ` · ${exam.term}` : ""}
                    {exam.examType ? ` · ${exam.examType}` : ""}
                </p>
                {exam.note && <p className="text-sm">{exam.note}</p>}
            </div>

            <Table
                columns={[
                    {
                        key: "subject",
                        header: "Subject",
                        render: (paper: ExamPaperPlan) => (
                            <div className="min-w-0">
                                <p className="font-medium">{paper.subject}</p>
                                <p className="text-muted-foreground truncate text-xs">
                                    {paper.chapters.length > 0
                                        ? paper.chapters.join(", ")
                                        : "No syllabus set"}
                                </p>
                            </div>
                        ),
                    },
                    {
                        key: "when",
                        header: "Sitting",
                        render: (paper: ExamPaperPlan) => (
                            <span className="text-sm">{paperWhenText(paper)}</span>
                        ),
                    },
                    {
                        key: "marks",
                        header: "Progress",
                        render: (paper: ExamPaperPlan) => {
                            const progress = paperProgress(paper, 0);
                            return <Badge tone={progress.tone}>{progress.label}</Badge>;
                        },
                    },
                    {
                        key: "actions",
                        header: "",
                        align: "right",
                        render: (paper: ExamPaperPlan) => (
                            <Button size="sm" variant="ghost" onClick={() => onOpenMarks(paper.id)}>
                                Marks
                            </Button>
                        ),
                    },
                ]}
                rows={ownPapers}
                rowKey={(paper) => paper.id}
                empty="No paper has been added to this exam yet."
            />

            {otherPapers > 0 && (
                <p className="text-muted-foreground text-xs">
                    {otherPapers} more {otherPapers === 1 ? "paper belongs" : "papers belong"} to
                    other classes in this school-wide exam. They are filled in from their own class
                    pages.
                </p>
            )}
        </div>
    );
}
