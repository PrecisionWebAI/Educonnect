"use client";

import { useApiQuery } from "@/lib/api/use-api-query";
import { getExam, getPaperMarks, listExams } from "@/services";

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

export function useExamDetail(examId: string | null) {
    const id = examId ?? "";
    return useApiQuery(examKey(id), () => getExam(id), { enabled: Boolean(id) });
}

export function usePaperSheet(paperId: string | null) {
    const id = paperId ?? "";
    return useApiQuery(paperMarksKey(id), () => getPaperMarks(id), { enabled: Boolean(id) });
}
