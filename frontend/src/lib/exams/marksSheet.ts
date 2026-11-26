import type { ExamPaperPlan } from "@/types";
import { gradeForPercent, round2, type LadderRung } from "./marking.ts";
import { amount, type MarkEdit } from "./view.ts";

/**
 * The marks table's live figures, as **pure functions** (`node --test` covers them).
 *
 * While a teacher types, each row shows its percentage, grade and Pass/Fail at once. They
 * come from the paper's **own** pass line and its **own** copy of the grading ladder (the
 * same rules the server judges the saved mark by), so what is on screen while typing is
 * what the family will be told. An absent child has no percentage and is neither pass nor
 * fail; zero is a score.
 */

export type RowState = "marked" | "absent" | "blank" | "invalid";

export interface RowFigures {
    state: RowState;
    percentage: number | null;
    grade: string | null;
    /** `true` pass, `false` fail, `null` when there is nothing to judge. */
    passed: boolean | null;
}

const NOTHING = { percentage: null, grade: null, passed: null } as const;

/** The ladder a paper is judged by: its own copy, else the school's. */
export function ladderOf(paper: ExamPaperPlan, fallback: LadderRung[]): LadderRung[] {
    const own = paper.gradingScale.map((rung) => ({
        minPercent: Number(rung.minPercent),
        grade: rung.grade,
    }));
    return own.length > 0 ? own : fallback;
}

/** Does a score pass on this paper? `marks` compares marks, `grade` compares the percent. */
export function passesPaper(score: number, paper: ExamPaperPlan): boolean | null {
    const total = amount(paper.maxMarks);
    if (total === null || !(total > 0)) return null;
    const EPS = 1e-9;
    if (paper.passMode === "grade") {
        const line = amount(paper.passPercent);
        return line === null ? null : score * 100 + EPS >= line * total;
    }
    const marks = amount(paper.passingMarks);
    return marks === null ? null : score + EPS >= marks;
}

/** One row's percentage, grade and result from what is typed in it right now. */
export function figuresFor(edit: MarkEdit, paper: ExamPaperPlan, ladder: LadderRung[]): RowFigures {
    if (edit.absent) return { state: "absent", ...NOTHING };
    const score = amount(edit.score);
    if (score === null) return { state: "blank", ...NOTHING };
    const total = amount(paper.maxMarks);
    if (total === null || !(total > 0) || score < 0 || score > total) {
        return { state: "invalid", ...NOTHING };
    }
    const percentage = round2((score * 100) / total);
    return {
        state: "marked",
        percentage,
        grade: gradeForPercent(ladder, percentage),
        passed: passesPaper(score, paper),
    };
}

/** How many of the **marked** children pass and fail, for the line under the table. */
export function passCounts(
    edits: MarkEdit[],
    paper: ExamPaperPlan,
    ladder: LadderRung[],
): { passed: number; failed: number } {
    let passed = 0;
    let failed = 0;
    for (const edit of edits) {
        const found = figuresFor(edit, paper, ladder);
        if (found.passed === true) passed += 1;
        else if (found.passed === false) failed += 1;
    }
    return { passed, failed };
}

/** `90` -> "90%", `33.33` -> "33.33%", `null` -> "—". */
export function percentCell(value: number | null): string {
    return value === null ? "—" : `${Number(value.toFixed(2))}%`;
}

/** A correction as one line: "45 → 10", "45 → Absent", "Absent → 30". */
export function changeText(item: {
    oldValue: string | number | null;
    newValue: string | number | null;
    oldAbsent: boolean;
    newAbsent: boolean;
}): string {
    const side = (value: string | number | null, absent: boolean) => {
        if (absent) return "Absent";
        const parsed = amount(value);
        return parsed === null ? "—" : String(Number(parsed.toFixed(2)));
    };
    return `${side(item.oldValue, item.oldAbsent)} → ${side(item.newValue, item.newAbsent)}`;
}
