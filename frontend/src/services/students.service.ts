import { api } from "@/lib/api/client";
import type {
    Student,
    ClassInfo,
    StudentDeleteResult,
    GuardianInput,
    GuardianLink,
    GuardianRemoveResult,
} from "@/types";

export async function getStudents(skip = 0, limit = 100): Promise<Student[]> {
    return api.get<Student[]>(`/students?skip=${skip}&limit=${limit}`);
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

export async function createStudent(data: Partial<Student>): Promise<Student> {
    return api.post<Student>("/students", data);
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

export async function getStudentGuardians(
    studentId: string,
): Promise<GuardianLink[]> {
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
    return api.put<GuardianLink>(
        `/students/${studentId}/guardians/${guardianId}`,
        data,
    );
}

/** Unlinks a guardian from this student. The person and their login stay. */
export async function removeStudentGuardian(
    studentId: string,
    guardianId: string,
): Promise<GuardianRemoveResult> {
    return api.delete<GuardianRemoveResult>(
        `/students/${studentId}/guardians/${guardianId}`,
    );
}
