import type {
    OverviewEntry,
    OverviewStats,
    OverviewStudent,
    OverviewTest,
    ResultOverview,
} from "@/types";
import { amount, dayText, figureText } from "./view.ts";

/**
 * The Exam Result tab's wording, as **pure functions** (`node --test` covers them).
 *
 * The server does the sums (`plan/overview.py`); this file only decides how a figure
 * reads. The school's `display_mode` - `marks`, `grades` or `both` - is applied **here, in
 * one place**, so every cell of every table follows it the same way. An absent child reads
 * "Absent", never a percentage; a missing figure is a dash, never a zero.
 */

export type DisplayMode = ResultOverview["displayMode"];

export function showsMarks(mode: DisplayMode): boolean {
    return mode === "marks" || mode === "both";
}

export function showsGrades(mode: DisplayMode): boolean {
    return mode === "grades" || mode === "both";
}

/** `90` -> "90%", `78.5714` -> "78.57%", `null` -> "". */
export function percentOf(value: string | number | null | undefined): string {
    const parsed = amount(value);
    return parsed === null ? "" : `${Number(parsed.toFixed(2))}%`;
}

/**
 * A percentage and its grade, the way the school shows them: `78.57% · B1`,
 * `78.57%` (marks only), `B1` (grades only), `—` when there is nothing yet.
 */
export function percentGradeText(
    percentage: string | number | null | undefined,
    grade: string | null | undefined,
    mode: DisplayMode,
): string {
    const parts: string[] = [];
    const percent = percentOf(percentage);
    if (showsMarks(mode) && percent) parts.push(percent);
    if (showsGrades(mode) && grade) parts.push(grade);
    return parts.length > 0 ? parts.join(" · ") : "—";
}

/** One child's result on one test: `45/50 (90%) · A1`, `Absent`, or `—` (not marked). */
export function entryText(
    entry: OverviewEntry | undefined,
    totalMarks: string | number,
    mode: DisplayMode,
): string {
    if (!entry) return "—";
    if (entry.absent) return "Absent";
    if (entry.obtained === null) return "—";
    const parts: string[] = [];
    if (showsMarks(mode)) {
        const percent = percentOf(entry.percentage);
        parts.push(
            `${figureText(entry.obtained)}/${figureText(totalMarks)}${percent ? ` (${percent})` : ""}`,
        );
    }
    if (showsGrades(mode) && entry.grade) parts.push(entry.grade);
    return parts.join(" · ") || "—";
}

/** Pass, Fail, Absent - or nothing to say yet. */
export function resultBadge(
    entry: OverviewEntry | undefined,
): { label: string; tone: "green" | "red" | "amber" } | null {
    if (!entry) return null;
    if (entry.absent) return { label: "Absent", tone: "amber" };
    if (entry.passed === true) return { label: "Pass", tone: "green" };
    if (entry.passed === false) return { label: "Fail", tone: "red" };
    return null;
}

/** "3 passed · 1 failed" - what the overall line says about the tests so far. */
export function passFailText(passed: number, failed: number): string {
    if (passed === 0 && failed === 0) return "—";
    return `${passed} passed · ${failed} failed`;
}

/** Every subject any child has a result in, alphabetically (the class table's columns). */
export function subjectColumns(students: OverviewStudent[]): string[] {
    const seen = new Map<string, string>();
    for (const student of students) {
        for (const line of student.subjects) {
            const key = line.subject.trim().toLowerCase();
            if (!seen.has(key)) seen.set(key, line.subject);
        }
    }
    return [...seen.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([, name]) => name);
}

/** A child's cumulative line for one subject, matched by name (any case). */
export function subjectOf(student: OverviewStudent, subject: string) {
    const key = subject.trim().toLowerCase();
    return student.subjects.find((line) => line.subject.trim().toLowerCase() === key);
}

/** The tests of one exam together, in the order the server sent them. */
export function groupByExam(
    tests: OverviewTest[],
): { examId: string; examName: string; tests: OverviewTest[] }[] {
    const groups: { examId: string; examName: string; tests: OverviewTest[] }[] = [];
    for (const test of tests) {
        const last = groups.find((group) => group.examId === test.examId);
        if (last) last.tests.push(test);
        else groups.push({ examId: test.examId, examName: test.examName, tests: [test] });
    }
    return groups;
}

/** A test's name as a row label: "Mathematics · 5 Dec". */
export function testLabel(test: OverviewTest): string {
    const date = dayText(test.examDate);
    return date === "—" ? test.subject : `${test.subject} · ${date}`;
}

/** The class view's figures for one test, each as the cell shows it. */
export function statsCells(stats: OverviewStats | null): {
    marked: string;
    absent: string;
    average: string;
    highest: string;
    lowest: string;
    passed: string;
    failed: string;
} {
    if (!stats || stats.marked + stats.absent === 0) {
        return {
            marked: "—",
            absent: "—",
            average: "—",
            highest: "—",
            lowest: "—",
            passed: "—",
            failed: "—",
        };
    }
    return {
        marked: String(stats.marked),
        absent: String(stats.absent),
        average:
            stats.averageMarks === null
                ? "—"
                : `${figureText(stats.averageMarks)}${
                      stats.averagePercentage ? ` (${percentOf(stats.averagePercentage)})` : ""
                  }`,
        highest: stats.highest === null ? "—" : figureText(stats.highest),
        lowest: stats.lowest === null ? "—" : figureText(stats.lowest),
        passed: String(stats.passed),
        failed: String(stats.failed),
    };
}

/** Is there anything to show a family (a published test with a result)? */
export function hasResults(overview: ResultOverview): boolean {
    return overview.tests.some((test) => test.published);
}

/** The entry a child has for a test, if any. */
export function entryFor(student: OverviewStudent, test: OverviewTest): OverviewEntry | undefined {
    return student.entries.find((entry) => entry.paperId === test.paperId);
}
