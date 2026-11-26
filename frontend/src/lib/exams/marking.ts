import { amount } from "./view.ts";

/**
 * The pass line of one paper, as **pure functions**: Marks or Grade.
 *
 * The date-sheet row and the class-test form both show it, and `PassLineFields` is only
 * a skin over these functions - so the rules (33% pre-fill, the small "40%" beside the
 * number, custom grades, when Save must stay disabled) are tested with `node --test`
 * instead of in a browser. The server repeats every check (`plan/marking.py`); nothing
 * here is trusted, it only saves a round trip.
 *
 * Marks, not money, but the same care: rounding is half-up to two places, so 50 marks
 * at 33% reads 16.5 and 20 reads 6.6 - exactly what the server stores.
 */

/** One rung of a grading ladder: `>= minPercent` earns `grade`. */
export interface LadderRung {
    minPercent: number;
    grade: string;
}

export type PassBy = "marks" | "grade";

/** What the teacher has filled in for one paper's pass line. */
export interface PassLineDraft {
    passBy: PassBy;
    /** Text, because an input holds text: "", "33", "16.5". */
    passMarks: string;
    /** True once the teacher typed a number themselves - it then stops following the total. */
    passMarksEdited: boolean;
    passingGrade: string;
    /** Where a custom grade starts, as text (only asked when the grade is not on the ladder). */
    customMinPercent: string;
    /** How the marks sheet's Grade column works for this paper. */
    gradeMode: GradeMode;
}

export type GradeMode = "na" | "auto" | "manual";

/** The school's own pass percentage until it says otherwise. */
export const DEFAULT_PASS_PERCENT = 33;

export function blankPassLine(): PassLineDraft {
    return {
        passBy: "marks",
        passMarks: "",
        passMarksEdited: false,
        passingGrade: "",
        customMinPercent: "",
        gradeMode: "na",
    };
}

/** Two decimals, halves **up** (`16.5`, `6.6`; 4.125 -> 4.13). */
export function round2(value: number): number {
    return Math.round(value * 100 + 1e-9) / 100;
}

/** The number a new paper starts from: `percent` of the total (100 -> 33, 50 -> 16.5, 20 -> 6.6). */
export function defaultPassMarks(total: number, percent: number = DEFAULT_PASS_PERCENT): number {
    return round2((total * percent) / 100);
}

/** What percentage of the total `passMarks` is - the small "40%" beside the number. */
export function passPercentOf(passMarks: number, total: number): number | null {
    if (!(total > 0)) return null;
    return round2((passMarks * 100) / total);
}

/** `40` -> "40%", `33.33` -> "33.33%", `16.5` -> "16.5%" (no trailing zeros). */
export function percentText(value: number | null): string {
    if (value === null) return "";
    return `${Number(value.toFixed(2))}%`;
}

/** `33` -> "33", `16.5` -> "16.5", `6.6` -> "6.6" - the way the number goes in the input. */
export function marksText(value: number): string {
    return String(Number(value.toFixed(2)));
}

/** The ladder rung a grade names (case ignored), or `undefined` when it is custom. */
export function rungOf(ladder: LadderRung[], grade: string): LadderRung | undefined {
    const wanted = grade.trim().toLowerCase();
    if (!wanted) return undefined;
    return ladder.find((rung) => rung.grade.toLowerCase() === wanted);
}

/** The grade a percentage earns on `ladder` (highest rung it reaches), or `null`. */
export function gradeForPercent(ladder: LadderRung[], percent: number | null): string | null {
    if (percent === null) return null;
    const rungs = [...ladder].sort((a, b) => b.minPercent - a.minPercent);
    return rungs.find((rung) => percent >= rung.minPercent)?.grade ?? null;
}

/**
 * The draft after the **total** changed.
 *
 * Until the teacher types their own number, the pass marks follow the total (a total of
 * 50 reads 16.5, then 20 reads 6.6). Once they typed one, it is theirs and stays.
 */
export function followTotal(
    draft: PassLineDraft,
    total: number | null,
    schoolPercent: number = DEFAULT_PASS_PERCENT,
): PassLineDraft {
    if (draft.passMarksEdited) return draft;
    if (total === null || !(total > 0)) return { ...draft, passMarks: "" };
    return { ...draft, passMarks: marksText(defaultPassMarks(total, schoolPercent)) };
}

/** The draft after the teacher typed in the pass-marks box. */
export function editPassMarks(draft: PassLineDraft, text: string): PassLineDraft {
    return { ...draft, passMarks: text, passMarksEdited: true };
}

/** Switch between Marks and Grade without losing what was typed for the other. */
export function choosePassBy(draft: PassLineDraft, passBy: PassBy): PassLineDraft {
    return { ...draft, passBy };
}

/** The small "40%" beside the pass-marks box, or "" when there is nothing to say. */
export function passMarksPercentText(draft: PassLineDraft, total: number | null): string {
    const marks = amount(draft.passMarks);
    if (marks === null || total === null) return "";
    return percentText(passPercentOf(marks, total));
}

/** Does this grade need its own starting percentage (it is not on the ladder)? */
export function needsCustomPercent(draft: PassLineDraft, ladder: LadderRung[]): boolean {
    return (
        draft.passBy === "grade" &&
        draft.passingGrade.trim() !== "" &&
        rungOf(ladder, draft.passingGrade) === undefined
    );
}

/**
 * Why this pass line cannot be saved yet - or `null` when it can.
 *
 * Drives the parent card's Save button: an incomplete pass line keeps it disabled, and the
 * sentence is shown under the field. The server repeats each rule.
 */
export function passLineIssue(
    draft: PassLineDraft,
    total: number | null,
    ladder: LadderRung[],
): string | null {
    if (total === null || !(total > 0)) return "Enter the total marks first.";
    if (draft.passBy === "marks") {
        const marks = amount(draft.passMarks);
        if (marks === null) return "Enter the passing marks.";
        if (marks < 0) return "Passing marks cannot be below 0.";
        if (marks > total)
            return `Passing marks cannot be more than the total (${marksText(total)}).`;
        return null;
    }
    const grade = draft.passingGrade.trim();
    if (!grade) return "Choose the lowest passing grade.";
    if (rungOf(ladder, grade) !== undefined) return null;
    if (!/^[A-Z][A-Z0-9]?$/.test(grade)) {
        return "A custom grade is up to two characters: a capital letter first, then a letter or a number.";
    }
    // A custom grade passes at the school's own pass percentage - nothing more to ask.
    return null;
}

/** The pass-line fields of the schedule payload (snake_case, as the API reads them). */
export interface PassLineBody {
    pass_mode: PassBy;
    passing_marks: number | null;
    passing_grade: string | null;
    custom_min_percent: number | null;
    grade_mode: GradeMode;
}

export function passLineBody(draft: PassLineDraft): PassLineBody {
    if (draft.passBy === "marks") {
        return {
            pass_mode: "marks",
            passing_marks: amount(draft.passMarks),
            passing_grade: null,
            custom_min_percent: null,
            grade_mode: draft.gradeMode,
        };
    }
    return {
        pass_mode: "grade",
        passing_marks: null,
        passing_grade: draft.passingGrade.trim(),
        custom_min_percent: amount(draft.customMinPercent),
        grade_mode: draft.gradeMode,
    };
}

/** What a grade box keeps while typing: capitals, a letter first, then a letter or a digit, at most two. */
export function cleanGradeInput(text: string): string {
    return text
        .toUpperCase()
        .replace(/[^A-Z0-9]/g, "")
        .replace(/^[0-9]+/, "")
        .slice(0, 2);
}

/** Is this a grade that can be saved (a capital letter, then a letter or a digit)? */
export function isGradeText(text: string): boolean {
    return /^[A-Z][A-Z0-9]?$/.test(text);
}
