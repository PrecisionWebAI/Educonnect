"use client";

import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, CalendarDays, Pencil } from "lucide-react";
import { Badge, Button, EmptyState, Spinner, Table } from "@/components/ui";
import { useToast } from "@/components/ui/toast";
import { errorMessage } from "@/lib/api/client";
import {
    dateRangeText,
    examStatusChip,
    paperProgress,
    paperWhenText,
    scopeLabel,
} from "@/lib/exams/view";
import { detachPaper } from "@/services";
import type { ExamPaperGroup, ExamPaperPlan, ExamPlan } from "@/types";
import PaperGroupDialog from "./PaperGroupDialog";
import { EXAM_LIST_KEY, useExamDetail } from "./useExamPlan";

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
//
// A paper belongs to one **section's** subject. Sections that sit the same question
// paper share a group: its title and chapters are edited once (until marks exist), and
// any section can be given a paper of its own - the group stays for everyone else.

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
    const queryClient = useQueryClient();
    const toast = useToast();
    const [editingGroup, setEditingGroup] = useState<ExamPaperGroup | null>(null);
    const [detaching, setDetaching] = useState<string | null>(null);
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
    const shownGroups = exam.groups.filter((group) =>
        ownPapers.some((paper) => paper.paperGroupId === group.id),
    );

    async function detach(paper: ExamPaperPlan) {
        if (!paper.paperGroupId) return;
        setDetaching(paper.id);
        try {
            await detachPaper(paper.paperGroupId, paper.id);
            await queryClient.invalidateQueries({ queryKey: EXAM_LIST_KEY });
            toast.push("success", `${paper.section} now has its own ${paper.subject} paper.`);
        } catch (cause) {
            toast.push("error", errorMessage(cause, "Could not give that section its own paper."));
        } finally {
            setDetaching(null);
        }
    }

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
                                <p className="flex flex-wrap items-center gap-1.5 font-medium">
                                    {paper.title}
                                    {paper.paperGroupId && <Badge tone="violet">Shared</Badge>}
                                </p>
                                <p className="text-muted-foreground text-xs">
                                    {paper.section}
                                    {paper.title !== paper.subject ? ` · ${paper.subject}` : ""}
                                </p>
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
                            <div className="flex justify-end gap-1">
                                {paper.canDetach && (
                                    <Button
                                        size="sm"
                                        variant="ghost"
                                        loading={detaching === paper.id}
                                        title="Give this section a question paper of its own"
                                        onClick={() => detach(paper)}
                                    >
                                        Own paper
                                    </Button>
                                )}
                                <Button
                                    size="sm"
                                    variant="ghost"
                                    onClick={() => onOpenMarks(paper.id)}
                                >
                                    Marks
                                </Button>
                            </div>
                        ),
                    },
                ]}
                rows={ownPapers}
                rowKey={(paper) => paper.id}
                empty="No paper has been added to this exam yet."
            />

            {shownGroups.length > 0 && (
                <div className="glass-tile space-y-2 rounded-2xl p-4">
                    <h4 className="text-sm font-semibold">Shared question papers</h4>
                    {shownGroups.map((group) => (
                        <div
                            key={group.id}
                            className="flex flex-wrap items-center justify-between gap-2 text-sm"
                        >
                            <span>
                                {group.displayTitle ?? "Shared paper"}
                                <span className="text-muted-foreground ml-2 text-xs">
                                    {group.paperIds.length} sections ·{" "}
                                    {group.chapters.length > 0
                                        ? group.chapters.join(", ")
                                        : "no syllabus set"}
                                </span>
                            </span>
                            <span className="flex items-center gap-2">
                                {group.locked && <Badge tone="amber">Locked</Badge>}
                                {canEdit && (
                                    <Button
                                        size="sm"
                                        variant="outline"
                                        onClick={() => setEditingGroup(group)}
                                    >
                                        {group.locked ? "View" : "Edit"}
                                    </Button>
                                )}
                            </span>
                        </div>
                    ))}
                </div>
            )}

            {otherPapers > 0 && (
                <p className="text-muted-foreground text-xs">
                    {otherPapers} more {otherPapers === 1 ? "paper belongs" : "papers belong"} to
                    other classes in this school-wide exam. They are filled in from their own class
                    pages.
                </p>
            )}

            <PaperGroupDialog
                group={editingGroup}
                papers={exam.papers.filter((paper) => paper.paperGroupId === editingGroup?.id)}
                open={editingGroup !== null}
                onOpenChange={(open) => {
                    if (!open) setEditingGroup(null);
                }}
            />
        </div>
    );
}
