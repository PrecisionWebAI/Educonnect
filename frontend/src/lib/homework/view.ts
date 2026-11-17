import type { SubmissionItem } from "@/types";

/**
 * The Homework tab's rules, as **pure functions**.
 *
 * Same reason as the other tabs: there is no component-test stack, so what is worth
 * testing - how a submission is labelled, what a grade needs, how the board counts -
 * lives here and is covered by `node --test`.
 */

export type ChipTone = "green" | "amber" | "red" | "muted" | "accent" | "violet" | "teal";

/** How one submission reads at a glance. Lateness is said on the chip, not hidden. */
export function submissionChip(item: {
    status: SubmissionItem["status"];
    isLate: boolean;
    id: string | null;
}): { label: string; tone: ChipTone } {
    if (item.id === null) return { label: "Not handed in", tone: "muted" };
    if (item.status === "Graded") {
        return { label: item.isLate ? "Graded · late" : "Graded", tone: "violet" };
    }
    if (item.status === "Submitted") {
        return { label: item.isLate ? "Late" : "Handed in", tone: item.isLate ? "red" : "green" };
    }
    return { label: "Pending", tone: "amber" };
}

/** The "Submitted" column: the time it arrived, or a dash. */
export function handedInText(item: { submittedAt: string }): string {
    return item.submittedAt === "" ? "—" : item.submittedAt;
}

/** What the board says above the table: "2 in · 1 late · 1 to grade". */
export function boardCounts(rows: SubmissionItem[]): {
    handedIn: number;
    late: number;
    pending: number;
    graded: number;
} {
    let handedIn = 0;
    let late = 0;
    let pending = 0;
    let graded = 0;
    for (const row of rows) {
        if (row.id === null) {
            pending += 1;
            continue;
        }
        handedIn += 1;
        if (row.isLate) late += 1;
        if (row.status === "Graded") graded += 1;
    }
    return { handedIn, late, pending, graded };
}

/** `"3/4 in"` - the assignment's own line on the board. */
export function progressText(item: { submitted: number; total: number }): string {
    if (item.total <= 0) return item.submitted > 0 ? `${item.submitted} in` : "No roll yet";
    return `${item.submitted}/${item.total} in`;
}

/**
 * What is wrong with the score box, or `null` when it is fine.
 *
 * Homework carries **no maximum** (`homeworkassignment` has no `max_marks` column, and
 * Phase 9 did not invent one), so this cannot say "out of 100" - it only refuses what is
 * not a score: text, a negative number, more than two decimals.
 */
export function marksProblem(marks: string): string | null {
    const text = marks.trim();
    if (text === "") return null;
    const value = Number(text);
    if (!Number.isFinite(value)) return "Enter a number.";
    if (value < 0) return "A score cannot be negative.";
    if (Math.round(value * 100) !== value * 100) return "Two decimals at most.";
    return null;
}

/**
 * May this row be graded, and if not, why not?
 *
 * The server's rule, said before the button: there must be something to say (a score,
 * a remark, or both), the score must be a score, and a child who never handed anything
 * in has nothing to grade.
 */
export function gradeGate({
    marks,
    feedback,
    item,
}: {
    marks: string;
    feedback: string;
    item: SubmissionItem;
}): { allowed: boolean; reason: string | null } {
    if (item.id === null) {
        return { allowed: false, reason: "This child has not handed anything in." };
    }
    const problem = marksProblem(marks);
    if (problem) return { allowed: false, reason: problem };
    if (marks.trim() === "" && feedback.trim() === "") {
        return { allowed: false, reason: "Give a score, a remark, or both." };
    }
    return { allowed: true, reason: null };
}

/** The body the feedback call sends - blanks become `null`, not empty strings. */
export function feedbackBody(
    marks: string,
    feedback: string,
): {
    marksAwarded: number | null;
    feedback: string | null;
} {
    const text = marks.trim();
    return {
        marksAwarded: text === "" ? null : Number(text),
        feedback: feedback.trim() === "" ? null : feedback.trim(),
    };
}

/** `8.5` -> `"8.5"`, `null` -> `"—"` - a figure as a person reads it. */
export function marksText(value: number | string | null | undefined): string {
    if (value === null || value === undefined || value === "") return "—";
    const parsed = typeof value === "number" ? value : Number(value);
    if (!Number.isFinite(parsed)) return "—";
    return String(Math.round(parsed * 100) / 100);
}
