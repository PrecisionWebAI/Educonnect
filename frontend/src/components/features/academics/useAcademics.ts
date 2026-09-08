"use client";

import { useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { getMarks } from "@/services";
import { useApiQuery } from "@/lib/api/use-api-query";
import type { MarksEntry } from "@/types";

// All academics/marks data logic in one hook.

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

export function useAcademics() {
    const queryClient = useQueryClient();
    const marksQuery = useApiQuery(["marks"], getMarks);
    const entries = marksQuery.data ?? null;
    const [exam, setExam] = useState("all");
    const [className, setClassName] = useState("all");

    const exams = useMemo(() => Array.from(new Set((entries ?? []).map((e) => e.exam))), [entries]);
    const classNames = useMemo(
        () => Array.from(new Set((entries ?? []).map((e) => e.className))),
        [entries],
    );

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
    function updateScore(studentId: number, subject: string, obtained: number) {
        queryClient.setQueryData<MarksEntry[]>(["marks"], (prev) =>
            (prev ?? []).map((e) =>
                e.studentId === studentId
                    ? {
                          ...e,
                          rows: e.rows.map((r) => (r.subject === subject ? { ...r, obtained } : r)),
                      }
                    : e,
            ),
        );
    }

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
        classNames,
        className,
        setClassName,
        subjects,
        updateScore,
    };
}
