import type { ExamPlan } from "@/types";
import { isSchoolExamType, typeLabel } from "./schoolExam.ts";
import { dayText } from "./view.ts";
import { titleCase } from "../format.ts";

/**
 * What a student or guardian reads about **upcoming** exams, as pure functions.
 *
 * The server already narrows `GET /exams` to their own children's sections and to what is
 * out (a class test once scheduled, a date sheet once the class teacher publishes it), so
 * this file only orders and words it. A cancelled test stays on the list - they were told
 * about it, so it must not just disappear - but sinks to the bottom.
 */

/** The earliest date on an exam, or `null` when none of its papers has one. */
export function firstDate(exam: ExamPlan): string | null {
    const dates = exam.papers
        .map((paper) => paper.examDate)
        .filter((date): date is string => Boolean(date))
        .sort();
    return dates[0] ?? null;
}

/** Soonest first; an undated exam after the dated ones; a cancelled one last of all. */
export function sortForFamily(exams: ExamPlan[]): ExamPlan[] {
    return [...exams].sort((a, b) => {
        const cancelled = Number(a.status === "cancelled") - Number(b.status === "cancelled");
        if (cancelled !== 0) return cancelled;
        const da = firstDate(a);
        const db = firstDate(b);
        if (da === db) return a.name.localeCompare(b.name);
        if (da === null) return 1;
        if (db === null) return -1;
        return da.localeCompare(db);
    });
}

/** What the card is called: "Class Test · Mathematics", or the exam's own name. */
export function familyTitle(exam: ExamPlan): string {
    if (exam.examType === "class_test") {
        const subject = exam.papers[0]?.subject;
        return subject ? `Class Test · ${subject}` : exam.name;
    }
    return exam.name;
}

/** The line under the title: the type and, for a class test, the day. */
export function familySubtitle(exam: ExamPlan): string {
    if (exam.examType === "class_test") return dayText(firstDate(exam));
    return isSchoolExamType(exam.examType) ? typeLabel(exam.examType) : titleCase(exam.examType);
}

/** Does this card carry syllabus buttons? (A school exam and a class test do.) */
export function hasSyllabusColumn(exam: ExamPlan): boolean {
    return isSchoolExamType(exam.examType) || exam.examType === "class_test";
}
