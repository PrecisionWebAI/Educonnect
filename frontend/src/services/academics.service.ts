import { api } from "@/lib/api/client";
import { toCamel } from "@/lib/api/case";
import type { ClassCatalog, ClassMatrixRow, DisputeRow, ExamOption, MarksEntry, ResultRow, SubjectRow } from "@/types";

export async function getMarks(): Promise<MarksEntry[]> {
    return api.get<MarksEntry[]>("/exams/marks");
}

/**
 * The marks of one class-section - what the Academics tab of a class shows.
 *
 * Only the students who sit in that section, one entry per student per exam, each
 * subject with the maximum the exam declared (`examsubject`).
 */
export async function getSectionMarks(sectionId: string): Promise<MarksEntry[]> {
    return api.get<MarksEntry[]>(`/classroom/sections/${sectionId}/marks`);
}

/**
 * Save the scores entered for one class-section.
 *
 * Upsert per (exam, student, subject), so pressing Save twice cannot double a
 * score. Returns how many rows were written.
 */
export async function saveSectionMarks(
    sectionId: string,
    examId: string,
    entries: { studentId: string; subjectId: string; obtained: number }[],
): Promise<number> {
    const result = await api.put<{ written: number }>(
        `/classroom/sections/${sectionId}/marks`,
        {
            exam_id: examId,
            entries: entries.map((entry) => ({
                student_id: entry.studentId,
                subject_id: entry.subjectId,
                marks_obtained: entry.obtained,
            })),
        },
    );
    return result?.written ?? 0;
}

export async function getResults(): Promise<ResultRow[]> {
    return api.get<ResultRow[]>("/exams/results");
}

/** School-wide results: pass rate / average / topper per class, exam by exam. */
export async function getSchoolResults(): Promise<ResultRow[]> {
    return api.get<ResultRow[]>("/classroom/results");
}

/** The exams a mark dispute can be filed against. */
export async function getExams(): Promise<ExamOption[]> {
    return api.get<ExamOption[]>("/classroom/exams");
}

/** Every mark challenge, newest first. */
export async function getSchoolDisputes(): Promise<DisputeRow[]> {
    return api.get<DisputeRow[]>("/classroom/disputes");
}

/** Log a challenge against one student's mark in one exam + subject. */
export async function raiseDispute(input: {
    studentId: string;
    examId: string;
    subjectId: string;
    reason: string;
}): Promise<DisputeRow> {
    return api.post<DisputeRow>("/classroom/disputes", {
        student_id: input.studentId,
        exam_id: input.examId,
        subject_id: input.subjectId,
        reason: input.reason,
    });
}

/** Move a challenge along: Open -> Under Review -> Resolved. */
export async function setDisputeStatus(id: string, status: string): Promise<DisputeRow> {
    return api.put<DisputeRow>(`/classroom/disputes/${id}`, { status });
}

export async function getDisputes(): Promise<DisputeRow[]> {
    return api.get<DisputeRow[]>("/exams/disputes");
}

export async function getClassMatrix(): Promise<ClassMatrixRow[]> {
    return api.get<ClassMatrixRow[]>("/academics/class-matrix");
}

/** Every class with its sections, plus the section names and stages in use.
 *
 * The single source for class/section dropdowns and filters: screens must not
 * ship a hardcoded class list, or a class added in the database would be
 * invisible to them.
 */
export async function getClassCatalog(): Promise<ClassCatalog> {
    return api.get<ClassCatalog>("/academics/catalog");
}

/** The school's subject vocabulary (interview "Subject" dropdown, assignments). */
export async function getSubjects(): Promise<SubjectRow[]> {
    return toCamel<SubjectRow[]>(await api.get("/academics/subjects"));
}
