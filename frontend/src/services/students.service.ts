import { api } from "@/lib/api/client";
import type {
    Student,
    ClassInfo,
    StudentDeleteResult,
    StudentLifecycleResult,
    GuardianInput,
    GuardianLink,
    GuardianRemoveResult,
    PromotionResult,
    DepromotePreview,
} from "@/types";

/**
 * One page of the directory, as the **server** filtered it.
 *
 * `q` matches name, admission number and guardian name; `classroomId` is one
 * class-section, `classId` a whole class, `status` the roll. `total` comes from the
 * `X-Total-Count` header - the count of everything the filters matched, which is what
 * the pagination needs when only one page was sent.
 */
export interface StudentPageQuery {
    q?: string;
    classroomId?: string;
    classId?: string;
    status?: "Active" | "Inactive";
    skip?: number;
    limit?: number;
}

export async function getStudents(skip = 0, limit = 100): Promise<Student[]> {
    return api.get<Student[]>(`/students?skip=${skip}&limit=${limit}`);
}

export async function getStudentsPage(
    query: StudentPageQuery = {},
): Promise<{ items: Student[]; total: number | null }> {
    const params = new URLSearchParams();
    if (query.q?.trim()) params.set("q", query.q.trim());
    if (query.classroomId) params.set("classroom_id", query.classroomId);
    if (query.classId) params.set("class_id", query.classId);
    if (query.status) params.set("status", query.status);
    params.set("skip", String(query.skip ?? 0));
    if (query.limit !== undefined) params.set("limit", String(query.limit));

    const { data, total } = await api.getWithTotal<Student[]>(`/students?${params}`);
    return { items: data, total };
}

export async function getStudent(id: string): Promise<Student> {
    return api.get<Student>(`/students/${id}`);
}

/**
 * Delete a student for good.
 *
 * The class-section goes with the last student in it - the response names it, so
 * the screen can tell the operator what was removed.
 */
export async function deleteStudent(id: string): Promise<StudentDeleteResult> {
    return api.delete<StudentDeleteResult>(`/students/${id}`);
}

export async function createStudent(data: StudentEditInput): Promise<Student> {
    return api.post<Student>("/students", data);
}

/**
 * Edit a student. Only the fields sent are written (`exclude_unset` on the server),
 * and `classroomId` moves the child through the one placement writer, which keeps
 * `student.classroom_id` and this session's `enrollment` row in step.
 */
export interface StudentEditInput {
    fullName?: string;
    gender?: string;
    dateOfBirth?: string;
    notes?: string;
    classroomId?: string | null;
}

export async function updateStudent(id: string, data: StudentEditInput): Promise<Student> {
    return api.patch<Student>(`/students/${id}`, data);
}

/** Take the child off the roll (nothing is deleted; the login stays). */
export async function deactivateStudent(id: string): Promise<StudentLifecycleResult> {
    return api.post<StudentLifecycleResult>(`/students/${id}/deactivate`, {});
}

/** Put the child back on the roll, with everything that was already theirs. */
export async function reactivateStudent(id: string): Promise<StudentLifecycleResult> {
    return api.post<StudentLifecycleResult>(`/students/${id}/reactivate`, {});
}

export async function getClasses(): Promise<ClassInfo[]> {
    return api.get<ClassInfo[]>("/academics/class-info");
}

// ---------------------------------------------------------------------------
// Guardians of a student (the card on their screen)
//
// One guardian is one **person**, shared by every child of that family, so adding a
// contact the school already has links that person instead of creating a second row -
// and the login comes back with its first-time password only when it was just created.
// ---------------------------------------------------------------------------

export async function getStudentGuardians(studentId: string): Promise<GuardianLink[]> {
    return api.get<GuardianLink[]>(`/students/${studentId}/guardians`);
}

export async function addStudentGuardian(
    studentId: string,
    data: GuardianInput,
): Promise<GuardianLink> {
    return api.post<GuardianLink>(`/students/${studentId}/guardians`, data);
}

export async function updateStudentGuardian(
    studentId: string,
    guardianId: string,
    data: GuardianInput,
): Promise<GuardianLink> {
    return api.put<GuardianLink>(`/students/${studentId}/guardians/${guardianId}`, data);
}

/** Unlinks a guardian from this student. The person and their login stay. */
export async function removeStudentGuardian(
    studentId: string,
    guardianId: string,
): Promise<GuardianRemoveResult> {
    return api.delete<GuardianRemoveResult>(`/students/${studentId}/guardians/${guardianId}`);
}

// ---- Promotion (principal and admin only; each call is one transaction) -------------------

const PROMOTION = "/promotions";

/** New record in the next year, in `targetClassId` (omit for "the next class"). */
export async function promoteStudents(
    studentIds: string[],
    targetClassId?: string,
    targetSection?: string,
): Promise<PromotionResult> {
    return api.post<PromotionResult>(`${PROMOTION}/promote`, {
        student_ids: studentIds,
        target_class_id: targetClassId ?? null,
        target_section: targetSection ?? null,
    });
}

/** New record in the next year, in the same class-section. */
export async function retainStudents(studentIds: string[]): Promise<PromotionResult> {
    return api.post<PromotionResult>(`${PROMOTION}/retain`, { student_ids: studentIds });
}

/** Highest class only: the current record becomes Completed. */
export async function completeStudents(studentIds: string[]): Promise<PromotionResult> {
    return api.post<PromotionResult>(`${PROMOTION}/complete`, { student_ids: studentIds });
}

/** What de-promoting would delete; nothing is changed. */
export async function previewDepromote(studentIds: string[]): Promise<DepromotePreview> {
    return api.post<DepromotePreview>(`${PROMOTION}/depromote/preview`, {
        student_ids: studentIds,
    });
}

/** Undo promote / retain / complete. Deletes only with `confirm: true`. */
export async function depromoteStudents(
    studentIds: string[],
    confirm: boolean,
): Promise<PromotionResult> {
    return api.post<PromotionResult>(`${PROMOTION}/depromote`, {
        student_ids: studentIds,
        confirm,
    });
}

/** Move students one class down (the class they came from) into a section "A" - "J". */
export async function demoteStudents(
    studentIds: string[],
    targetSection: string,
): Promise<PromotionResult> {
    return api.post<PromotionResult>(`${PROMOTION}/demote`, {
        student_ids: studentIds,
        target_section: targetSection,
    });
}

/** What undoing the last promote / retain / move down would permanently delete. */
export async function previewUndo(studentIds: string[]): Promise<DepromotePreview> {
    return api.post<DepromotePreview>(`${PROMOTION}/undo/preview`, { student_ids: studentIds });
}

/** Undo the last promote, retain or move down. Deletes data only with `confirm: true`. */
export async function undoStudents(
    studentIds: string[],
    confirm: boolean,
): Promise<PromotionResult> {
    return api.post<PromotionResult>(`${PROMOTION}/undo`, {
        student_ids: studentIds,
        confirm,
    });
}
