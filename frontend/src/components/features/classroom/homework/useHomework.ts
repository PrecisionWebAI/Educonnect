"use client";

import { useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { getDiary, getHomeworks, getSectionHomeworks, getSubmissions } from "@/services";
import { useApiQuery } from "@/lib/api/use-api-query";

export type HomeworkTab = "Assign Homework" | "Submissions & Review" | "Class Diary";

/**
 * The class-section the homework board belongs to.
 *
 * With a scope, all three reads are narrowed **on the server** - the section's own
 * assignments, its submissions (`/homework/submissions?section_id=`) and its diary - so
 * the board never filters another section's rows out in the browser (Phase 9: the old
 * hook matched student *names*, which two children can share).
 */
export interface HomeworkScope {
    sectionId?: string;
    className?: string;
    section?: string;
}

export function useHomework(scope: HomeworkScope = {}) {
    const queryClient = useQueryClient();
    const sectionId = scope.sectionId;
    const homeworksQuery = useApiQuery(
        sectionId ? ["homework", "section", sectionId] : ["homework"],
        () => (sectionId ? getSectionHomeworks(sectionId) : getHomeworks()),
    );
    const submissionsQuery = useApiQuery(
        sectionId ? ["homework", "submissions", sectionId] : ["homework", "submissions"],
        () => getSubmissions(sectionId),
    );
    const diaryQuery = useApiQuery(
        sectionId ? ["homework", "diary", sectionId] : ["homework", "diary"],
        () => getDiary(sectionId),
    );

    // Memoised so the arrays keep one identity across renders: the filters below
    // depend on them, and a fresh `[]` each render would re-run them every time.
    const homeworks = useMemo(() => homeworksQuery.data ?? [], [homeworksQuery.data]);
    const submissions = useMemo(() => submissionsQuery.data ?? [], [submissionsQuery.data]);
    const diary = useMemo(() => diaryQuery.data ?? [], [diaryQuery.data]);
    const loading = homeworksQuery.isPending || submissionsQuery.isPending || diaryQuery.isPending;
    const [query, setQuery] = useState("");

    const filteredHomeworks = useMemo(
        () =>
            homeworks.filter(
                (h) =>
                    !query ||
                    h.title.toLowerCase().includes(query.toLowerCase()) ||
                    (h.subject ?? "").toLowerCase().includes(query.toLowerCase()),
            ),
        [homeworks, query],
    );
    const filteredSubmissions = useMemo(
        () =>
            submissions.filter(
                (s) =>
                    !query ||
                    s.student.toLowerCase().includes(query.toLowerCase()) ||
                    s.homeworkTitle.toLowerCase().includes(query.toLowerCase()),
            ),
        [submissions, query],
    );
    const filteredDiary = useMemo(
        () =>
            diary.filter(
                (entry) =>
                    !query ||
                    entry.topic.toLowerCase().includes(query.toLowerCase()) ||
                    entry.subject.toLowerCase().includes(query.toLowerCase()),
            ),
        [diary, query],
    );

    const submittedCount = submissions.filter((s) => s.id !== null).length;
    const pendingCount = submissions.filter((s) => s.id === null).length;

    /** Anything that changed a submission or a diary line: re-read the whole board. */
    async function refresh() {
        await Promise.all([
            queryClient.invalidateQueries({ queryKey: ["homework"] }),
            queryClient.invalidateQueries({ queryKey: ["classroom"] }),
        ]);
    }

    return {
        homeworks,
        filteredHomeworks,
        submissions,
        filteredSubmissions,
        diary,
        filteredDiary,
        loading,
        query,
        setQuery,
        submittedCount,
        pendingCount,
        refresh,
    };
}
