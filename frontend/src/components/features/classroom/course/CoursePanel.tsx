"use client";

import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
    Button,
    Card,
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    Spinner,
} from "@/components/ui";
import { useToast } from "@/components/ui/toast";
import AcademicYearRequiredBanner from "@/components/layout/AcademicYearRequiredBanner";
import { usePermission } from "@/hooks/use-authorization";
import { ApiError, errorMessage } from "@/lib/api/client";
import { useApiQuery } from "@/lib/api/use-api-query";
import { titleCase } from "@/lib/format";
import { canWriteCourse } from "@/lib/course/view";
import { useAcademicYear } from "@/providers/academic-year-context";
import {
    archiveCourseSubject,
    deleteCourseSubject,
    getSectionCourse,
    restoreCourseSubject,
} from "@/services";
import type { CourseSubject, SectionCourse } from "@/types";

import AddSubjectDialog from "./AddSubjectDialog";
import ChapterPlanDialog from "./ChapterPlanDialog";
import ChapterProgressDialog from "./ChapterProgressDialog";
import CourseCompletionCard from "./CourseCompletionCard";
import CourseTable from "./CourseTable";
import LessonPlanReviewPanel from "./LessonPlanReviewPanel";
import RenameSubjectDialog from "./RenameSubjectDialog";
import TeacherAssignDialog from "./TeacherAssignDialog";
import TeacherHistoryDialog from "./TeacherHistoryDialog";
import WeeklyLessonPlanDialog from "./WeeklyLessonPlanDialog";

// The **Course** tab of a class-section.
//
// The table's rows are the section's own subjects (`classroomsubject`), so a subject
// exists here the moment it is added - before anybody is assigned to teach it. Each
// action is drawn only when the server said this caller may use it (`canArchive`,
// `canRestore`, `canDelete`); the API checks again, because a hidden button is a
// courtesy and the permission is the rule.
//
// The chapter table stays behind the row's "Chapters" button: the same tick contract the
// tab has always had, now opened from the summary instead of drawn under every subject.

export default function CoursePanel({ sectionId }: { sectionId: string }) {
    const queryClient = useQueryClient();
    const toast = useToast();
    const canManage = usePermission("course.manage");
    const canApprove = usePermission("course.approve");
    const { current: academicYear } = useAcademicYear();
    const academicYearReady = canWriteCourse(academicYear);

    const [showArchived, setShowArchived] = useState(false);
    const [reviewsOpen, setReviewsOpen] = useState(false);
    const [addOpen, setAddOpen] = useState(false);
    const [renameSubject, setRenameSubject] = useState<CourseSubject | null>(null);
    const [chapterSubject, setChapterSubject] = useState<CourseSubject | null>(null);
    const [progressSubject, setProgressSubject] = useState<CourseSubject | null>(null);
    const [lessonPlanSubject, setLessonPlanSubject] = useState<CourseSubject | null>(null);
    const [assignSubject, setAssignSubject] = useState<CourseSubject | null>(null);
    const [historySubject, setHistorySubject] = useState<CourseSubject | null>(null);
    const [deleteTarget, setDeleteTarget] = useState<CourseSubject | null>(null);
    const [busyId, setBusyId] = useState<string | null>(null);

    const course = useApiQuery(["course", "section", sectionId, showArchived], () =>
        getSectionCourse(sectionId, showArchived),
    );
    const data: SectionCourse | undefined = course.data;
    const subjects = data?.subjects ?? [];

    // The dialog follows the fresh row after an archive/restore, not the copy it opened
    // with - otherwise its buttons would still describe the old state.
    const selectedChapterSubject = chapterSubject
        ? (subjects.find((row) => row.classroomSubjectId === chapterSubject.classroomSubjectId) ??
          chapterSubject)
        : null;

    const selectedProgressSubject = progressSubject
        ? (subjects.find((row) => row.classroomSubjectId === progressSubject.classroomSubjectId) ??
          progressSubject)
        : null;

    async function refresh() {
        await queryClient.invalidateQueries({ queryKey: ["course"] });
        // The Classroom card prints the same completion number, so it re-reads too.
        await queryClient.invalidateQueries({ queryKey: ["classroom"] });
    }

    /**
     * A `409` from the course service can mean "there is no academic year" (the
     * server's final guard). It gets the same plain sentence everywhere instead of
     * exposing the raw API text in a toast.
     */
    function courseError(cause: unknown, fallback: string): string {
        if (
            cause instanceof ApiError &&
            cause.status === 409 &&
            /academic (year|session)/i.test(cause.message)
        ) {
            return "No academic year is open. Open it from the top bar, then try again.";
        }
        return errorMessage(cause, fallback);
    }

    async function archive(subject: CourseSubject) {
        if (!subject.classroomSubjectId) return;
        setBusyId(subject.classroomSubjectId);
        try {
            await archiveCourseSubject(subject.classroomSubjectId);
            await refresh();
            toast.push("success", `${titleCase(subject.name)} archived`);
            setDeleteTarget(null);
        } catch (cause) {
            toast.push("error", courseError(cause, "Could not archive the subject."));
        } finally {
            setBusyId(null);
        }
    }

    async function restore(subject: CourseSubject) {
        if (!subject.classroomSubjectId) return;
        setBusyId(subject.classroomSubjectId);
        try {
            await restoreCourseSubject(subject.classroomSubjectId);
            await refresh();
            toast.push("success", `${titleCase(subject.name)} unarchived`);
        } catch (cause) {
            toast.push("error", courseError(cause, "Could not unarchive the subject."));
        } finally {
            setBusyId(null);
        }
    }

    async function remove(subject: CourseSubject) {
        if (!subject.classroomSubjectId) return;
        setBusyId(subject.classroomSubjectId);
        try {
            await deleteCourseSubject(subject.classroomSubjectId);
            await refresh();
            toast.push("success", `${titleCase(subject.name)} removed from this classroom`);
            setDeleteTarget(null);
        } catch (cause) {
            // A `409` is the server saying "archive it instead"; its message says why.
            toast.push("error", courseError(cause, "Could not delete the subject."));
        } finally {
            setBusyId(null);
        }
    }

    if (course.isPending) return <Spinner />;

    return (
        <div className="space-y-4">
            <CourseCompletionCard course={data} />

            <AcademicYearRequiredBanner />

            <div className="toolbar flex flex-wrap items-center justify-between gap-2">
                <span className="text-muted-foreground text-sm">
                    {academicYear
                        ? `Academic year ${academicYear.name}`
                        : "No academic year is open - add subjects after it is set."}
                </span>
                <div className="flex flex-wrap items-center gap-2">
                    {canApprove && (
                        <Button size="sm" variant="outline" onClick={() => setReviewsOpen(true)}>
                            Review plans
                        </Button>
                    )}
                    {canManage && (
                        <Button
                            size="sm"
                            disabled={!academicYearReady}
                            title={academicYearReady ? undefined : "Open an academic year first"}
                            onClick={() => setAddOpen(true)}
                        >
                            Add Subject
                        </Button>
                    )}
                    {canManage && (
                        <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => setShowArchived((value) => !value)}
                        >
                            {showArchived ? "Hide archived" : "Show archived"}
                        </Button>
                    )}
                </div>
            </div>

            {subjects.length === 0 ? (
                <Card title="Course">
                    <p style={{ color: "var(--muted)", fontSize: "0.9rem" }}>
                        {canManage
                            ? "No subjects added yet. Add the first subject to start the course plan."
                            : "No subjects have been added to this class-section yet."}
                    </p>
                </Card>
            ) : (
                <CourseTable
                    rows={subjects}
                    busyId={busyId}
                    onChapters={setChapterSubject}
                    onProgress={setProgressSubject}
                    onLessonPlan={setLessonPlanSubject}
                    onAssign={setAssignSubject}
                    onHistory={setHistorySubject}
                    onArchive={archive}
                    onRestore={restore}
                    onDelete={setDeleteTarget}
                    onRename={setRenameSubject}
                />
            )}

            <ChapterPlanDialog
                subject={selectedChapterSubject}
                open={selectedChapterSubject !== null}
                onOpenChange={(open) => {
                    if (!open) setChapterSubject(null);
                }}
            />

            <ChapterProgressDialog
                subject={selectedProgressSubject}
                open={selectedProgressSubject !== null}
                onOpenChange={(open) => {
                    if (!open) setProgressSubject(null);
                }}
            />

            <LessonPlanReviewPanel
                sectionId={sectionId}
                open={reviewsOpen}
                onOpenChange={setReviewsOpen}
            />

            <WeeklyLessonPlanDialog
                subject={lessonPlanSubject}
                open={lessonPlanSubject !== null}
                onOpenChange={(open) => {
                    if (!open) setLessonPlanSubject(null);
                }}
            />

            <Dialog
                open={deleteTarget !== null}
                onOpenChange={(open) => {
                    if (!open) setDeleteTarget(null);
                }}
            >
                <DialogContent className="sm:max-w-md">
                    <DialogHeader>
                        <DialogTitle>Delete subject</DialogTitle>
                    </DialogHeader>
                    <p className="text-muted-foreground text-sm">
                        Remove <b>{titleCase(deleteTarget?.name)}</b> from this class-section? A
                        subject with a lesson plan or a completed chapter cannot be deleted -
                        archive it instead so the history stays.
                    </p>
                    <div className="flex flex-wrap justify-end gap-2">
                        <Button
                            variant="outline"
                            onClick={() => setDeleteTarget(null)}
                            disabled={busyId !== null}
                        >
                            Cancel
                        </Button>
                        {deleteTarget?.canArchive && (
                            <Button
                                variant="outline"
                                onClick={() => deleteTarget && archive(deleteTarget)}
                                loading={busyId === deleteTarget?.classroomSubjectId}
                            >
                                Archive instead
                            </Button>
                        )}
                        <Button
                            variant="danger"
                            onClick={() => deleteTarget && remove(deleteTarget)}
                            loading={busyId === deleteTarget?.classroomSubjectId}
                        >
                            Delete
                        </Button>
                    </div>
                </DialogContent>
            </Dialog>

            <TeacherAssignDialog
                subject={assignSubject}
                open={assignSubject !== null}
                onOpenChange={(open) => {
                    if (!open) setAssignSubject(null);
                }}
            />
            <TeacherHistoryDialog
                subject={historySubject}
                open={historySubject !== null}
                onOpenChange={(open) => {
                    if (!open) setHistorySubject(null);
                }}
            />

            {addOpen && (
                <AddSubjectDialog sectionId={sectionId} open={addOpen} onOpenChange={setAddOpen} />
            )}
            {renameSubject && (
                <RenameSubjectDialog
                    key={renameSubject.classroomSubjectId ?? renameSubject.name}
                    subject={renameSubject}
                    open
                    onOpenChange={(open) => {
                        if (!open) setRenameSubject(null);
                    }}
                />
            )}
        </div>
    );
}
