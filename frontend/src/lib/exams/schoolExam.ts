import type { ExamPaperPlan, ExamPlan } from "@/types";
import {
    blankPassLine,
    defaultPassMarks,
    followTotal,
    marksText,
    passLineBody,
    passLineIssue,
    percentText as pct,
    type LadderRung,
    type PassLineDraft,
} from "./marking.ts";
import { amount, figureText } from "./view.ts";

/**
 * The School Exam date sheet's rules, as **pure functions** (`node --test` covers them).
 *
 * A date sheet is one section's list of subjects, each with a **date**, a **total** and its
 * own **pass line** (marks or grade); the syllabus is written separately by the subject
 * teacher. There is no first/last day and no clock time. The form holds a
 * `SchoolExamDraft`; these functions turn it into the create/update body and read the
 * server's answers. The server repeats every rule.
 */

/** The types in the spec's order; `custom` means the teacher types the exam's name. */
export const SCHOOL_EXAM_TYPES = [
    { value: "unit_test", label: "Unit Test" },
    { value: "periodic_test", label: "Periodic Test" },
    { value: "mid_term_test", label: "Mid Term Test" },
    { value: "half_yearly", label: "Half Yearly" },
    { value: "annual", label: "Annual" },
    { value: "pre_board", label: "Pre-Board" },
    { value: "practical", label: "Practical" },
    { value: "custom", label: "Custom" },
] as const;

/** Is this one of the new School Exam types (as opposed to a class test or an older exam)? */
export function isSchoolExamType(type: string | null | undefined): boolean {
    return SCHOOL_EXAM_TYPES.some((item) => item.value === type);
}

export function typeLabel(type: string | null | undefined): string {
    return SCHOOL_EXAM_TYPES.find((item) => item.value === type)?.label ?? type ?? "";
}

/** A new row starts at a full paper; every subject's total is the teacher's to change. */
export const DEFAULT_TOTAL = "100";

export interface SchoolRowDraft {
    subjectId: string;
    subjectName: string;
    /** On the date sheet or not (a subject can be left off). */
    included: boolean;
    /** `yyyy-MM-dd`. */
    examDate: string;
    total: string;
    passLine: PassLineDraft;
    /** Who takes this paper: "" = the subject's assigned teacher; else a temporary teacher. */
    takenBy: string;
}

export interface SchoolExamDraft {
    examType: string;
    /** The teacher's own name for the exam (only when the type is `custom`). */
    customName: string;
    familyNote: string;
    rows: SchoolRowDraft[];
}

function blankRow(subject: { id: string; name: string }, schoolPercent: number): SchoolRowDraft {
    return {
        subjectId: subject.id,
        subjectName: subject.name,
        included: true,
        examDate: "",
        total: DEFAULT_TOTAL,
        passLine: followTotal(blankPassLine(), Number(DEFAULT_TOTAL), schoolPercent),
        takenBy: "",
    };
}

export function blankSchoolExamDraft(
    subjects: { id: string; name: string }[],
    schoolPercent: number = 33,
): SchoolExamDraft {
    return {
        examType: "",
        customName: "",
        familyNote: "",
        rows: subjects.map((subject) => blankRow(subject, schoolPercent)),
    };
}

/** The draft an existing date sheet opens with; subjects not on it start switched off. */
export function schoolExamDraftFromExam(
    exam: ExamPlan,
    subjects: { id: string; name: string }[],
    schoolPercent: number = 33,
): SchoolExamDraft {
    return {
        examType: exam.examType ?? "",
        customName: exam.examType === "custom" ? exam.name : "",
        familyNote: exam.familyNote ?? "",
        rows: subjects.map((subject) => {
            const paper = exam.papers.find((item) => item.classroomSubjectId === subject.id);
            if (!paper) return { ...blankRow(subject, schoolPercent), included: false };
            const total = amount(paper.maxMarks);
            const passMarks = amount(paper.passingMarks);
            const atDefault =
                total !== null && passMarks !== null && passMarks === defaultPassMarks(total);
            return {
                subjectId: subject.id,
                subjectName: subject.name,
                included: true,
                examDate: paper.examDate ?? "",
                total: total === null ? "" : marksText(total),
                passLine: {
                    ...blankPassLine(),
                    passBy: paper.passMode === "grade" ? "grade" : "marks",
                    passMarks: passMarks === null ? "" : marksText(passMarks),
                    passMarksEdited: !atDefault,
                    passingGrade: paper.passingGrade ?? "",
                    gradeMode: paper.gradeMode ?? "na",
                },
                takenBy: paper.isTemporary ? (paper.takenByEmployeeId ?? "") : "",
            };
        }),
    };
}

/** What stops the date sheet from being saved (each sentence is shown to the teacher). */
export function schoolExamProblems(draft: SchoolExamDraft, ladder: LadderRung[]): string[] {
    const found: string[] = [];
    if (!draft.examType) found.push("Choose the type of exam.");
    if (draft.examType === "custom" && !draft.customName.trim()) {
        found.push("Type the name of this exam.");
    }
    const included = draft.rows.filter((row) => row.included);
    if (included.length === 0) found.push("Keep at least one subject on the date sheet.");
    for (const row of included) {
        if (!row.examDate) found.push(`${row.subjectName}: choose the date.`);
        const total = amount(row.total);
        if (total === null || total <= 0) {
            found.push(`${row.subjectName}: enter the total marks.`);
            continue;
        }
        if (total > 9999.99) found.push(`${row.subjectName}: the total marks are too large.`);
        const issue = passLineIssue(row.passLine, total, ladder);
        if (issue) found.push(`${row.subjectName}: ${issue}`);
    }
    return found;
}

function rowBodies(draft: SchoolExamDraft): Record<string, unknown>[] {
    return draft.rows
        .filter((row) => row.included)
        .map((row) => ({
            classroom_subject_id: row.subjectId,
            exam_date: row.examDate,
            total_marks: amount(row.total),
            taken_by_employee_id: row.takenBy || null,
            ...passLineBody(row.passLine),
        }));
}

/** The body of `POST /exams/school-exams`. */
export function schoolExamCreateBody(
    draft: SchoolExamDraft,
    classroomId: string,
    options: { confirmDuplicate?: boolean } = {},
): Record<string, unknown> {
    return {
        classroom_id: classroomId,
        confirm_duplicate: options.confirmDuplicate ?? false,
        exam_type: draft.examType,
        custom_name: draft.examType === "custom" ? draft.customName.trim() : null,
        family_note: draft.familyNote.trim() || null,
        rows: rowBodies(draft),
    };
}

/**
 * The body of `PATCH /exams/school-exams/{id}`: the top-level fields **that changed**, plus
 * the whole sheet (the server compares it with what is saved and tells the families only
 * what really moved).
 */
export function schoolExamUpdateBody(
    draft: SchoolExamDraft,
    exam: ExamPlan,
    options: { confirmDuplicate?: boolean } = {},
): Record<string, unknown> {
    const body: Record<string, unknown> = { rows: rowBodies(draft) };
    if (options.confirmDuplicate) body.confirm_duplicate = true;
    const nameNow = draft.examType === "custom" ? draft.customName.trim() : "";
    const nameWas = exam.examType === "custom" ? exam.name : "";
    if (draft.examType !== (exam.examType ?? "") || nameNow !== nameWas) {
        body.exam_type = draft.examType;
        body.custom_name = draft.examType === "custom" ? nameNow : null;
    }
    if (draft.familyNote.trim() !== (exam.familyNote ?? "").trim()) {
        body.family_note = draft.familyNote.trim() || null;
    }
    return body;
}

/** Draft until the class teacher publishes it; then Published; Cancelled when called off. */
export function schoolExamChip(exam: ExamPlan): {
    label: string;
    tone: "muted" | "green" | "red";
} {
    if (exam.status === "cancelled") return { label: "Cancelled", tone: "red" };
    if (exam.datesheetPublishedAt) return { label: "Published", tone: "green" };
    return { label: "Draft", tone: "muted" };
}

/** A subject's pass line in words: "33 (33%)" for marks, "Grade D" for a grade. */
export function passText(paper: ExamPaperPlan): string {
    if (paper.passMode === "grade") {
        return paper.passingGrade ? `Grade ${paper.passingGrade}` : "—";
    }
    const marks = amount(paper.passingMarks);
    if (marks === null) return "—";
    const percent = amount(paper.passPercent);
    return percent === null ? figureText(marks) : `${figureText(marks)} (${pct(percent)})`;
}

/** How many subjects have a syllabus written, out of the sheet. */
export function syllabusProgress(exam: ExamPlan): { written: number; total: number } {
    return {
        written: exam.papers.filter((paper) => paper.hasSyllabus).length,
        total: exam.papers.length,
    };
}

/** The last day on an exam's date sheet (`""` when it has no dates yet). */
export function lastDateOf(exam: ExamPlan): string {
    const dates = exam.papers
        .map((paper) => paper.examDate)
        .filter((date): date is string => Boolean(date))
        .sort();
    return dates[dates.length - 1] ?? exam.endDate ?? exam.startDate ?? "";
}

/**
 * School exams in two lists: **upcoming** (the last paper is today or later - nearest
 * first; an exam with no date yet is upcoming and last) and **past** (every paper has
 * gone by - the most recent first).
 */
export function splitSchoolByDate(
    exams: ExamPlan[],
    today: string,
): { upcoming: ExamPlan[]; past: ExamPlan[] } {
    const upcoming = exams.filter((exam) => !lastDateOf(exam) || lastDateOf(exam) >= today);
    const past = exams.filter((exam) => lastDateOf(exam) && lastDateOf(exam) < today);
    upcoming.sort((a, b) =>
        (lastDateOf(a) || "9999-12-31").localeCompare(lastDateOf(b) || "9999-12-31"),
    );
    past.sort((a, b) => lastDateOf(b).localeCompare(lastDateOf(a)));
    return { upcoming, past };
}
