"use client";

import { Badge, Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui";
import { historyLabel } from "@/lib/course/view";
import type { CourseSubject } from "@/types";

/**
 * Who held this subject, and what each of them finished.
 *
 * The rows come from `subjectteacher`, which the assign/change route writes as history:
 * an old teacher's row is closed, never overwritten. `completed` is **their** chapters,
 * read from `chapterprogress.completed_by_employee_id` - so a handover does not move the
 * old teacher's work to the new one.
 */
export default function TeacherHistoryDialog({
    subject,
    open,
    onOpenChange,
}: {
    subject: CourseSubject | null;
    open: boolean;
    onOpenChange: (open: boolean) => void;
}) {
    const timeline = subject?.teachers ?? [];

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-lg">
                <DialogHeader>
                    <DialogTitle>
                        Teacher history{subject ? ` · ${subject.subject}` : ""}
                    </DialogTitle>
                </DialogHeader>

                {timeline.length === 0 ? (
                    <p className="text-muted-foreground text-sm">
                        No teacher has held this subject yet.
                    </p>
                ) : (
                    <ol className="space-y-3">
                        {timeline.map((teacher) => (
                            <li
                                key={`${teacher.employeeId}-${teacher.effectiveFrom ?? "start"}`}
                                className="flex flex-wrap items-center justify-between gap-2 border-b pb-2 last:border-b-0"
                            >
                                <div className="flex flex-col">
                                    <span className="flex items-center gap-2 font-medium">
                                        {teacher.name}
                                        {teacher.current && <Badge tone="green">Current</Badge>}
                                    </span>
                                    <span className="text-muted-foreground text-xs">
                                        {historyLabel(teacher)}
                                    </span>
                                </div>
                                <span className="text-sm">
                                    {teacher.completed} chapter
                                    {teacher.completed === 1 ? "" : "s"} completed
                                </span>
                            </li>
                        ))}
                    </ol>
                )}
            </DialogContent>
        </Dialog>
    );
}
