"use client";

import { useCallback, useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { getMarks, getSectionMarks, saveSectionMarks } from "@/services";
import { useApiQuery } from "@/lib/api/use-api-query";
import type { MarksEntry } from "@/types";

// All academics/marks data logic in one hook.
//
// The same hook serves two hosts: the school-wide screen (no scope) and the
// Academics view **inside one class-section**, which passes `sectionId` so the
// marks come from that section's own endpoint - only the students of that class.

/**
 * The class-section whose marks these are.
 *
 * With a scope, Save writes back through `PUT /classroom/sections/{id}/marks`
 * (upsert per exam/student/subject). Without one there is nothing to write to.
 */
export interface AcademicsScope {
    sectionId?: string;
}

export function gradeFor(percent: number): {
    label: string;
    tone: "green" | "teal" | "amber" | "red" | "muted";
} {
    if (percent >= 90) return { label: "A+", tone: "green" };
    if (percent >= 75) return { label: "A", tone: "teal" };
    if (percent >= 60) return { label: "B", tone: "teal" };
    if (percent >= 40) return { label: "C", tone: "amber" };
    return { label: "F", tone: "red" };
}

export function totalsFor(entry: MarksEntry) {
    const max = entry.rows.reduce((sum, r) => sum + r.max, 0);
    const obtained = entry.rows.reduce((sum, r) => sum + r.obtained, 0);
    const percent = max > 0 ? Math.round((obtained / max) * 100) : 0;
    return { obtained, max, percent };
}

export function useAcademics(scope: AcademicsScope = {}) {
    const queryClient = useQueryClient();
    const marksQuery = useApiQuery(
        scope.sectionId ? ["classroom", "marks", scope.sectionId] : ["marks"],
        () => (scope.sectionId ? getSectionMarks(scope.sectionId) : getMarks()),
    );
    const entries = marksQuery.data ?? null;
    const [exam, setExam] = useState("all");
    const [className, setClassName] = useState("all");
    const [saving, setSaving] = useState(false);

    const exams = useMemo(() => Array.from(new Set((entries ?? []).map((e) => e.exam))), [entries]);

    const filtered = useMemo(
        () =>
            (entries ?? []).filter((e) => {
                if (exam !== "all" && e.exam !== exam) return false;
                if (className !== "all" && e.className !== className) return false;
                return true;
            }),
        [entries, exam, className],
    );

    /** Update a single subject score for a student (writes through to the query cache). */
    function updateScore(studentId: string, subject: string, obtained: number) {
        queryClient.setQueryData<MarksEntry[]>(
            scope.sectionId ? ["classroom", "marks", scope.sectionId] : ["marks"],
            (prev) =>
                (prev ?? []).map((e) =>
                    e.studentId === studentId
                        ? {
                              ...e,
                              rows: e.rows.map((r) =>
                                  r.subject === subject ? { ...r, obtained } : r,
                              ),
                          }
                        : e,
                ),
        );
    }

    /**
     * Write the scores currently on screen for the selected exam.
     *
     * One row per (exam, student, subject): the server upserts, so saving twice
     * cannot double a score. Needs an exam (the marks belong to one) and a section
     * (that is the scope the endpoint writes against).
     */
    const save = useCallback(async (): Promise<number> => {
        if (!scope.sectionId) return 0;
        const rows = filtered.filter((entry) => entry.examId);
        const examId = rows[0]?.examId;
        if (!examId) return 0;

        const payload = rows.flatMap((entry) =>
            entry.rows
                .filter((row) => row.subjectId)
                .map((row) => ({
                    studentId: entry.studentId,
                    subjectId: row.subjectId as string,
                    obtained: row.obtained,
                })),
        );
        if (payload.length === 0) return 0;

        setSaving(true);
        try {
            const written = await saveSectionMarks(scope.sectionId, examId, payload);
            await queryClient.invalidateQueries({ queryKey: ["classroom"] });
            return written;
        } finally {
            setSaving(false);
        }
    }, [scope.sectionId, filtered, queryClient]);

    const subjects = useMemo(() => {
        const set = new Set<string>();
        (filtered ?? []).forEach((e) => e.rows.forEach((r) => set.add(r.subject)));
        return Array.from(set);
    }, [filtered]);

    return {
        loading: entries === null,
        entries: filtered,
        exams,
        exam,
        setExam,
        className,
        setClassName,
        subjects,
        updateScore,
        save,
        saving,
        /** True when Save can actually write (the view is inside a class-section). */
        canSave: Boolean(scope.sectionId),
    };
}

