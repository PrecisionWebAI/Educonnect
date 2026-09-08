"use client";
import { useMemo, useState } from "react";
import { getHomeworks, getSubmissions, getDiary } from "@/services";
import { useApiQuery } from "@/lib/api/use-api-query";

export type HomeworkTab = "Assign Homework" | "Submissions & Review" | "Class Diary";

export function useHomework() {
    const homeworksQuery = useApiQuery(["homework"], getHomeworks);
    const submissionsQuery = useApiQuery(["homework", "submissions"], getSubmissions);
    const diaryQuery = useApiQuery(["homework", "diary"], getDiary);
    const homeworks = homeworksQuery.data ?? [];
    const submissions = submissionsQuery.data ?? [];
    const diary = diaryQuery.data ?? [];
    const loading =
        homeworksQuery.isPending || submissionsQuery.isPending || diaryQuery.isPending;
    const [query, setQuery] = useState("");

    const filteredHomeworks = useMemo(
        () =>
            homeworks.filter(
                (h) =>
                    !query ||
                    h.title.toLowerCase().includes(query.toLowerCase()) ||
                    h.subject.toLowerCase().includes(query.toLowerCase()),
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
    const submittedCount = submissions.filter((s) => s.status === "Submitted").length;
    const pendingCount = submissions.filter((s) => s.status === "Pending").length;

    return {
        homeworks,
        filteredHomeworks,
        submissions,
        filteredSubmissions,
        diary,
        loading,
        query,
        setQuery,
        submittedCount,
        pendingCount,
    };
}
