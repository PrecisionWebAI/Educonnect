"use client";

import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Badge, Button, Card, Spinner, Table } from "@/components/ui";
import { useToast } from "@/components/ui/toast";
import { errorMessage } from "@/lib/api/client";
import { getSectionCourse, tickChapter } from "@/services";
import { useApiQuery } from "@/lib/api/use-api-query";
import {
    chaptersLabel,
    nextStatus,
    scheduleBadge,
    teacherTrail,
    tickGate,
} from "@/lib/course/view";
import type { CourseChapter, CourseSubject, SectionCourse } from "@/types";

import CourseBar from "./CourseBar";
import { chapterColumns } from "./chapter-columns";

// The **Course** tab of a class-section (Phase 6).
//
// One read (`GET /classroom/sections/{id}/course`) draws the whole tab: each subject
// with its teacher trail, the segmented bar (one colour per person who finished
// chapters + the grey remainder), the ahead/behind badge and the chapter table.
//
// The tick button appears only where the server said `canTick` (this teacher holds the
// subject now, or the caller has the office's `classes.update`). A refusal keeps the
// button disabled with the reason in its tooltip, and the server refuses again if
// anyone calls it anyway - the button is a courtesy, the permission is the rule.

export default function CoursePanel({ sectionId }: { sectionId: string }) {
    const queryClient = useQueryClient();
    const toast = useToast();
    const course = useApiQuery(["course", "section", sectionId], () => getSectionCourse(sectionId));
    const [busyChapter, setBusyChapter] = useState<string | null>(null);
    const [open, setOpen] = useState<Record<string, boolean>>({});

    const data: SectionCourse | undefined = course.data;

    async function handleTick(subject: CourseSubject, chapter: CourseChapter) {
        const gate = tickGate(chapter);
        if (!gate.allowed) {
            toast.push("error", gate.reason);
            return;
        }
        const target = nextStatus(chapter);
        setBusyChapter(chapter.chapterId);
        try {
            await tickChapter(chapter.chapterId, sectionId, target);
            await queryClient.invalidateQueries({
                queryKey: ["course", "section", sectionId],
            });
            // The Classroom card prints the same completion number, so it re-reads too.
            await queryClient.invalidateQueries({ queryKey: ["classroom"] });
            toast.push(
                "success",
                `${subject.subject} · ${chapter.name}: ${
                    target === "Completed" ? "marked done" : "re-opened"
                }`,
            );
        } catch (cause) {
            toast.push("error", errorMessage(cause, "Could not update the chapter"));
        } finally {
            setBusyChapter(null);
        }
    }

    if (course.isPending) return <Spinner />;

    const subjects = data?.subjects ?? [];
    if (subjects.length === 0) {
        return (
            <Card title="Course">
                <p style={{ color: "var(--muted)", fontSize: "0.9rem" }}>
                    No subject is assigned to this class-section yet. Once a subject teacher is
                    assigned, the plan and its bar appear here.
                </p>
            </Card>
        );
    }

    return (
        <div className="space-y-4">
            <div className="toolbar">
                <span className="text-muted-foreground text-sm">
                    {data?.label} · {subjects.length}{" "}
                    {subjects.length === 1 ? "subject" : "subjects"}
                    {data?.academicYear ? ` · session ${data.academicYear}` : ""}
                </span>
            </div>

            {subjects.map((subject) => {
                const badge = scheduleBadge(subject);
                const isOpen = open[subject.subjectId] ?? false;
                return (
                    <Card
                        key={subject.subjectId}
                        title={subject.subject}
                        action={<Badge tone={badge.tone}>{badge.label}</Badge>}
                    >
                        <div className="flex flex-col gap-3">
                            <div className="flex flex-wrap items-center justify-between gap-2">
                                <span className="text-sm">
                                    <b>{subject.currentTeacher ?? "No teacher assigned"}</b>
                                    <span
                                        style={{
                                            color: "var(--muted)",
                                            fontSize: "0.78rem",
                                            display: "block",
                                        }}
                                    >
                                        {teacherTrail(subject)}
                                    </span>
                                    {subject.teachers.length > 1 && (
                                        <ul style={{ marginTop: "0.25rem" }}>
                                            {subject.teachers.map((teacher) => (
                                                <li
                                                    key={teacher.employeeId}
                                                    style={{
                                                        color: "var(--muted)",
                                                        fontSize: "0.76rem",
                                                    }}
                                                >
                                                    {teacher.name} · {teacher.effectiveFrom ?? "—"}{" "}
                                                    → {teacher.effectiveTo ?? "now"} ·{" "}
                                                    {teacher.completed}/{subject.total}
                                                </li>
                                            ))}
                                        </ul>
                                    )}
                                </span>
                                <span className="flex items-center gap-2">
                                    <span className="text-sm font-semibold">
                                        {subject.percent === null
                                            ? "No plan"
                                            : `${subject.percent}%`}
                                    </span>
                                    <span style={{ color: "var(--muted)", fontSize: "0.78rem" }}>
                                        {chaptersLabel(subject.done, subject.total)}
                                    </span>
                                    <Button
                                        size="sm"
                                        variant="ghost"
                                        onClick={() =>
                                            setOpen((prev) => ({
                                                ...prev,
                                                [subject.subjectId]: !isOpen,
                                            }))
                                        }
                                    >
                                        {isOpen ? "Hide chapters" : "Chapters"}
                                    </Button>
                                </span>
                            </div>

                            <CourseBar subject={subject} />

                            {subject.nextChapter && (
                                <p style={{ color: "var(--muted)", fontSize: "0.8rem" }}>
                                    On now: {subject.nextChapter}
                                </p>
                            )}

                            {isOpen && (
                                <Table
                                    columns={chapterColumns(subject, handleTick, busyChapter)}
                                    rows={subject.chapters}
                                    rowKey={(row) => row.chapterId}
                                    empty="No chapters planned for this subject yet."
                                />
                            )}
                        </div>
                    </Card>
                );
            })}
        </div>
    );
}
