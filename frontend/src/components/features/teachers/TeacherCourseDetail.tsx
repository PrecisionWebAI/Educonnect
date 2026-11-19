"use client";

import { useState } from "react";
import { Badge, Button, Card, Spinner } from "@/components/ui";
import { errorMessage } from "@/lib/api/client";
import { useApiQuery } from "@/lib/api/use-api-query";
import { getMyCourse, getTeacherCourse } from "@/services";
import type {
    CourseSubject,
    TeacherAssignment,
    TeacherChapterRow,
    TeacherWeekRow,
} from "@/types";

import WeeklyLessonPlanDialog from "@/components/features/classroom/course/WeeklyLessonPlanDialog";

/** The month rows a teacher detail shows: status is the whole story here. */
function weekTone(status: TeacherWeekRow["status"]): "green" | "amber" | "red" | "muted" {
    if (status === "Approved") return "green";
    if (status === "Submitted") return "amber";
    if (status === "Rejected") return "red";
    return "muted";
}

function chapterTone(status: TeacherChapterRow["status"]): "green" | "amber" | "muted" {
    if (status === "Completed") return "green";
    if (status === "In progress") return "amber";
    return "muted";
}

/**
 * The subject shape `WeeklyLessonPlanDialog` needs.
 *
 * The detail already has the section subject id and the numbers; the dialog only reads
 * `classroomSubjectId`/`subject` and then asks the plan endpoint for the truth.
 */
function planSubject(
    assignment: TeacherAssignment,
    teacherName: string,
    teacherId: string,
): CourseSubject {
    return {
        classroomSubjectId: assignment.classroomSubjectId,
        subjectId: assignment.subjectId,
        subject: assignment.subject,
        status: "Active",
        currentTeacher: teacherName,
        currentTeacherId: teacherId,
        teachers: [],
        done: assignment.done,
        total: assignment.total,
        percent: assignment.percent,
        nextChapter: null,
        behind: 0,
        planned: assignment.chapters.some((chapter) => chapter.plannedDate !== null),
        chapters: [],
        lessonPlan: null,
        canManage: false,
        canAssignTeacher: false,
        canArchive: false,
        canRestore: false,
        canDelete: false,
    };
}

/**
 * One teacher's course - current subjects first, then history.
 *
 * The same component serves the office (`/course/teachers/{id}`) and a teacher's own
 * record (`/course/my`), so "my course" cannot drift from what the principal sees.
 * Opening a subject's plan reuses the Classroom popup, including its approve/reject
 * controls for a reviewer.
 */
export default function TeacherCourseDetail({
    employeeId,
    mode = "teacher",
    onBack,
}: {
    employeeId?: string;
    mode?: "teacher" | "my";
    onBack?: () => void;
}) {
    const [plan, setPlan] = useState<CourseSubject | null>(null);
    const query = useApiQuery(
        ["course", "teacher", mode === "my" ? "my" : employeeId],
        () => (mode === "my" ? getMyCourse() : getTeacherCourse(employeeId as string)),
        { enabled: mode === "my" || Boolean(employeeId) },
    );

    if (query.isPending) return <Spinner />;
    if (query.error) {
        return (
            <p className="text-sm text-red-500">
                {errorMessage(query.error, "The teacher's course could not be loaded.")}
            </p>
        );
    }
    if (!query.data) return null;

    const detail = query.data;
    const current = detail.assignments.filter((assignment) => assignment.current);
    const past = detail.assignments.filter((assignment) => !assignment.current);

    return (
        <div className="space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                    {onBack && (
                        <Button size="sm" variant="ghost" onClick={onBack}>
                            ← Back
                        </Button>
                    )}
                    <div>
                        <h2 className="text-lg font-semibold">{detail.name}</h2>
                        <p className="text-muted-foreground text-xs">
                            {detail.employeeCode ?? "—"}
                            {detail.department ? ` · ${detail.department}` : ""}
                        </p>
                    </div>
                </div>
                <Badge tone="teal">
                    {current.length} current subject{current.length === 1 ? "" : "s"}
                </Badge>
            </div>

            {current.length === 0 ? (
                <Card>
                    <p className="text-muted-foreground text-sm">
                        This teacher has no current subject assignment.
                    </p>
                </Card>
            ) : (
                current.map((assignment) => (
                    <Card
                        key={`${assignment.sectionId}-${assignment.subjectId}`}
                        title={`${assignment.subject} · ${assignment.label}`}
                    >
                        <div className="space-y-3">
                            <div className="flex flex-wrap items-center justify-between gap-2">
                                <span className="text-muted-foreground text-xs">
                                    {assignment.effectiveFrom
                                        ? `Since ${assignment.effectiveFrom}`
                                        : "Current"}
                                </span>
                                <div className="flex items-center gap-2">
                                    <span className="text-sm font-medium">
                                        {assignment.done}/{assignment.total}
                                        {assignment.percent !== null
                                            ? ` · ${assignment.percent}%`
                                            : " · no plan"}
                                    </span>
                                    {assignment.classroomSubjectId && (
                                        <Button
                                            size="sm"
                                            variant="outline"
                                            onClick={() =>
                                                setPlan(
                                                    planSubject(
                                                        assignment,
                                                        detail.name,
                                                        detail.employeeId,
                                                    ),
                                                )
                                            }
                                        >
                                            Lesson plan
                                        </Button>
                                    )}
                                </div>
                            </div>

                            <div className="bg-muted h-2 w-full overflow-hidden rounded-full">
                                <div
                                    className="bg-primary h-full rounded-full"
                                    style={{
                                        width: `${Math.max(
                                            0,
                                            Math.min(100, assignment.percent ?? 0),
                                        )}%`,
                                    }}
                                />
                            </div>

                            <div className="flex flex-wrap gap-1">
                                {assignment.weeks.map((week) => (
                                    <Badge key={week.weekNo} tone={weekTone(week.status)}>
                                        W{week.weekNo} {week.status ?? "Not submitted"}
                                    </Badge>
                                ))}
                            </div>

                            {assignment.chapters.length > 0 && (
                                <div className="overflow-x-auto">
                                    <table className="w-full text-left text-sm">
                                        <thead className="text-muted-foreground">
                                            <tr>
                                                <th className="py-1 pr-2">#</th>
                                                <th className="py-1 pr-2">Chapter</th>
                                                <th className="py-1 pr-2">Planned</th>
                                                <th className="py-1 pr-2">Status</th>
                                                <th className="py-1">Done by</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {assignment.chapters.map((chapter) => (
                                                <tr
                                                    key={chapter.chapterId}
                                                    className="border-t"
                                                >
                                                    <td className="py-1 pr-2">
                                                        {chapter.sequence}
                                                    </td>
                                                    <td className="py-1 pr-2">
                                                        {chapter.name}
                                                    </td>
                                                    <td className="py-1 pr-2">
                                                        {chapter.plannedDate ?? "—"}
                                                    </td>
                                                    <td className="py-1 pr-2">
                                                        <Badge
                                                            tone={chapterTone(
                                                                chapter.status,
                                                            )}
                                                        >
                                                            {chapter.status}
                                                        </Badge>
                                                    </td>
                                                    <td className="py-1">
                                                        {chapter.completedBy ?? "—"}
                                                        {chapter.completedOn
                                                            ? ` · ${chapter.completedOn}`
                                                            : ""}
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            )}
                        </div>
                    </Card>
                ))
            )}

            {past.length > 0 && (
                <Card title="Past subjects">
                    <div className="space-y-2">
                        {past.map((assignment) => (
                            <div
                                key={`${assignment.sectionId}-${assignment.subjectId}-${assignment.effectiveTo ?? "past"}`}
                                className="flex flex-wrap items-center justify-between gap-2 border-b pb-2 last:border-b-0"
                            >
                                <span>
                                    <b>{assignment.subject}</b> · {assignment.label}
                                </span>
                                <span className="text-muted-foreground text-xs">
                                    {assignment.effectiveFrom ?? "—"} →{" "}
                                    {assignment.effectiveTo ?? "—"}
                                </span>
                            </div>
                        ))}
                    </div>
                </Card>
            )}

            <WeeklyLessonPlanDialog
                subject={plan}
                open={plan !== null}
                onOpenChange={(open) => {
                    if (!open) setPlan(null);
                }}
            />
        </div>
    );
}