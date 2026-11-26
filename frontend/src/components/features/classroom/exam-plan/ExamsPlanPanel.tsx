"use client";

import { useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { ClipboardList, Plus } from "lucide-react";
import { Badge, Button, Select, Spinner, Table, Tabs } from "@/components/ui";
import { useToast } from "@/components/ui/toast";
import { errorMessage } from "@/lib/api/client";
import {
    classTestChip,
    paperOfSection,
    sectionsText,
    splitByDate,
    todayText,
} from "@/lib/exams/classTest";
import {
    isSchoolExamType,
    schoolExamChip,
    splitSchoolByDate,
    typeLabel,
} from "@/lib/exams/schoolExam";
import {
    archiveClassTest,
    archiveSchoolExam,
    cancelClassTest,
    cancelSchoolExam,
    publishDateSheet,
} from "@/services";
import AcademicYearRequiredBanner from "@/components/layout/AcademicYearRequiredBanner";
import { useAuth } from "@/providers/auth-context";
import { ACADEMIC_STAFF_ROLES, hasAnyRole } from "@/lib/auth/rbac";
import {
    dateRangeText,
    dayText,
    examStatusChip,
    figureText,
    forSection,
    splitByScope,
    type ExamScopeWord,
} from "@/lib/exams/view";
import type { ExamPlan } from "@/types";
import ClassTestForm from "./ClassTestForm";
import SyllabusDialog from "./SyllabusDialog";
import DateSheet from "./DateSheet";
import ExamResultPanel from "./ExamResultPanel";
import ExamScheduleForm from "./ExamScheduleForm";
import MarksGrid from "./MarksGrid";
import SchoolExamForm from "./SchoolExamForm";
import SyllabusForm from "./SyllabusForm";
import SyllabusSheet from "./SyllabusSheet";
import ResultsView from "./ResultsView";
import { EXAM_LIST_KEY, useExamList } from "./useExamPlan";
import { titleCase } from "@/lib/format";

// The **Exams** tab of a class-section (Phase 8).
//
// Two sub-tabs, because the two kinds of exam behave differently:
//
//   Class Test  - one subject, one date, one or several sections of this class. The
//                 subject teacher, the class teacher or the leadership schedules it
//                 (`ClassTestForm`); there is no date sheet.
//   School Exam - every class sits them, so the office plans them **once** and each
//                 class sits its own paper per subject. This page reads them, fills
//                 in its own papers and reads its own results; it never re-cuts the
//                 whole date sheet from one room's page.
//
// The list read is unfiltered on purpose: the server decides what a teacher may see
// (the exams they hold a subject in), so asking again here would only invent a rule
// the API does not have.

type View =
    | { kind: "list" }
    | { kind: "exam"; examId: string }
    | { kind: "marks"; examId: string; paperId: string; from?: "list" }
    | { kind: "results"; examId: string }
    | { kind: "syllabus"; examId: string };

const TABS = ["Class Test", "School Exam", "Overall Result"] as const;

export default function ExamsPlanPanel({
    sectionId,
    classroomId,
    classId,
    classLabel,
    className,
    subjects,
    teachers = [],
}: {
    sectionId: string;
    classroomId: string;
    /** The class the page shows - a class-level exam is the whole class's. */
    classId: string | null;
    /** "Class 10-A" - what the toolbar says. */
    classLabel: string;
    /** "Class 10" - the class a paper is for. */
    className: string;
    /** The section's own subjects (with their assigned teacher), for the schedule form. */
    subjects: { id: string; name: string; teacherId?: string | null }[];
    /** Teachers who can take a test (the "Test Taken By" dropdown). */
    teachers?: { employeeId: string; name: string }[];
}) {
    const { user } = useAuth();
    const list = useExamList();
    const [tab, setTab] = useState<(typeof TABS)[number]>("Class Test");
    const [view, setView] = useState<View>({ kind: "list" });
    const [form, setForm] = useState<{ scope: ExamScopeWord; exam: ExamPlan | null } | null>(null);
    const [classForm, setClassForm] = useState<{ exam: ExamPlan | null } | null>(null);
    const [schoolForm, setSchoolForm] = useState<{ exam: ExamPlan | null } | null>(null);
    const [syllabusForm, setSyllabusForm] = useState(false);

    const exams = useMemo(() => list.data ?? [], [list.data]);
    const byScope = useMemo(() => splitByScope(exams), [exams]);
    const classExams = useMemo(
        () => forSection(exams, { classroomId, classId }),
        [exams, classroomId, classId],
    );

    const canPlanClass = hasAnyRole(user?.roles, ACADEMIC_STAFF_ROLES);
    const scope: ExamScopeWord = tab === "Class Test" ? "class" : "school";
    // The Class Test tab holds class tests only; an older class-level exam of another
    // type is a school-style exam, so it reads under School Exam.
    const classTests = useMemo(
        () => classExams.filter((exam) => exam.examType === "class_test"),
        [classExams],
    );
    const schoolRows = useMemo(
        () => [...byScope.school, ...classExams.filter((exam) => exam.examType !== "class_test")],
        [byScope.school, classExams],
    );
    const rows = scope === "class" ? classTests : schoolRows;
    // Both kinds are set from this section's page by its staff; the server decides who may
    // (the class teacher or leadership for a date sheet, the subject teacher for a test).
    const canPlan = canPlanClass;

    if (list.isPending) return <Spinner />;

    if (view.kind === "marks") {
        return (
            <MarksGrid
                examId={view.examId}
                paperId={view.paperId}
                onBack={() =>
                    setView(
                        view.from === "list"
                            ? { kind: "list" }
                            : { kind: "exam", examId: view.examId },
                    )
                }
            />
        );
    }

    if (view.kind === "results") {
        return <ResultsView examId={view.examId} onBack={() => setView({ kind: "list" })} />;
    }

    if (view.kind === "syllabus") {
        return <SyllabusSheet examId={view.examId} onBack={() => setView({ kind: "list" })} />;
    }

    if (syllabusForm) {
        return (
            <SyllabusForm
                exams={schoolRows.filter(
                    (exam) => isSchoolExamType(exam.examType) && !exam.archivedAt,
                )}
                teachers={teachers}
                onClose={() => setSyllabusForm(false)}
            />
        );
    }

    if (schoolForm) {
        return (
            <SchoolExamForm
                exam={schoolForm.exam}
                classroomId={classroomId}
                className={className}
                subjects={subjects}
                teachers={teachers}
                onClose={() => setSchoolForm(null)}
            />
        );
    }

    if (view.kind === "exam") {
        return (
            <DateSheet
                examId={view.examId}
                classId={classId}
                onBack={() => setView({ kind: "list" })}
                onOpenMarks={(paperId) => setView({ kind: "marks", examId: view.examId, paperId })}
                onOpenResults={() => setView({ kind: "results", examId: view.examId })}
                onEdit={(exam) =>
                    exam.examType === "class_test"
                        ? setClassForm({ exam })
                        : isSchoolExamType(exam.examType)
                          ? setSchoolForm({ exam })
                          : setForm({ scope: exam.scope, exam })
                }
            />
        );
    }

    if (classForm) {
        return (
            <ClassTestForm
                exam={classForm.exam}
                classroomId={classroomId}
                className={className}
                subjects={subjects}
                teachers={teachers}
                onClose={() => setClassForm(null)}
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
            {tab !== "Overall Result" && (
                <div className="toolbar justify-between">
                    <div className="flex items-center gap-2">
                        <ClipboardList aria-hidden="true" className="text-primary size-4" />
                        <span className="text-sm font-semibold">
                            {scope === "class" ? `${classLabel} class tests` : "School-wide exams"}
                        </span>
                        <span className="text-muted-foreground text-xs">
                            {rows.length}{" "}
                            {scope === "class"
                                ? rows.length === 1
                                    ? "test"
                                    : "tests"
                                : rows.length === 1
                                  ? "exam"
                                  : "exams"}
                        </span>
                    </div>
                    {canPlan && (
                        <div className="flex flex-wrap gap-2">
                            {scope === "school" && (
                                <Button
                                    size="sm"
                                    variant="outline"
                                    onClick={() => setSyllabusForm(true)}
                                >
                                    <Plus aria-hidden="true" className="mr-1 size-4" />
                                    Create syllabus
                                </Button>
                            )}
                            <Button
                                size="sm"
                                onClick={() =>
                                    scope === "class"
                                        ? setClassForm({ exam: null })
                                        : setSchoolForm({ exam: null })
                                }
                            >
                                <Plus aria-hidden="true" className="mr-1 size-4" />
                                {scope === "class"
                                    ? "Schedule a class test"
                                    : "Create the date sheet"}
                            </Button>
                        </div>
                    )}
                </div>
            )}

            <Tabs tabs={[...TABS]} active={tab} onChange={(next) => setTab(next as typeof tab)} />

            {tab === "Overall Result" ? (
                <ExamResultPanel classroomId={classroomId} />
            ) : scope === "class" ? (
                <ClassTestTable
                    rows={classTests}
                    classroomId={classroomId}
                    onOpen={setView}
                    onEdit={(exam) => setClassForm({ exam })}
                />
            ) : (
                <SchoolExamTable rows={schoolRows} onOpen={setView} onEdit={setSchoolForm} />
            )}

            {scope === "school" && tab !== "Overall Result" && (
                <p className="text-muted-foreground text-xs">
                    The class teacher sets the date sheet and publishes it; each subject teacher
                    writes the syllabus of their own subject. Families see nothing until it is
                    published.
                </p>
            )}
        </div>
    );
}

/**
 * The School Exam list: a date sheet per exam, with the buttons that are this caller's.
 *
 * The **Date Sheet** button (class teacher / leadership) and the **Syllabus** button (the
 * subject teachers) are separate on purpose - they are different people's work. An older
 * exam (a free-text type) keeps only Open and Results.
 */
function SchoolExamTable({
    rows,
    onOpen,
    onEdit,
}: {
    rows: ExamPlan[];
    onOpen: (view: View) => void;
    onEdit: (form: { exam: ExamPlan | null }) => void;
}) {
    const queryClient = useQueryClient();
    const toast = useToast();
    const [busy, setBusy] = useState<string | null>(null);
    const [showArchived, setShowArchived] = useState(false);
    const [when, setWhen] = useState<"upcoming" | "past" | "all">("upcoming");
    const visible = showArchived ? rows : rows.filter((exam) => !exam.archivedAt);
    const { upcoming, past } = splitSchoolByDate(visible, todayText());
    const shown = when === "upcoming" ? upcoming : when === "past" ? past : [...upcoming, ...past];

    async function run(exam: ExamPlan, action: "publish" | "cancel" | "archive" | "unarchive") {
        const question =
            action === "publish"
                ? "Publish this date sheet? The families can see it from now on and will be told."
                : action === "cancel"
                  ? "Cancel this exam? The families will be told. Any marks stay."
                  : action === "archive"
                    ? "Archive this date sheet? It is hidden from the list; nothing is deleted."
                    : null;
        if (question && !window.confirm(question)) return;
        setBusy(exam.id);
        try {
            if (action === "publish") await publishDateSheet(exam.id);
            else if (action === "cancel") await cancelSchoolExam(exam.id);
            else await archiveSchoolExam(exam.id, action === "archive");
            await queryClient.invalidateQueries({ queryKey: EXAM_LIST_KEY });
            toast.push(
                "success",
                action === "publish"
                    ? "Date sheet published — the families have been told."
                    : action === "cancel"
                      ? "Exam cancelled."
                      : action === "archive"
                        ? "Date sheet archived."
                        : "Date sheet restored.",
            );
        } catch (cause) {
            toast.push("error", errorMessage(cause, "Could not do that"));
        } finally {
            setBusy(null);
        }
    }

    return (
        <div className="space-y-3">
            <div className="flex flex-wrap items-end justify-between gap-3">
                <div className="w-44">
                    <Select
                        label="Show"
                        value={when}
                        onChange={(event) => setWhen(event.target.value as typeof when)}
                    >
                        <option value="upcoming">Upcoming</option>
                        <option value="past">Past</option>
                        <option value="all">All</option>
                    </Select>
                </div>
                {rows.some((exam) => exam.archivedAt) && (
                    <Button
                        size="sm"
                        variant="outline"
                        onClick={() => setShowArchived((current) => !current)}
                    >
                        {showArchived ? "Hide archived" : "Show archived"}
                    </Button>
                )}
            </div>
            <Table
                columns={[
                    {
                        key: "name",
                        header: "Exam",
                        render: (exam: ExamPlan) => (
                            <p className="truncate font-medium">
                                {isSchoolExamType(exam.examType) && exam.examType !== "custom"
                                    ? typeLabel(exam.examType)
                                    : titleCase(exam.name)}
                            </p>
                        ),
                    },
                    {
                        key: "dates",
                        header: "Date sheet",
                        render: (exam: ExamPlan) => {
                            if (!isSchoolExamType(exam.examType)) {
                                return (
                                    <span className="text-sm">
                                        {dateRangeText(exam.startDate, exam.endDate)}
                                    </span>
                                );
                            }
                            const dates = exam.papers
                                .map((paper) => paper.examDate)
                                .filter((date): date is string => Boolean(date))
                                .sort();
                            return (
                                <span className="text-sm">
                                    {exam.papers.length}{" "}
                                    {exam.papers.length === 1 ? "subject" : "subjects"}
                                    {dates.length > 0
                                        ? ` · ${dateRangeText(dates[0], dates[dates.length - 1])}`
                                        : ""}
                                </span>
                            );
                        },
                    },
                    {
                        key: "status",
                        header: "Status",
                        render: (exam: ExamPlan) => {
                            const chip = exam.archivedAt
                                ? { label: "Archived", tone: "muted" as const }
                                : isSchoolExamType(exam.examType)
                                  ? schoolExamChip(exam)
                                  : examStatusChip(exam.status);
                            return <Badge tone={chip.tone}>{chip.label}</Badge>;
                        },
                    },
                    {
                        key: "actions",
                        header: "",
                        align: "right",
                        render: (exam: ExamPlan) => {
                            const fresh = isSchoolExamType(exam.examType);
                            const cancelled = exam.status === "cancelled";
                            const published = Boolean(exam.datesheetPublishedAt);
                            const mine = fresh && exam.canManage;
                            if (exam.archivedAt) {
                                return mine ? (
                                    <div className="flex justify-end">
                                        <Button
                                            size="sm"
                                            variant="ghost"
                                            disabled={busy === exam.id}
                                            onClick={() => run(exam, "unarchive")}
                                        >
                                            Unarchive
                                        </Button>
                                    </div>
                                ) : null;
                            }
                            // A called-off exam needs nothing more - it can only be archived.
                            if (cancelled) {
                                return mine ? (
                                    <div className="flex justify-end">
                                        <Button
                                            size="sm"
                                            variant="ghost"
                                            disabled={busy === exam.id}
                                            onClick={() => run(exam, "archive")}
                                        >
                                            Archive
                                        </Button>
                                    </div>
                                ) : null;
                            }
                            return (
                                <div className="flex flex-wrap justify-end gap-2">
                                    <Button
                                        size="sm"
                                        variant="ghost"
                                        onClick={() => onOpen({ kind: "exam", examId: exam.id })}
                                    >
                                        Open
                                    </Button>
                                    {mine && (
                                        <Button
                                            size="sm"
                                            variant="outline"
                                            disabled={busy === exam.id}
                                            onClick={() => onEdit({ exam })}
                                        >
                                            Date Sheet
                                        </Button>
                                    )}
                                    {mine && !published && (
                                        <Button
                                            size="sm"
                                            variant="primary"
                                            disabled={busy === exam.id}
                                            onClick={() => run(exam, "publish")}
                                        >
                                            Publish
                                        </Button>
                                    )}
                                    {mine && (
                                        <Button
                                            size="sm"
                                            variant="ghost"
                                            disabled={busy === exam.id}
                                            onClick={() =>
                                                run(exam, published ? "cancel" : "archive")
                                            }
                                        >
                                            {published ? "Cancel" : "Archive"}
                                        </Button>
                                    )}
                                    {!fresh && (
                                        <Button
                                            size="sm"
                                            variant="outline"
                                            onClick={() =>
                                                onOpen({ kind: "results", examId: exam.id })
                                            }
                                        >
                                            Results
                                        </Button>
                                    )}
                                </div>
                            );
                        },
                    },
                ]}
                rows={shown}
                rowKey={(exam) => exam.id}
                empty={
                    when === "upcoming"
                        ? "No upcoming exam."
                        : when === "past"
                          ? "No past exam."
                          : "No date sheet has been set here yet."
                }
            />
        </div>
    );
}

/**
 * The class tests of this section in one table with a **Show** dropdown: Upcoming (the date
 * has not passed, nearest first), Past (the date has gone by, latest first) or All (upcoming
 * first, then past).
 *
 * A test is cancelled - never deleted - and only then archived (hidden behind Show archived),
 * like a school exam. Marks and Edit are on every live row, upcoming or past.
 */
function ClassTestTable({
    rows,
    classroomId,
    onOpen,
    onEdit,
}: {
    rows: ExamPlan[];
    classroomId: string;
    onOpen: (view: View) => void;
    onEdit: (exam: ExamPlan) => void;
}) {
    const queryClient = useQueryClient();
    const toast = useToast();
    const [busy, setBusy] = useState<string | null>(null);
    const [reading, setReading] = useState<{ id: string; subject: string } | null>(null);
    const [hideCancelled, setHideCancelled] = useState(false);
    const [when, setWhen] = useState<"upcoming" | "past" | "all">("upcoming");
    const [showArchived, setShowArchived] = useState(false);

    const live = showArchived ? rows : rows.filter((exam) => !exam.archivedAt);
    const shown = hideCancelled ? live.filter((exam) => exam.status !== "cancelled") : live;
    const { upcoming, past } = splitByDate(shown, classroomId, todayText());

    async function cancel(exam: ExamPlan) {
        if (!window.confirm("Cancel this class test? The families will be told. Any marks stay."))
            return;
        setBusy(exam.id);
        try {
            await cancelClassTest(exam.id);
            await queryClient.invalidateQueries({ queryKey: EXAM_LIST_KEY });
            toast.push("success", "Class test cancelled.");
        } catch (cause) {
            toast.push("error", errorMessage(cause, "Could not cancel the class test"));
        } finally {
            setBusy(null);
        }
    }

    async function archive(exam: ExamPlan, archived: boolean) {
        setBusy(exam.id);
        try {
            await archiveClassTest(exam.id, archived);
            await queryClient.invalidateQueries({ queryKey: EXAM_LIST_KEY });
            toast.push("success", archived ? "Class test archived." : "Class test restored.");
        } catch (cause) {
            toast.push("error", errorMessage(cause, "Could not do that"));
        } finally {
            setBusy(null);
        }
    }

    function columns() {
        return [
            {
                key: "subject",
                header: "Subject",
                render: (exam: ExamPlan) => {
                    const paper = paperOfSection(exam, classroomId);
                    return (
                        <div className="min-w-0">
                            <p className="truncate font-medium">
                                {titleCase(paper?.subject ?? exam.name)}
                            </p>
                            <p className="text-muted-foreground truncate text-xs">
                                {sectionsText(exam) || "—"}
                            </p>
                        </div>
                    );
                },
            },
            {
                key: "date",
                header: "Exam Date",
                render: (exam: ExamPlan) => (
                    <span className="text-sm">
                        {dayText(paperOfSection(exam, classroomId)?.examDate)}
                    </span>
                ),
            },
            {
                key: "total",
                header: "Total Marks",
                render: (exam: ExamPlan) => (
                    <span className="text-sm tabular-nums">
                        {figureText(paperOfSection(exam, classroomId)?.maxMarks)}
                    </span>
                ),
            },
            {
                key: "taker",
                header: "Taken By",
                render: (exam: ExamPlan) => {
                    const first = paperOfSection(exam, classroomId);
                    if (!first?.takenByName)
                        return <span className="text-muted-foreground">—</span>;
                    return (
                        <span className="flex items-center gap-1.5 text-sm">
                            <i
                                className={`tt-badge tt-badge-static ${
                                    first.isTemporary ? "tt-badge-t" : "tt-badge-s"
                                }`}
                                title={first.isTemporary ? "Temporary teacher" : "Assigned teacher"}
                            >
                                {first.isTemporary ? "T" : "S"}
                            </i>
                            {first.takenByName}
                        </span>
                    );
                },
            },
            {
                key: "syllabus",
                header: "Syllabus",
                render: (exam: ExamPlan) => {
                    const paper = paperOfSection(exam, classroomId);
                    if (exam.status === "cancelled") return null;
                    return (
                        <Button
                            size="sm"
                            variant="outline"
                            disabled={!paper?.hasSyllabus}
                            title={
                                paper?.hasSyllabus ? "Read the syllabus" : "Syllabus not added yet"
                            }
                            onClick={() =>
                                paper && setReading({ id: paper.id, subject: paper.subject })
                            }
                        >
                            View
                        </Button>
                    );
                },
            },
            {
                key: "status",
                header: "Status",
                render: (exam: ExamPlan) => {
                    const chip = exam.archivedAt
                        ? { label: "Archived", tone: "muted" as const }
                        : classTestChip(exam);
                    return <Badge tone={chip.tone}>{chip.label}</Badge>;
                },
            },
            {
                key: "actions",
                header: "",
                align: "right" as const,
                render: (exam: ExamPlan) => {
                    const mine = exam.papers.some((paper) => paper.canEdit);
                    // Archived: only Unarchive. Cancelled: nothing but Archive (like a
                    // school exam - cancel first, then archive).
                    if (exam.archivedAt || exam.status === "cancelled") {
                        return mine ? (
                            <div className="flex justify-end">
                                <Button
                                    size="sm"
                                    variant="ghost"
                                    disabled={busy === exam.id}
                                    onClick={() => archive(exam, !exam.archivedAt)}
                                >
                                    {exam.archivedAt ? "Unarchive" : "Archive"}
                                </Button>
                            </div>
                        ) : null;
                    }
                    const paper = paperOfSection(exam, classroomId);
                    return (
                        <div className="flex flex-wrap justify-end gap-2">
                            {paper && (
                                <Button
                                    size="sm"
                                    variant="outline"
                                    onClick={() =>
                                        onOpen({
                                            kind: "marks",
                                            examId: exam.id,
                                            paperId: paper.id,
                                            from: "list",
                                        })
                                    }
                                >
                                    Marks
                                </Button>
                            )}
                            {mine && (
                                <Button
                                    size="sm"
                                    variant="outline"
                                    disabled={busy === exam.id}
                                    onClick={() => onEdit(exam)}
                                >
                                    Edit
                                </Button>
                            )}
                            {mine && (
                                <Button
                                    size="sm"
                                    variant="ghost"
                                    disabled={busy === exam.id}
                                    onClick={() => cancel(exam)}
                                >
                                    Cancel
                                </Button>
                            )}
                        </div>
                    );
                },
            },
        ];
    }

    const listed = when === "upcoming" ? upcoming : when === "past" ? past : [...upcoming, ...past];

    return (
        <div className="space-y-4">
            <div className="flex flex-wrap items-end justify-between gap-3">
                <div className="w-44">
                    <Select
                        label="Show"
                        value={when}
                        onChange={(event) => setWhen(event.target.value as typeof when)}
                    >
                        <option value="upcoming">Upcoming</option>
                        <option value="past">Past</option>
                        <option value="all">All</option>
                    </Select>
                </div>
                <div className="flex flex-wrap items-center gap-3">
                    {rows.some((exam) => exam.status === "cancelled") && (
                        <label className="text-muted-foreground flex w-fit items-center gap-2 text-xs">
                            <input
                                type="checkbox"
                                className="size-4"
                                checked={hideCancelled}
                                onChange={(event) => setHideCancelled(event.target.checked)}
                            />
                            Hide cancelled tests
                        </label>
                    )}
                    {rows.some((exam) => exam.archivedAt) && (
                        <Button
                            size="sm"
                            variant="outline"
                            onClick={() => setShowArchived((current) => !current)}
                        >
                            {showArchived ? "Hide archived" : "Show archived"}
                        </Button>
                    )}
                </div>
            </div>

            <Table
                columns={columns()}
                rows={listed}
                rowKey={(exam) => exam.id}
                empty={
                    when === "upcoming"
                        ? "No upcoming class test."
                        : when === "past"
                          ? "No past class test."
                          : "No class test has been scheduled here yet."
                }
            />

            <SyllabusDialog
                paperId={reading?.id ?? null}
                subject={reading?.subject ?? ""}
                editable={false}
                onClose={() => setReading(null)}
            />
        </div>
    );
}
