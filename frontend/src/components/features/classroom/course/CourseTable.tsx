"use client";

import { Badge, Button, Table, type Column } from "@/components/ui";
import {
    lessonPlanLabel,
    progressText,
    progressWidth,
    statusBadge,
    teacherName,
} from "@/lib/course/view";
import type { CourseSubject } from "@/types";

/**
 * The section's Course table - the rows the plan is built on.
 *
 * Columns follow the business rule: Subject, Teacher, Lesson Plan, Total, Completed and
 * a **long** progress bar. The actions are drawn only when the server said the caller may
 * use them (`canArchive` / `canRestore` / `canDelete`) - and the API checks again, because
 * a hidden button is a courtesy, never the rule.
 *
 * The Lesson Plan cell says "No plan" today; the weekly plan popup arrives in its own
 * phase, and this cell is where its status summary will live.
 */

export default function CourseTable({
    rows,
    onChapters,
    onLessonPlan,
    onAssign,
    onHistory,
    onArchive,
    onRestore,
    onDelete,
    busyId,
}: {
    rows: CourseSubject[];
    onChapters: (subject: CourseSubject) => void;
    onLessonPlan: (subject: CourseSubject) => void;
    onAssign: (subject: CourseSubject) => void;
    onHistory: (subject: CourseSubject) => void;
    onArchive: (subject: CourseSubject) => void;
    onRestore: (subject: CourseSubject) => void;
    onDelete: (subject: CourseSubject) => void;
    busyId?: string | null;
}) {
    const columns: Column<CourseSubject>[] = [
        {
            key: "subject",
            header: "Subject",
            render: (row) => {
                const state = statusBadge(row);
                return (
                    <div className="flex flex-col gap-1">
                        <span className="flex items-center gap-2 font-semibold">
                            {row.subject}
                            {row.status === "Archived" && (
                                <Badge tone={state.tone}>{state.label}</Badge>
                            )}
                        </span>
                        {row.nextChapter && (
                            <span style={{ color: "var(--muted)", fontSize: "0.76rem" }}>
                                On now: {row.nextChapter}
                            </span>
                        )}
                    </div>
                );
            },
        },
        {
            key: "teacher",
            header: "Teacher",
            render: (row) => (
                <div className="flex flex-col gap-1">
                    <span style={{ color: row.currentTeacher ? undefined : "var(--muted)" }}>
                        {teacherName(row)}
                    </span>
                    {row.teachers.length > 1 && (
                        <Button
                            size="sm"
                            variant="ghost"
                            className="h-auto justify-start px-0 text-xs"
                            onClick={() => onHistory(row)}
                        >
                            {row.teachers.length} assignments · history
                        </Button>
                    )}
                </div>
            ),
        },
        {
            key: "lessonPlan",
            header: "Lesson Plan",
            render: (row) => {
                const plan = row.lessonPlan;
                const tone = !plan || plan.submitted === 0
                    ? "muted"
                    : plan.rejected > 0
                      ? "red"
                      : plan.approved === plan.submitted
                        ? "green"
                        : "amber";
                const badge = <Badge tone={tone}>{lessonPlanLabel(row)}</Badge>;
                if (!row.classroomSubjectId) return badge;
                return (
                    <Button
                        size="sm"
                        variant="ghost"
                        className="h-auto px-0"
                        title="Open the weekly lesson plan"
                        onClick={() => onLessonPlan(row)}
                    >
                        {badge}
                    </Button>
                );
            },
        },
        {
            key: "total",
            header: "Total Chapters",
            align: "right",
            render: (row) => (row.total === 0 ? "—" : row.total),
        },
        {
            key: "done",
            header: "Completed",
            align: "right",
            render: (row) => row.done,
        },
        {
            key: "progress",
            header: "Progress",
            render: (row) => (
                <div className="flex min-w-[170px] items-center gap-2">
                    <div
                        className="bg-muted h-2 w-full overflow-hidden rounded-full"
                        role="img"
                        aria-label={`${row.done} of ${row.total} chapters done`}
                    >
                        <div
                            className="bg-primary h-full rounded-full transition-all"
                            style={{ width: progressWidth(row) }}
                        />
                    </div>
                    <span
                        className="shrink-0 text-xs font-medium"
                        style={{ color: "var(--muted)" }}
                    >
                        {progressText(row)}
                    </span>
                </div>
            ),
        },
        {
            key: "actions",
            header: "",
            align: "right",
            render: (row) => (
                <div className="flex items-center justify-end gap-1">
                    {row.canAssignTeacher && row.classroomSubjectId && (
                        <Button
                            size="sm"
                            variant="ghost"
                            disabled={busyId === row.classroomSubjectId}
                            onClick={() => onAssign(row)}
                        >
                            {row.currentTeacherId ? "Edit" : "Assign teacher"}
                        </Button>
                    )}
                    <Button
                        size="sm"
                        variant="ghost"
                        disabled={row.total === 0 && row.chapters.length === 0}
                        onClick={() => onChapters(row)}
                    >
                        Chapters
                    </Button>
                    {row.canArchive && (
                        <Button
                            size="sm"
                            variant="ghost"
                            disabled={busyId === row.classroomSubjectId}
                            onClick={() => onArchive(row)}
                        >
                            Archive
                        </Button>
                    )}
                    {row.canRestore && (
                        <Button
                            size="sm"
                            variant="ghost"
                            disabled={busyId === row.classroomSubjectId}
                            onClick={() => onRestore(row)}
                        >
                            Restore
                        </Button>
                    )}
                    {row.canDelete && (
                        <Button
                            size="sm"
                            variant="danger"
                            disabled={busyId === row.classroomSubjectId}
                            onClick={() => onDelete(row)}
                        >
                            Delete
                        </Button>
                    )}
                </div>
            ),
        },
    ];

    return (
        <Table
            columns={columns}
            rows={rows}
            rowKey={(row) => row.classroomSubjectId ?? row.subjectId}
            empty="No subjects added yet."
        />
    );
}
