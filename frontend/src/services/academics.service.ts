import { api } from "@/lib/api/client";
import { toCamel } from "@/lib/api/case";
import type { ClassCatalog, MarksEntry, SubjectRow } from "@/types";

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
    entries: { studentId: string; subjectId: string; obtained: number }[],
): Promise<number> {
    const result = await api.put<{ written: number }>(`/classroom/sections/${sectionId}/marks`, {
        exam_id: examId,
        entries: entries.map((entry) => ({
            student_id: entry.studentId,
            subject_id: entry.subjectId,
            marks_obtained: entry.obtained,
        })),
    });
    return result?.written ?? 0;
}

export async function getClassCatalog(): Promise<ClassCatalog> {
    return api.get<ClassCatalog>("/academics/catalog");
}

/**
 * The school's subject vocabulary.
 *
 * Retired subjects are hidden by default; the Course manager asks for them with
 * `includeInactive`, because they still sit on the rows that already point at them.
 */
export async function getSubjects(includeInactive = false): Promise<SubjectRow[]> {
    const query = includeInactive ? "?include_inactive=true" : "";
    return toCamel<SubjectRow[]>(await api.get(`/academics/subjects${query}`));
}

/** Add a subject to the school's master list; the server mints a code when omitted. */
export async function createSubject(input: {
    name: string;
    code?: string | null;
}): Promise<SubjectRow> {
    return toCamel<SubjectRow>(await api.post("/academics/subjects", input));
}

/** Rename or retire a subject. Retiring leaves every row that points at it alone. */
export async function updateSubject(
    subjectId: string,
    input: { name?: string; isActive?: boolean },
): Promise<SubjectRow> {
    return toCamel<SubjectRow>(
        await api.patch(`/academics/subjects/${subjectId}`, {
            name: input.name,
            is_active: input.isActive,
        }),
    );
}
