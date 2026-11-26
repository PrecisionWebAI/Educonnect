"use client";

import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, CalendarDays, Pencil, Send } from "lucide-react";
import { Badge, Button, EmptyState, Spinner, Table, type Column } from "@/components/ui";
import { useToast } from "@/components/ui/toast";
import { errorMessage } from "@/lib/api/client";
import { classTestChip } from "@/lib/exams/classTest";
import { isSchoolExamType, schoolExamChip, typeLabel } from "@/lib/exams/schoolExam";
import {
    dateRangeText,
    dayText,
    examStatusChip,
    figureText,
    paperProgress,
    paperWhenText,
    scopeLabel,
} from "@/lib/exams/view";
import { detachPaper, publishDateSheet } from "@/services";
import type { ExamPaperGroup, ExamPaperPlan, ExamPlan } from "@/types";
import PaperGroupDialog from "./PaperGroupDialog";
import SyllabusDialog from "./SyllabusDialog";
import { EXAM_LIST_KEY, useExamDetail } from "./useExamPlan";
import { titleCase } from "@/lib/format";

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
    const [viewing, setViewing] = useState<ExamPaperPlan | null>(null);
    const [publishing, setPublishing] = useState(false);
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
    // A School Exam (the new date sheet) reads differently from an older exam: a date, a
    // total and a pass line per subject, a Syllabus button, and a draft/published state.
    const schoolStyle = isSchoolExamType(exam.examType);
    // A class test has no date sheet: one subject, one date, one or several sections.
    const classStyle = exam.examType === "class_test";
    const status = classStyle
        ? classTestChip(exam)
        : schoolStyle
          ? schoolExamChip(exam)
          : examStatusChip(exam.status);
    const canEdit = schoolStyle ? exam.canManage : exam.papers.some((paper) => paper.canEdit);
    const canPublish = schoolStyle && exam.canManage && !exam.datesheetPublishedAt;
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

    async function publish() {
        if (
            !window.confirm(
                "Publish this date sheet? The families can see it from now on and will be told.",
            )
        ) {
            return;
        }
        setPublishing(true);
        try {
            await publishDateSheet(examId);
            await queryClient.invalidateQueries({ queryKey: EXAM_LIST_KEY });
            toast.push("success", "Date sheet published — the families have been told.");
        } catch (cause) {
            toast.push("error", errorMessage(cause, "Could not publish the date sheet."));
        } finally {
            setPublishing(false);
        }
    }

    // A class test's papers: the subject in each section, its date, total and pass line,
    // who takes it (Assigned / Temporary), and the way into its marks.
    const classColumns: Column<ExamPaperPlan>[] = [
        {
            key: "subject",
            header: "Subject",
            render: (paper) => (
                <div className="min-w-0">
                    <p className="font-medium">{paper.subject}</p>
                    <p className="text-muted-foreground text-xs">{paper.section}</p>
                </div>
            ),
        },
        {
            key: "date",
            header: "Date",
            render: (paper) => <span className="text-sm">{dayText(paper.examDate)}</span>,
        },
        {
            key: "total",
            header: "Total marks",
            align: "right",
            render: (paper) => (
                <span className="text-sm tabular-nums">{figureText(paper.maxMarks)}</span>
            ),
        },
        {
            key: "taker",
            header: "Taken by",
            render: (paper) =>
                paper.takenByName ? (
                    <span className="flex items-center gap-1.5 text-sm">
                        <i
                            className={`tt-badge tt-badge-static ${
                                paper.isTemporary ? "tt-badge-t" : "tt-badge-s"
                            }`}
                            title={paper.isTemporary ? "Temporary teacher" : "Assigned teacher"}
                        >
                            {paper.isTemporary ? "T" : "S"}
                        </i>
                        {paper.takenByName}
                    </span>
                ) : (
                    <span className="text-muted-foreground">—</span>
                ),
        },
        {
            key: "actions",
            header: "",
            align: "right",
            render: (paper) => (
                <Button size="sm" variant="ghost" onClick={() => onOpenMarks(paper.id)}>
                    Marks
                </Button>
            ),
        },
    ];

    // The date sheet as families read it: subject, date, total, and a Syllabus
    // button that is live only once the subject teacher has written one.
    const schoolColumns: Column<ExamPaperPlan>[] = [
        {
            key: "subject",
            header: "Subject",
            render: (paper) => <span className="font-medium">{paper.subject}</span>,
        },
        {
            key: "date",
            header: "Date",
            render: (paper) => <span className="text-sm">{dayText(paper.examDate)}</span>,
        },
        {
            key: "total",
            header: "Total marks",
            align: "right",
            render: (paper) => (
                <span className="text-sm tabular-nums">{figureText(paper.maxMarks)}</span>
            ),
        },
        {
            key: "taker",
            header: "Taken by",
            render: (paper) =>
                paper.takenByName ? (
                    <span className="flex items-center gap-1.5 text-sm">
                        <i
                            className={`tt-badge tt-badge-static ${
                                paper.isTemporary ? "tt-badge-t" : "tt-badge-s"
                            }`}
                            title={paper.isTemporary ? "Temporary teacher" : "Assigned teacher"}
                        >
                            {paper.isTemporary ? "T" : "S"}
                        </i>
                        {paper.takenByName}
                    </span>
                ) : (
                    <span className="text-muted-foreground">—</span>
                ),
        },
        {
            key: "syllabus",
            header: "Syllabus",
            render: (paper) => (
                <Button
                    size="sm"
                    variant="outline"
                    disabled={!paper.hasSyllabus}
                    title={paper.hasSyllabus ? "Read the syllabus" : "Syllabus not added yet"}
                    onClick={() => setViewing(paper)}
                >
                    View
                </Button>
            ),
        },
        {
            key: "actions",
            header: "",
            align: "right",
            render: (paper) => (
                <Button size="sm" variant="ghost" onClick={() => onOpenMarks(paper.id)}>
                    Marks
                </Button>
            ),
        },
    ];

    return (
        <div className="space-y-4">
            <div className="flex items-center justify-between gap-3">
                <button type="button" onClick={onBack} className="classroom-back-link">
                    <ArrowLeft aria-hidden="true" className="size-4" />
                    Back to the exams
                </button>
                <div className="flex flex-wrap gap-2">
                    {/* Results of a class test or a School Exam live in the Overall Result tab. */}
                    {!schoolStyle && !classStyle && (
                        <Button size="sm" variant="outline" onClick={onOpenResults}>
                            Results
                        </Button>
                    )}
                    {canPublish && (
                        <Button size="sm" variant="primary" loading={publishing} onClick={publish}>
                            <Send aria-hidden="true" className="mr-1 size-4" />
                            Publish date sheet
                        </Button>
                    )}
                    {canEdit && (
                        <Button size="sm" variant="ghost" onClick={() => onEdit(exam)}>
                            <Pencil aria-hidden="true" className="mr-1 size-4" />
                            {classStyle ? "Edit the test" : "Edit the date sheet"}
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
                {classStyle ? (
                    <p className="text-muted-foreground text-sm">
                        Class Test · {dayText(exam.papers[0]?.examDate)}
                    </p>
                ) : schoolStyle ? (
                    <p className="text-muted-foreground text-sm">
                        {typeLabel(exam.examType)} ·{" "}
                        {exam.datesheetPublishedAt
                            ? "Published — the families can see it"
                            : "Draft — the families cannot see it until it is published"}
                    </p>
                ) : (
                    <p className="text-muted-foreground text-sm">
                        {dateRangeText(exam.startDate, exam.endDate)}
                        {exam.term ? ` · ${exam.term}` : ""}
                        {exam.examType ? ` · ${titleCase(exam.examType)}` : ""}
                    </p>
                )}
                {exam.familyNote && <p className="text-sm">{exam.familyNote}</p>}
                {exam.note && <p className="text-sm">{exam.note}</p>}
            </div>

            <Table
                columns={
                    schoolStyle
                        ? schoolColumns
                        : classStyle
                          ? classColumns
                          : [
                                {
                                    key: "subject",
                                    header: "Subject",
                                    render: (paper: ExamPaperPlan) => (
                                        <div className="min-w-0">
                                            <p className="flex flex-wrap items-center gap-1.5 font-medium">
                                                {paper.title}
                                                {paper.paperGroupId && (
                                                    <Badge tone="violet">Shared</Badge>
                                                )}
                                            </p>
                                            <p className="text-muted-foreground text-xs">
                                                {paper.section}
                                                {paper.title !== paper.subject
                                                    ? ` · ${paper.subject}`
                                                    : ""}
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
                            ]
                }
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

            <SyllabusDialog
                paperId={viewing?.id ?? null}
                subject={viewing?.subject ?? ""}
                editable={false}
                onClose={() => setViewing(null)}
            />

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
