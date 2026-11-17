import type { ExamPaperPlan, ExamPlan, ExamResults, PaperMarkRow } from "@/types";

/**
 * The Exams tab's rules, as **pure functions**.
 *
 * Same reason as `lib/attendance/view.ts` and `lib/course/view.ts`: the repository
 * has no component-test stack, so the parts worth testing - the schedule form's
 * validation, the marks sheet's diff and its publish gate, the grade and rank
 * wording - live here and are covered by `node --test` instead of a browser.
 *
 * Nothing here decides **whether** a caller may do something. The server answers
 * that (`canEdit` per paper, `403`/`409` on the write) and sends the flags down;
 * these functions only turn those answers into words and payloads.
 */

/* ---------- decimals, as the API writes them ---------- */

/**
 * A `numeric` from the API, as a number.
 *
 * Pydantic serialises `Decimal` to JSON as a **string** (`"72.50"`), so a field
 * that is a number in the database arrives as text. Everything that does
 * arithmetic or validation goes through here, and anything blank, `null` or
 * unparseable reads as "no figure" rather than `NaN` leaking into a sum.
 */
export function amount(value: string | number | null | undefined): number | null {
    if (value === null || value === undefined) return null;
    if (typeof value === "string" && value.trim() === "") return null;
    const parsed = typeof value === "number" ? value : Number(value);
    return Number.isFinite(parsed) ? parsed : null;
}

/** `"72.50"` -> `"72.5"`, `null` -> `"—"` - a figure as a person reads it. */
export function figureText(value: string | number | null | undefined): string {
    const parsed = amount(value);
    if (parsed === null) return "—";
    return String(Math.round(parsed * 100) / 100);
}

/** `"82.5"` -> `"82.5%"`, `null` -> `"—"`. */
export function percentText(value: string | number | null | undefined): string {
    const parsed = amount(value);
    if (parsed === null) return "—";
    return `${Math.round(parsed * 100) / 100}%`;
}

/* ---------- the exams list ---------- */

/** One class sits the exam, or the whole school does. */
export type ExamScopeWord = "class" | "school";

/**
 * The two sub-tabs' rows.
 *
 * A school-wide exam has papers for several classes, so it is **not** "this
 * section's exam" even when this section sits one of its papers - which is why
 * the split is on the exam's own scope rather than on its class.
 */
export function splitByScope(exams: ExamPlan[]): Record<ExamScopeWord, ExamPlan[]> {
    return {
        class: exams.filter((exam) => exam.scope !== "school"),
        school: exams.filter((exam) => exam.scope === "school"),
    };
}

export function scopeLabel(scope: string): string {
    return scope === "school" ? "School exam" : "Class exam";
}

/**
 * A class-section's own exams.
 *
 * The read is `GET /exams` without a filter - the server has already narrowed it
 * to what this caller may see (a teacher: the exams they hold a subject in; the
 * office: all of them) - so the page still has to pick out the ones that belong
 * to the section in front of it: its own room, or a class-level exam that the
 * whole class sits. A school-wide exam is never "this section's" exam, even when
 * this section sits one of its papers.
 */
export function forSection(
    exams: ExamPlan[],
    ids: { classroomId: string; classId?: string | null },
): ExamPlan[] {
    return exams.filter(
        (exam) =>
            exam.scope !== "school" &&
            (exam.classroomId === ids.classroomId ||
                (exam.classroomId === null && !!ids.classId && exam.classId === ids.classId)),
    );
}

export type ChipTone = "green" | "amber" | "red" | "muted" | "accent" | "violet" | "teal";

/** The status chip: the database's word, said the way a school says it. */
export function examStatusChip(status: string): { label: string; tone: ChipTone } {
    switch (status) {
        case "draft":
            // A draft is not on the date sheet yet - nobody has been told.
            return { label: "Draft", tone: "muted" };
        case "scheduled":
            return { label: "Scheduled", tone: "accent" };
        case "marks_entry":
            return { label: "Marks entry", tone: "amber" };
        case "done":
            return { label: "Sat", tone: "violet" };
        case "published":
            return { label: "Published", tone: "green" };
        default:
            return { label: status, tone: "muted" };
    }
}

/* ---------- dates and times ---------- */

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/**
 * `"2026-03-12"` -> `"12 Mar"`.
 *
 * Done by hand rather than through `toLocaleDateString`: the tab must print the
 * same words in every browser and in `node --test`, and a locale that spells the
 * month differently (or writes the day first) would make the date sheet disagree
 * with the tests.
 */
export function dayText(value: string | null | undefined): string {
    if (!value) return "—";
    const [year, month, day] = value.split("-").map((part) => Number(part));
    if (!year || !month || !day || month < 1 || month > 12) return "—";
    return `${day} ${MONTHS[month - 1]}`;
}

/** `"09:00:00"` -> `"09:00"`. */
export function clockText(value: string | null | undefined): string {
    if (!value) return "";
    const [hour, minute] = value.split(":");
    if (hour === undefined || minute === undefined) return "";
    return `${hour.padStart(2, "0")}:${minute.padStart(2, "0")}`;
}

/** The exam's span: `"12 Mar – 20 Mar"`, one day when it is one day, `"Dates not set"`. */
export function dateRangeText(start: string | null, end: string | null): string {
    if (!start && !end) return "Dates not set";
    if (!start) return `Until ${dayText(end)}`;
    if (!end || end === start) return dayText(start);
    return `${dayText(start)} – ${dayText(end)}`;
}

/** A paper's own line: `"12 Mar · 09:00–12:00 · Room 4"`. */
export function paperWhenText(paper: ExamPaperPlan): string {
    const parts: string[] = [];
    parts.push(paper.examDate ? dayText(paper.examDate) : "Date to be set");
    const from = clockText(paper.startTime);
    const to = clockText(paper.endTime);
    if (from && to) parts.push(`${from}–${to}`);
    else if (from) parts.push(`from ${from}`);
    if (paper.room) parts.push(`Room ${paper.room}`);
    return parts.join(" · ");
}

/**
 * How far a paper's marks have got.
 *
 * `cohort` is how many children sit it (0 when this caller cannot know - a
 * school exam's other classes). "Published" wins over any count: once the marks
 * are out, the number entered is history, not progress.
 */
export function paperProgress(
    paper: ExamPaperPlan,
    cohort: number,
): { label: string; tone: ChipTone } {
    if (paper.publishedAt) return { label: "Published", tone: "green" };
    if (paper.marksEntered === 0) return { label: "Not entered", tone: "muted" };
    const count = cohort > 0 ? `${paper.marksEntered}/${cohort}` : `${paper.marksEntered}`;
    if (cohort > 0 && paper.marksEntered >= cohort) return { label: `${count} in`, tone: "accent" };
    return { label: `${count} in`, tone: "amber" };
}

/* ---------- the schedule form ---------- */

/** One row of the date sheet while it is being written. */
export interface PaperDraft {
    /** Stable React key; never sent. */
    key: string;
    subjectId: string;
    /** A school exam's paper names its own class; a class exam inherits the page's. */
    classId: string;
    /** `""` means "not chosen yet". */
    examDate: string;
    startTime: string;
    endTime: string;
    maxMarks: string;
    passingMarks: string;
    room: string;
    note: string;
    chapterIds: string[];
}

export interface ExamDraft {
    name: string;
    term: string;
    examType: string;
    scope: ExamScopeWord;
    startDate: string;
    endDate: string;
    note: string;
    papers: PaperDraft[];
}

let draftSequence = 0;

/** A row with the school's usual shape filled in (out of 100, passing 33). */
export function blankPaper(overrides: Partial<PaperDraft> = {}): PaperDraft {
    draftSequence += 1;
    return {
        key: `paper-${draftSequence}`,
        subjectId: "",
        classId: "",
        examDate: "",
        startTime: "",
        endTime: "",
        maxMarks: "100",
        passingMarks: "33",
        room: "",
        note: "",
        chapterIds: [],
        ...overrides,
    };
}

export function blankDraft(scope: ExamScopeWord, overrides: Partial<ExamDraft> = {}): ExamDraft {
    return {
        name: "",
        term: "",
        examType: "",
        scope,
        startDate: "",
        endDate: "",
        note: "",
        papers: [],
        ...overrides,
    };
}

/**
 * A row nobody has touched.
 *
 * The form opens with one empty row so the shape is obvious; saving must not
 * send it, or the server would answer "that paper needs a class" for a row the
 * person never filled in.
 */
export function isBlankPaper(paper: PaperDraft): boolean {
    return (
        !paper.subjectId &&
        !paper.examDate &&
        !paper.startTime &&
        !paper.endTime &&
        !paper.room &&
        !paper.note &&
        paper.chapterIds.length === 0
    );
}

/** The rows that would actually be sent. */
export function draftPapers(draft: ExamDraft): PaperDraft[] {
    return draft.papers.filter((paper) => !isBlankPaper(paper));
}

/**
 * Everything wrong with the form, in the words the person can act on.
 *
 * Empty means "send it". The rules are the backend's own (`max_marks` is the
 * only maximum, so passing cannot exceed it; a paper needs a date; a school
 * exam's paper needs its class), checked here so the button explains itself
 * before a round trip answers `422`.
 */
export function draftProblems(draft: ExamDraft): string[] {
    const problems: string[] = [];

    if (!draft.name.trim()) problems.push("Give the exam a name.");

    const rows = draftPapers(draft);
    if (rows.length === 0) problems.push("Add at least one paper to the date sheet.");

    if (draft.startDate && draft.endDate && draft.endDate < draft.startDate) {
        problems.push("The exam cannot end before it starts.");
    }

    const seen = new Set<string>();
    for (const row of rows) {
        if (!row.subjectId) problems.push("Every paper needs a subject.");
        if (draft.scope === "school" && !row.classId) {
            problems.push("A school exam's paper needs its class.");
        }
        if (!row.examDate) problems.push("Every paper needs a date.");

        const max = amount(row.maxMarks);
        if (max === null || max <= 0) {
            problems.push("A paper's maximum must be more than zero.");
        }
        const passing = amount(row.passingMarks);
        if (passing !== null) {
            if (passing < 0) problems.push("Passing marks cannot be negative.");
            else if (max !== null && passing > max) {
                problems.push("Passing marks cannot exceed the paper's maximum.");
            }
        }

        if (row.startTime && row.endTime && row.endTime <= row.startTime) {
            problems.push("A paper cannot end before it starts.");
        }

        if (row.subjectId) {
            const key = `${row.classId || draft.scope}|${row.subjectId}`;
            if (seen.has(key)) problems.push("That class already has a paper in this subject.");
            seen.add(key);
        }
    }

    return [...new Set(problems)];
}

/* ---------- the marks sheet ---------- */

/** One child's line while the sheet is being filled in. */
export interface MarkEdit {
    studentId: string;
    name: string;
    admissionNumber: string | null;
    section: string | null;
    /** What the input holds - text, because a half-typed "7" is not a score yet. */
    score: string;
    absent: boolean;
    /** What the server last confirmed (the row as it was read), for the diff. */
    saved: PaperMarkRow | null;
}

function scoreOf(row: PaperMarkRow | null): string {
    if (!row || row.absent) return "";
    const parsed = amount(row.marksObtained);
    return parsed === null ? "" : String(parsed);
}

/** The sheet's rows from the server's rows: a saved score opens pre-filled. */
export function editFromRows(rows: PaperMarkRow[]): MarkEdit[] {
    return rows.map((row) => ({
        studentId: row.studentId,
        name: row.name,
        admissionNumber: row.admissionNumber,
        section: row.section,
        score: scoreOf(row),
        absent: row.absent,
        saved: row,
    }));
}

/** True when this line differs from what the server holds. */
export function rowChanged(edit: MarkEdit): boolean {
    const saved = edit.saved;
    const wasAbsent = saved?.absent ?? false;
    if (edit.absent !== wasAbsent) return true;
    const wasScore = amount(saved?.marksObtained ?? null);
    const nowScore = edit.absent ? null : amount(edit.score);
    if (wasScore === null && nowScore === null) return false;
    if (wasScore === null || nowScore === null) return true;
    return Math.abs(wasScore - nowScore) > 0.0001;
}

/** The lines to send - only the ones that changed, so Save is a diff. */
export function changedEdits(edits: MarkEdit[]): MarkEdit[] {
    return edits.filter(rowChanged);
}

/**
 * What is wrong with one score box, or `null` when it is fine.
 *
 * Blank is **not** a problem: an unmarked child is a state the sheet allows (the
 * score is simply absent), and the publish gate is what insists on a decision.
 */
export function scoreProblem(score: string, maxMarks: string | number): string | null {
    const text = score.trim();
    if (text === "") return null;
    const value = Number(text);
    if (!Number.isFinite(value)) return "Enter a number.";
    if (value < 0) return "A score cannot be negative.";
    const ceiling = amount(maxMarks);
    if (ceiling !== null && value > ceiling) return `The maximum is ${figureText(maxMarks)}.`;
    return null;
}

/** The body `POST /exams/papers/{id}/marks` takes - an absence carries no score. */
export interface MarkEntryPayload {
    student_id: string;
    marks_obtained: number | null;
    absent: boolean;
}

export function marksEntries(edits: MarkEdit[]): MarkEntryPayload[] {
    return changedEdits(edits).map((edit) => ({
        student_id: edit.studentId,
        marks_obtained: edit.absent ? null : amount(edit.score),
        absent: edit.absent,
    }));
}

export type Gate = { allowed: boolean; reason: string | null };

/**
 * May these marks be published, and if not, why not?
 *
 * The server's own rule: at least one mark must exist on the paper, a published
 * paper stays published (`409`), and only its teacher or the office may publish.
 * It does **not** demand a score for every child - a school often publishes a
 * paper while one child is still being looked into, and the server leaves that
 * call to the school - so this gate does not invent a stricter rule either.
 */
export function publishGate({
    paper,
    edits,
    canEdit,
}: {
    paper: ExamPaperPlan;
    edits: MarkEdit[];
    canEdit: boolean;
}): Gate {
    if (!canEdit) {
        return { allowed: false, reason: "Only the paper's teacher or the office can publish." };
    }
    if (paper.publishedAt) {
        return { allowed: false, reason: "These marks are already published." };
    }
    const bad = edits.find((edit) => scoreProblem(edit.score, paper.maxMarks) !== null);
    if (bad) {
        return {
            allowed: false,
            reason: `${bad.name}: ${scoreProblem(bad.score, paper.maxMarks)}`,
        };
    }
    const marked = edits.filter((edit) => edit.absent || amount(edit.score) !== null);
    if (marked.length === 0) {
        return { allowed: false, reason: "Enter at least one mark before publishing." };
    }
    return { allowed: true, reason: null };
}

/** The sheet's said-out-loud counts: how many are marked, absent, still blank. */
export function sheetCounts(edits: MarkEdit[]): { marked: number; absent: number; blank: number } {
    let marked = 0;
    let absent = 0;
    let blank = 0;
    for (const edit of edits) {
        if (edit.absent) absent += 1;
        else if (amount(edit.score) !== null) marked += 1;
        else blank += 1;
    }
    return { marked, absent, blank };
}

/* ---------- results ---------- */

/**
 * A rank, as the report card prints it.
 *
 * `enabled` is the school's `rank_display` setting: when it is off the backend
 * sends no ranks at all, and a dash is the honest answer - not "1".
 */
export function rankText(rank: number | null, enabled: boolean): string {
    if (!enabled || rank === null) return "—";
    return `#${rank}`;
}

/** How a grade reads at a glance: A green, F red, nothing in between invented. */
export function gradeTone(grade: string | null): ChipTone {
    if (!grade) return "muted";
    const head = grade.trim().charAt(0).toUpperCase();
    if (head === "A") return "green";
    if (head === "B" || head === "C") return "accent";
    if (head === "D" || head === "E") return "amber";
    if (head === "F") return "red";
    return "muted";
}

/**
 * The principal's to-do list: the papers in `unpublished`, as subject names.
 *
 * Drawn from `results.papers`, so a paper that vanished mid-read simply does not
 * appear instead of printing an id.
 */
export function unpublishedSubjects(results: ExamResults): string[] {
    const pending = new Set(results.unpublished);
    return results.papers
        .filter((paper) => pending.has(paper.paperId))
        .map((paper) => paper.subject);
}

/** `"All passed"` / `"Failed a paper"` / `"—"` when nothing was sat. */
export function passText(row: { passedAll: boolean | null; absentCount: number }): string {
    if (row.passedAll === null) return "—";
    if (row.passedAll) return row.absentCount > 0 ? "Passed, absent in some" : "All passed";
    return "Failed a paper";
}

/** One child's subject cell: `"72.5/100"`, `"Absent"`, or `"—"`. */
export function markCellText(mark: {
    obtained: string | number | null;
    absent: boolean;
    maxMarks: string | number;
}): string {
    if (mark.absent) return "Absent";
    const score = amount(mark.obtained);
    if (score === null) return "—";
    return `${figureText(mark.obtained)}/${figureText(mark.maxMarks)}`;
}

/* ---------- body: from a saved exam back into the form ---------- */

/**
 * A saved exam, as the form that made it.
 *
 * Times are cut to `HH:mm` because `<input type="time">` refuses the seconds the
 * database keeps, and a value the input cannot show would silently blank itself
 * the first time somebody touched the field.
 */
export function draftFromExam(exam: ExamPlan): ExamDraft {
    return {
        name: exam.name,
        term: exam.term ?? "",
        examType: exam.examType ?? "",
        scope: exam.scope === "school" ? "school" : "class",
        startDate: exam.startDate ?? "",
        endDate: exam.endDate ?? "",
        note: exam.note ?? "",
        papers: exam.papers.map((paper) =>
            blankPaper({
                subjectId: paper.subjectId,
                classId: paper.classId,
                examDate: paper.examDate ?? "",
                startTime: clockText(paper.startTime),
                endTime: clockText(paper.endTime),
                maxMarks: figureText(paper.maxMarks),
                passingMarks: paper.passingMarks === null ? "" : figureText(paper.passingMarks),
                room: paper.room ?? "",
                note: paper.note ?? "",
                chapterIds: paper.chapterIds,
            }),
        ),
    };
}

/* ---------- the form, as the API reads it ---------- */

/** A date or `null` - the backend takes `null` for "not set", not `""`. */
function dateOrNull(value: string): string | null {
    return value.trim() === "" ? null : value.trim();
}

function textOrNull(value: string): string | null {
    const text = value.trim();
    return text === "" ? null : text;
}

/** One paper row of `POST /exams` / `PATCH /exams/{id}`, in the API's words. */
export interface PaperBody {
    subject_id: string;
    class_id: string | null;
    exam_date: string | null;
    start_time: string | null;
    end_time: string | null;
    max_marks: number;
    passing_marks: number | null;
    room: string | null;
    note: string | null;
    chapter_ids: string[];
}

/** The body `POST /exams` and `PATCH /exams/{id}` take. */
export interface ExamBody {
    name: string;
    term: string | null;
    exam_type: string | null;
    scope: ExamScopeWord;
    class_id: string | null;
    classroom_id: string | null;
    start_date: string | null;
    end_date: string | null;
    note: string | null;
    papers: PaperBody[];
}

/**
 * The form, as the API reads it.
 *
 * Two rules live here rather than in the component:
 *
 * * a **class** exam carries the page's `class_id` / `classroom_id`, so every paper
 *   inherits them and the backend never has to guess which room sits it;
 * * a **school** exam carries no class of its own - each row names its own - which
 *   is exactly what `exam_paper.class_id` is for.
 */
export function draftBody(
    draft: ExamDraft,
    ids: { classId?: string | null; classroomId?: string | null } = {},
): ExamBody {
    const school = draft.scope === "school";
    return {
        name: draft.name.trim(),
        term: textOrNull(draft.term),
        exam_type: textOrNull(draft.examType),
        scope: draft.scope,
        class_id: school ? null : (ids.classId ?? null),
        classroom_id: school ? null : (ids.classroomId ?? null),
        start_date: dateOrNull(draft.startDate),
        end_date: dateOrNull(draft.endDate),
        note: textOrNull(draft.note),
        papers: draftPapers(draft).map((row) => ({
            subject_id: row.subjectId,
            class_id: school ? textOrNull(row.classId) : (ids.classId ?? null),
            exam_date: dateOrNull(row.examDate),
            start_time: dateOrNull(row.startTime),
            end_time: dateOrNull(row.endTime),
            max_marks: amount(row.maxMarks) ?? 0,
            passing_marks: amount(row.passingMarks),
            room: textOrNull(row.room),
            note: textOrNull(row.note),
            chapter_ids: row.chapterIds,
        })),
    };
}
