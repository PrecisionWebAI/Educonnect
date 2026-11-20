"use client";

import { useMemo, useState } from "react";
import { ClipboardList, Plus } from "lucide-react";
import { Badge, Button, Spinner, Table, Tabs } from "@/components/ui";
import AcademicYearRequiredBanner from "@/components/layout/AcademicYearRequiredBanner";
import { useAuth } from "@/providers/auth-context";
import { ACADEMIC_STAFF_ROLES, LEADERSHIP_ROLES, hasAnyRole } from "@/lib/auth/rbac";
import {
    dateRangeText,
    examStatusChip,
    forSection,
    splitByScope,
    type ExamScopeWord,
} from "@/lib/exams/view";
import type { ExamPlan } from "@/types";
import DateSheet from "./DateSheet";
import ExamScheduleForm from "./ExamScheduleForm";
import MarksGrid from "./MarksGrid";
import ResultsView from "./ResultsView";
import { useExamList } from "./useExamPlan";

// The **Exams** tab of a class-section (Phase 8).
//
// Two sub-tabs, because the two kinds of exam behave differently:
//
//   Class Exams  - *this* class-section sits them. Planned here (its teacher, or the
//                  office), with a date sheet, marks entry, publication and results.
//   School Exams - every class sits them, so the office plans them **once** and each
//                  class sits its own paper per subject. This page reads them, fills
//                  in its own papers and reads its own results; it never re-cuts the
//                  whole date sheet from one room's page.
//
// The list read is unfiltered on purpose: the server decides what a teacher may see
// (the exams they hold a subject in), so asking again here would only invent a rule
// the API does not have.

type View =
    | { kind: "list" }
    | { kind: "exam"; examId: string }
    | { kind: "marks"; examId: string; paperId: string }
    | { kind: "results"; examId: string };

const TABS = ["Class Exams", "School Exams"] as const;

export default function ExamsPlanPanel({
    sectionId,
    classroomId,
    classId,
    classLabel,
    className,
    subjects,
}: {
    sectionId: string;
    classroomId: string;
    /** The class the page shows - a class-level exam is the whole class's. */
    classId: string | null;
    /** "Class 10-A" - what the toolbar says. */
    classLabel: string;
    /** "Class 10" - the class a paper is for. */
    className: string;
    /** The section's own subjects, for the schedule form. */
    subjects: { id: string; name: string }[];
}) {
    const { user } = useAuth();
    const list = useExamList();
    const [tab, setTab] = useState<(typeof TABS)[number]>("Class Exams");
    const [view, setView] = useState<View>({ kind: "list" });
    const [form, setForm] = useState<{ scope: ExamScopeWord; exam: ExamPlan | null } | null>(null);

    const exams = useMemo(() => list.data ?? [], [list.data]);
    const byScope = useMemo(() => splitByScope(exams), [exams]);
    const classExams = useMemo(
        () => forSection(exams, { classroomId, classId }),
        [exams, classroomId, classId],
    );

    const canPlanClass = hasAnyRole(user?.roles, ACADEMIC_STAFF_ROLES);
    const canPlanSchool = hasAnyRole(user?.roles, LEADERSHIP_ROLES);
    const scope: ExamScopeWord = tab === "Class Exams" ? "class" : "school";
    const rows = scope === "class" ? classExams : byScope.school;
    const canPlan = scope === "class" ? canPlanClass : canPlanSchool;

    if (list.isPending) return <Spinner />;

    if (view.kind === "marks") {
        return (
            <MarksGrid
                examId={view.examId}
                paperId={view.paperId}
                onBack={() => setView({ kind: "exam", examId: view.examId })}
            />
        );
    }

    if (view.kind === "results") {
        return <ResultsView examId={view.examId} onBack={() => setView({ kind: "list" })} />;
    }

    if (view.kind === "exam") {
        return (
            <DateSheet
                examId={view.examId}
                classId={classId}
                onBack={() => setView({ kind: "list" })}
                onOpenMarks={(paperId) => setView({ kind: "marks", examId: view.examId, paperId })}
                onOpenResults={() => setView({ kind: "results", examId: view.examId })}
                onEdit={(exam) => setForm({ scope: exam.scope, exam })}
            />
        );
    }

    if (form) {
        return (
            <ExamScheduleForm
                scope={form.scope}
                exam={form.exam}
                sectionId={sectionId}
                classroomId={classroomId}
                classId={classId}
                className={className}
                subjects={subjects}
                onClose={() => setForm(null)}
            />
        );
    }

    return (
        <div className="space-y-4">
            <AcademicYearRequiredBanner />
            <div className="toolbar justify-between">
                <div className="flex items-center gap-2">
                    <ClipboardList aria-hidden="true" className="text-primary size-4" />
                    <span className="text-sm font-semibold">
                        {scope === "class" ? `${classLabel} exams` : "School-wide exams"}
                    </span>
                    <span className="text-muted-foreground text-xs">
                        {rows.length} {rows.length === 1 ? "exam" : "exams"}
                    </span>
                </div>
                {canPlan && (
                    <Button size="sm" onClick={() => setForm({ scope, exam: null })}>
                        <Plus aria-hidden="true" className="mr-1 size-4" />
                        {scope === "class" ? "Plan a class exam" : "Plan a school exam"}
                    </Button>
                )}
            </div>

            <Tabs tabs={[...TABS]} active={tab} onChange={(next) => setTab(next as typeof tab)} />

            <ExamTable rows={rows} onOpen={setView} />

            {scope === "school" && (
                <p className="text-muted-foreground text-xs">
                    A school-wide exam carries one paper per class and subject. Marks are entered on
                    the paper this class sits; the other classes&apos; papers belong to their own
                    pages.
                </p>
            )}
        </div>
    );
}

/** The list itself - one table, whichever sub-tab is open. */
function ExamTable({ rows, onOpen }: { rows: ExamPlan[]; onOpen: (view: View) => void }) {
    return (
        <Table
            columns={[
                {
                    key: "name",
                    header: "Exam",
                    render: (exam: ExamPlan) => (
                        <div className="min-w-0">
                            <p className="truncate font-medium">{exam.name}</p>
                            <p className="text-muted-foreground truncate text-xs">
                                {[exam.term, exam.examType].filter(Boolean).join(" · ") || "—"}
                            </p>
                        </div>
                    ),
                },
                {
                    key: "dates",
                    header: "Date sheet",
                    render: (exam: ExamPlan) => (
                        <span className="text-sm">
                            {dateRangeText(exam.startDate, exam.endDate)}
                        </span>
                    ),
                },
                {
                    key: "papers",
                    header: "Papers",
                    align: "right",
                    render: (exam: ExamPlan) => (
                        <span className="text-sm tabular-nums">{exam.papers.length}</span>
                    ),
                },
                {
                    key: "status",
                    header: "Status",
                    render: (exam: ExamPlan) => {
                        const chip = examStatusChip(exam.status);
                        return <Badge tone={chip.tone}>{chip.label}</Badge>;
                    },
                },
                {
                    key: "actions",
                    header: "",
                    align: "right",
                    render: (exam: ExamPlan) => (
                        <div className="flex justify-end gap-2">
                            <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => onOpen({ kind: "exam", examId: exam.id })}
                            >
                                Open
                            </Button>
                            <Button
                                size="sm"
                                variant="outline"
                                onClick={() => onOpen({ kind: "results", examId: exam.id })}
                            >
                                Results
                            </Button>
                        </div>
                    ),
                },
            ]}
            rows={rows}
            rowKey={(exam) => exam.id}
            empty="No exam has been planned here yet."
        />
    );
}
