"use client";

import { useEffect, useMemo, useState } from "react";
import { getMarks } from "@/services";
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
    const [entries, setEntries] = useState<MarksEntry[] | null>(null);
    const [exam, setExam] = useState("all");
    const [className, setClassName] = useState("all");

    useEffect(() => {
        void getMarks().then(setEntries);
    }, []);

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

    /** Update a single subject score for a student (mock — will be an API call). */
    function updateScore(studentId: number, subject: string, obtained: number) {
        setEntries((prev) =>
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
