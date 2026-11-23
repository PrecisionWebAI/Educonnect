import { api } from "@/lib/api/client";
import { toCamel } from "@/lib/api/case";
import type { ClassCatalog, MarksEntry } from "@/types";

/**
 * Every mark the school holds - the school-wide views (the Academics screen and the
 * director's dashboard). Grouped per student per exam by the server, exactly like a
 * class-section's own marks.
 */
export async function getMarks(): Promise<MarksEntry[]> {
    return api.get<MarksEntry[]>("/classroom/marks");
}

/**
 * The marks of one class-section - what the Academics tab of a class shows.
 *
 * Only the students who sit in that section, one entry per student per exam, each
 * subject carrying the maximum of its own paper.
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
    entries: { studentId: string; classroomSubjectId: string; obtained: number }[],
): Promise<number> {
    const result = await api.put<{ written: number }>(`/classroom/sections/${sectionId}/marks`, {
        exam_id: examId,
        entries: entries.map((entry) => ({
            student_id: entry.studentId,
            classroom_subject_id: entry.classroomSubjectId,
            marks_obtained: entry.obtained,
        })),
    });
    return result?.written ?? 0;
}

export async function getClassCatalog(): Promise<ClassCatalog> {
    return api.get<ClassCatalog>("/academics/catalog");
}
