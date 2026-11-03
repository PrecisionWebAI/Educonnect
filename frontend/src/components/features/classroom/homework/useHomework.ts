"use client";

import { useMemo, useState } from "react";
import { getHomeworks, getSectionHomeworks, getStudents, getSubmissions, getDiary } from "@/services";
import { useApiQuery } from "@/lib/api/use-api-query";

export type HomeworkTab = "Assign Homework" | "Submissions & Review" | "Class Diary";

/**
 * The class-section the homework board belongs to.
 *
 * With a scope, the assignments come from that section's own endpoint
 * (`/homework/section/{id}`), the submissions are narrowed to that section's
 * students and the diary to that class-section's log. Without one the hook keeps
 * the school-wide behaviour.
 */
export interface HomeworkScope {
    sectionId?: string;
    className?: string;
    section?: string;
}

export function useHomework(scope: HomeworkScope = {}) {
    const homeworksQuery = useApiQuery(
        scope.sectionId ? ["homework", "section", scope.sectionId] : ["homework"],
        () => (scope.sectionId ? getSectionHomeworks(scope.sectionId) : getHomeworks()),
    );
    const submissionsQuery = useApiQuery(["homework", "submissions"], getSubmissions);
    const diaryQuery = useApiQuery(["homework", "diary"], getDiary);
    // Only needed to recognise this section's students in the submissions list.
    const studentsQuery = useApiQuery(["students"], () => getStudents(), {
        enabled: Boolean(scope.className && scope.section),
    });

    // Memoised so the arrays keep one identity across renders: the filters below
    // depend on them, and a fresh `[]` each render would re-run them every time.
    const homeworks = useMemo(() => homeworksQuery.data ?? [], [homeworksQuery.data]);
    const submissions = useMemo(() => submissionsQuery.data ?? [], [submissionsQuery.data]);
    const diary = useMemo(() => diaryQuery.data ?? [], [diaryQuery.data]);
    const loading =
        homeworksQuery.isPending || submissionsQuery.isPending || diaryQuery.isPending;
    const [query, setQuery] = useState("");

    /** The names of the students who sit in this class-section. */
    const sectionStudents = useMemo(() => {
        if (!scope.className || !scope.section) return null;
        return new Set(
            (studentsQuery.data ?? [])
                .filter((s) => s.className === scope.className && s.section === scope.section)
                .map((s) => s.name),
        );
    }, [studentsQuery.data, scope.className, scope.section]);

    const sectionLabel = scope.className && scope.section
        ? `${scope.className}-${scope.section}`
        : "";

    const scopedSubmissions = useMemo(
        () =>
            sectionStudents
                ? submissions.filter((s) => sectionStudents.has(s.student))
                : submissions,
        [submissions, sectionStudents],
    );
    const scopedDiary = useMemo(
        () =>
            sectionLabel
                ? diary.filter((entry) => entry.className === sectionLabel)
                : diary,
        [diary, sectionLabel],
    );

    const filteredHomeworks = useMemo(
        () =>
            homeworks.filter(
                (h) =>
                    !query ||
                    h.title.toLowerCase().includes(query.toLowerCase()) ||
                    // The name comes from the subject row, so it can be absent on a
                    // row written before the subject existed.
                    (h.subject ?? "").toLowerCase().includes(query.toLowerCase()),
            ),
        [homeworks, query],
    );
    const filteredSubmissions = useMemo(
        () =>
            scopedSubmissions.filter(
                (s) =>
                    !query ||
                    s.student.toLowerCase().includes(query.toLowerCase()) ||
                    s.homeworkTitle.toLowerCase().includes(query.toLowerCase()),
            ),
        [scopedSubmissions, query],
    );
    const submittedCount = scopedSubmissions.filter((s) => s.status === "Submitted").length;
    const pendingCount = scopedSubmissions.filter((s) => s.status === "Pending").length;

    return {
        homeworks: filteredHomeworks,
        filteredHomeworks,
        submissions: scopedSubmissions,
        filteredSubmissions,
        diary: scopedDiary,
        loading,
        query,
        setQuery,
        submittedCount,
        pendingCount,
    };
}

