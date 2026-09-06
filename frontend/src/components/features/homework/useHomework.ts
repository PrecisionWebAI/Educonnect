"use client";
import { useEffect, useMemo, useState } from "react";
import { getHomeworks, getSubmissions, getDiary } from "@/services";
import type { HomeworkItem, SubmissionItem, DiaryEntry } from "@/types";

export type HomeworkTab = "Assign Homework" | "Submissions & Review" | "Class Diary";

export function useHomework() {
    const [homeworks, setHomeworks] = useState<HomeworkItem[]>([]);
    const [submissions, setSubmissions] = useState<SubmissionItem[]>([]);
    const [diary, setDiary] = useState<DiaryEntry[]>([]);
    const [loading, setLoading] = useState(true);
    const [query, setQuery] = useState("");

    useEffect(() => {
        let alive = true;
        Promise.all([getHomeworks(), getSubmissions(), getDiary()]).then(([h, s, d]) => {
            if (!alive) return;
            setHomeworks(h);
            setSubmissions(s);
            setDiary(d);
            setLoading(false);
        });
        return () => {
            alive = false;
        };
    }, []);

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
