"use client";

import { Badge, Button } from "@/components/ui";
import { tickGate, tickLabel, type ChapterMove } from "@/lib/course/view";
import type { CourseChapter, CourseSubject } from "@/types";

/**
 * The chapter table's columns.
 *
 * Kept beside the panel rather than inside it so the tick button's rule - "disabled
 * unless the server said `canTick`, with the reason in the tooltip" - is one small
 * piece of code a reader can find, and the panel stays a layout.
 */
export function chapterColumns(
    subject: CourseSubject,
    onTick: (subject: CourseSubject, chapter: CourseChapter) => void,
    busyChapter: string | null,
    onEdit: (subject: CourseSubject, chapter: CourseChapter) => void,
    onDelete: (chapter: CourseChapter) => void,
    onMove: (subject: CourseSubject, chapter: CourseChapter, direction: ChapterMove) => void,
) {
    const ordered = [...subject.chapters].sort((left, right) => left.sequence - right.sequence);
    return [
        { key: "sequence", header: "#" },
        {
            key: "name",
            header: "Chapter",
            render: (row: CourseChapter) => <b>{row.name}</b>,
        },
        {
            key: "plannedDate",
            header: "Planned",
            render: (row: CourseChapter) => row.plannedDate ?? "—",
        },
        {
            key: "status",
            header: "Status",
            render: (row: CourseChapter) => (
                <Badge
                    tone={
                        row.status === "Completed"
                            ? "green"
                            : row.behind
                              ? "red"
                              : row.status === "In progress"
                                ? "amber"
                                : "muted"
                    }
                >
                    {row.status}
                </Badge>
            ),
        },
        {
            key: "completedOn",
            header: "Done on",
            render: (row: CourseChapter) => row.completedOn ?? "—",
        },
        {
            key: "completedBy",
            header: "By",
            render: (row: CourseChapter) => row.completedBy ?? "—",
        },
        {
            key: "tick",
            header: "",
            render: (row: CourseChapter) => {
                const gate = tickGate(row);
                return (
                    <Button
                        size="sm"
                        variant={row.status === "Completed" ? "ghost" : "success"}
                        disabled={!gate.allowed || busyChapter === row.chapterId}
                        title={gate.reason ?? undefined}
                        onClick={() => onTick(subject, row)}
                    >
                        {busyChapter === row.chapterId ? "Saving…" : tickLabel(row)}
                    </Button>
                );
            },
        },
        {
            key: "planActions",
            header: "",
            render: (row: CourseChapter) => {
                if (!row.canEdit) return null;
                const index = ordered.findIndex((chapter) => chapter.chapterId === row.chapterId);
                return (
                    <div className="flex items-center justify-end gap-1">
                        <Button
                            size="sm"
                            variant="ghost"
                            title="Move up"
                            disabled={index <= 0 || busyChapter === row.chapterId}
                            onClick={() => onMove(subject, row, "up")}
                        >
                            ↑
                        </Button>
                        <Button
                            size="sm"
                            variant="ghost"
                            title="Move down"
                            disabled={
                                index < 0 ||
                                index === ordered.length - 1 ||
                                busyChapter === row.chapterId
                            }
                            onClick={() => onMove(subject, row, "down")}
                        >
                            ↓
                        </Button>
                        <Button
                            size="sm"
                            variant="ghost"
                            disabled={busyChapter === row.chapterId}
                            onClick={() => onEdit(subject, row)}
                        >
                            Edit
                        </Button>
                        <Button
                            size="sm"
                            variant="danger"
                            disabled={busyChapter === row.chapterId}
                            onClick={() => onDelete(row)}
                        >
                            Delete
                        </Button>
                    </div>
                );
            },
        },
    ];
}
