"use client";

import { useApiQuery } from "@/lib/api/use-api-query";
import {
    getExam,
    getMarkingDefaults,
    getPaperMarks,
    getResultOverview,
    getSectionChoices,
    listExams,
} from "@/services";

// The Exams tab's reads, and the keys they cache under.
//
// `GET /exams` is called **without** a filter on purpose: the server already
// narrows it to what this caller may see (a teacher: the exams they hold a
// subject in; the office: all of them). Writing the filter here as well would
// fetch the same rows twice and let the two answers disagree.
//
// The detail and sheet keys sit **under** the list's key, so invalidating the
// list after a save re-reads the date sheet and the marks too - one call, no
// chance of a stale paper left on screen.

export const EXAM_LIST_KEY = ["exams", "plan"] as const;

export const examKey = (examId: string) => ["exams", "plan", "exam", examId] as const;

export const paperMarksKey = (paperId: string) => ["exams", "plan", "marks", paperId] as const;

export function useExamList(enabled = true) {
    return useApiQuery(EXAM_LIST_KEY, () => listExams({}), { enabled });
}

/**
 * The pre-filled pass line for a paper out of `total` marks. Disabled until the total is
 * a real number; the answer for a total is the same all day, so it is cached by total.
 */
/** The sections of this section's class that exist in the school, with their subjects. */
export function useSectionChoices(classroomId: string) {
    return useApiQuery(["exams", "sections", classroomId], () => getSectionChoices(classroomId), {
        staleTime: 60_000,
    });
}

export function useMarkingDefaults(total: number | null) {
    const ok = total !== null && total > 0 && total <= 9999.99;
    return useApiQuery(
        ["exams", "marking-defaults", ok ? total : 0],
        () => getMarkingDefaults(total ?? 0),
        { enabled: ok, staleTime: 5 * 60_000 },
    );
}

/**
 * The result overview of one kind: a section's class view (staff pass the section) or the
 * caller's own children (a student or guardian pass none).
 *
 * It sits **under** the exam list's key, so publishing marks or correcting one - which
 * invalidates the list - refreshes the results too.
 */
export function useResultOverview(kind: "class_test" | "school_exam", classroomId: string | null) {
    return useApiQuery([...EXAM_LIST_KEY, "results", kind, classroomId ?? "mine"], () =>
        getResultOverview(kind, classroomId),
    );
}

export function useExamDetail(examId: string | null) {
    const id = examId ?? "";
    return useApiQuery(examKey(id), () => getExam(id), { enabled: Boolean(id) });
}

export function usePaperSheet(paperId: string | null) {
    const id = paperId ?? "";
    return useApiQuery(paperMarksKey(id), () => getPaperMarks(id), { enabled: Boolean(id) });
}
