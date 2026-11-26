import type { ExamPlan } from "@/types";
import {
    blankPassLine,
    defaultPassMarks,
    marksText,
    passLineBody,
    passLineIssue,
    type LadderRung,
    type PassLineDraft,
} from "./marking.ts";
import { amount } from "./view.ts";

/**
 * The Class Test form's rules, as **pure functions** (`node --test` covers them).
 *
 * A class test is one subject, one date and one total, sat by one or several sections of
 * one class. The form holds a `ClassTestDraft`; these functions turn it into the create
 * body, into a **patch of only what changed** (so a reschedule is never confused with a
 * total-marks edit), and read the server's answers (the duplicate warning, the status).
 * The server repeats every rule; nothing here is trusted.
 */

/** Test Taken By = "" means "each section's assigned teacher". */
export interface ClassTestDraft {
    /** The anchor: the section subject the teacher picked from this section's course list. */
    subjectId: string;
    /** Every section (classroom) that sits it - all of one class. */
    sectionIds: string[];
    /** `yyyy-MM-dd`. */
    examDate: string;
    total: string;
    takenBy: string;
    familyNote: string;
    /** Free text: what will come in the test. */
    syllabus: string;
    passLine: PassLineDraft;
}

export function blankClassTestDraft(input: {
    classroomId: string;
    subjectId?: string;
}): ClassTestDraft {
    return {
        subjectId: input.subjectId ?? "",
        sectionIds: [input.classroomId],
        examDate: "",
        total: "",
        takenBy: "",
        familyNote: "",
        syllabus: "",
        passLine: blankPassLine(),
    };
}

/** The draft an existing test opens with (its papers all share one date, total and pass line). */
export function classTestDraftFromExam(exam: ExamPlan, syllabus: string = ""): ClassTestDraft {
    const first = exam.papers[0];
    if (!first) return blankClassTestDraft({ classroomId: exam.classroomId ?? "" });
    const total = amount(first.maxMarks);
    const passMarks = amount(first.passingMarks);
    const startsAtDefault =
        total !== null && passMarks !== null && passMarks === defaultPassMarks(total);
    const temporary = exam.papers.find((paper) => paper.isTemporary);
    return {
        subjectId: first.classroomSubjectId,
        sectionIds: exam.papers.map((paper) => paper.classroomId),
        examDate: first.examDate ?? "",
        total: total === null ? "" : marksText(total),
        // Only a *different* teacher is a choice; the assigned one is "" (the default).
        takenBy: temporary?.takenByEmployeeId ?? "",
        familyNote: exam.familyNote ?? "",
        syllabus,
        passLine: {
            ...blankPassLine(),
            passBy: first.passMode === "grade" ? "grade" : "marks",
            passMarks: passMarks === null ? "" : marksText(passMarks),
            // A number that is not the 33% default is the teacher's own and must not
            // follow the total any more.
            passMarksEdited: !startsAtDefault,
            passingGrade: first.passingGrade ?? "",
            gradeMode: first.gradeMode ?? "na",
        },
    };
}

/** What stops the form from being saved (each sentence is shown to the teacher). */
export function classTestProblems(
    draft: ClassTestDraft,
    ladder: LadderRung[],
    options: { needsTaker?: boolean } = {},
): string[] {
    const found: string[] = [];
    if (!draft.subjectId) found.push("Choose the subject.");
    if (draft.sectionIds.length === 0) found.push("Choose at least one section.");
    if (!draft.examDate) found.push("Choose the date of the test.");
    const total = amount(draft.total);
    if (total === null || total <= 0) found.push("Enter the total marks.");
    else if (total > 9999.99) found.push("The total marks are too large.");
    if (options.needsTaker && !draft.takenBy) found.push("Pick who takes the test.");
    const issue = passLineIssue(draft.passLine, total, ladder);
    if (issue && total !== null && total > 0) found.push(issue);
    return found;
}

/** The body of `POST /exams/class-tests`. */
export function classTestCreateBody(
    draft: ClassTestDraft,
    options: { confirmDuplicate?: boolean } = {},
): Record<string, unknown> {
    return {
        classroom_subject_id: draft.subjectId,
        section_ids: draft.sectionIds,
        exam_date: draft.examDate,
        total_marks: amount(draft.total),
        taken_by_employee_id: draft.takenBy || null,
        family_note: draft.familyNote.trim() || null,
        syllabus_text: draft.syllabus.trim() || null,
        ...passLineBody(draft.passLine),
        confirm_duplicate: options.confirmDuplicate ?? false,
    };
}

function sameSet(a: string[], b: string[]): boolean {
    return a.length === b.length && [...a].sort().join("|") === [...b].sort().join("|");
}

/**
 * The body of `PATCH /exams/class-tests/{id}`: **only what changed**.
 *
 * The server decides what to tell families from what arrives, so a field that did not
 * change must not be sent (a resent date would not matter, but a resent `null` taker
 * would reset it). Returns `{}` when nothing changed.
 */
export function classTestPatch(
    draft: ClassTestDraft,
    exam: ExamPlan,
    options: { confirmDuplicate?: boolean; savedSyllabus?: string } = {},
): Record<string, unknown> {
    const before = classTestDraftFromExam(exam, options.savedSyllabus ?? "");
    const patch: Record<string, unknown> = {};
    if (draft.examDate !== before.examDate) patch.exam_date = draft.examDate;
    if (amount(draft.total) !== amount(before.total)) patch.total_marks = amount(draft.total);
    if (draft.takenBy !== before.takenBy) patch.taken_by_employee_id = draft.takenBy || null;
    if (draft.familyNote.trim() !== before.familyNote.trim()) {
        patch.family_note = draft.familyNote.trim() || null;
    }
    if (draft.syllabus.trim() !== before.syllabus.trim()) {
        patch.syllabus_text = draft.syllabus.trim() || null;
    }
    if (!sameSet(draft.sectionIds, before.sectionIds)) patch.section_ids = draft.sectionIds;

    const now = passLineBody(draft.passLine);
    const was = passLineBody(before.passLine);
    if (
        now.pass_mode !== was.pass_mode ||
        now.passing_marks !== was.passing_marks ||
        now.passing_grade !== was.passing_grade ||
        now.grade_mode !== was.grade_mode ||
        now.custom_min_percent !== null
    ) {
        Object.assign(patch, now);
    }
    if (Object.keys(patch).length > 0 && options.confirmDuplicate) {
        patch.confirm_duplicate = true;
    }
    return patch;
}

/** One test the server found for the same section, subject and date. */
export interface DuplicateTest {
    examId: string;
    name: string;
    examDate: string | null;
    subject: string;
    totalMarks: string;
    section: string;
    createdBy: string | null;
    status: string;
}

/**
 * The existing tests behind a `409 DUPLICATE_EXAM`, or `null` for any other error.
 *
 * Reads the error's `code` and its `detail.existing` (snake_case from the API).
 */
export function duplicatesFrom(error: unknown): DuplicateTest[] | null {
    const shape = error as { code?: unknown; detail?: { existing?: unknown } } | null;
    if (!shape || shape.code !== "DUPLICATE_EXAM") return null;
    const list = shape.detail?.existing;
    if (!Array.isArray(list)) return null;
    return list.map((item) => {
        const row = item as Record<string, unknown>;
        return {
            examId: String(row.exam_id ?? ""),
            name: String(row.name ?? ""),
            examDate: (row.exam_date as string | null) ?? null,
            subject: String(row.subject ?? ""),
            totalMarks: String(row.total_marks ?? ""),
            section: String(row.section ?? ""),
            createdBy: (row.created_by as string | null) ?? null,
            status: String(row.status ?? ""),
        };
    });
}

/** The status chip of a class test: Scheduled / Completed (marks uploaded) / Cancelled. */
export function classTestChip(exam: ExamPlan): {
    label: string;
    tone: "accent" | "green" | "red";
} {
    if (exam.status === "cancelled") return { label: "Cancelled", tone: "red" };
    const marked = exam.papers.some((paper) => paper.marksEntered > 0 || paper.publishedAt);
    return marked ? { label: "Completed", tone: "green" } : { label: "Scheduled", tone: "accent" };
}

/** `Class 9-A`, `Class 9-B` -> `9-A, 9-B` - the sections a test is for, short. */
export function sectionsText(exam: ExamPlan): string {
    return exam.papers
        .map((paper) => paper.section.replace(/^class\s+/i, ""))
        .filter(Boolean)
        .join(", ");
}

/** Does this test have a mark entered anywhere (so it can only be cancelled, not deleted)? */
export function hasMarks(exam: ExamPlan): boolean {
    return exam.papers.some((paper) => paper.marksEntered > 0);
}

/** This section's own paper of a class test (a test can cover several sections). */
export function paperOfSection(exam: ExamPlan, classroomId: string) {
    return exam.papers.find((paper) => paper.classroomId === classroomId) ?? exam.papers[0];
}

/** `yyyy-MM-dd` for the day on this machine - the one a test's date is compared with. */
export function todayText(now: Date = new Date()): string {
    const month = String(now.getMonth() + 1).padStart(2, "0");
    const day = String(now.getDate()).padStart(2, "0");
    return `${now.getFullYear()}-${month}-${day}`;
}

/**
 * The class tests of one section in two lists: **upcoming** (today or later, the nearest
 * first) and **past** (the date has gone by, the most recent first). A test with no date
 * yet is upcoming and comes last.
 */
export function splitByDate(
    exams: ExamPlan[],
    classroomId: string,
    today: string,
): { upcoming: ExamPlan[]; past: ExamPlan[] } {
    const dateOf = (exam: ExamPlan) => paperOfSection(exam, classroomId)?.examDate ?? "";
    const upcoming = exams.filter((exam) => !dateOf(exam) || dateOf(exam) >= today);
    const past = exams.filter((exam) => dateOf(exam) && dateOf(exam) < today);
    upcoming.sort((a, b) => (dateOf(a) || "9999-12-31").localeCompare(dateOf(b) || "9999-12-31"));
    past.sort((a, b) => dateOf(b).localeCompare(dateOf(a)));
    return { upcoming, past };
}
