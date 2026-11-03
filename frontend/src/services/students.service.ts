import { api } from "@/lib/api/client";
import type { Student, ClassInfo, StudentDeleteResult } from "@/types";

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
