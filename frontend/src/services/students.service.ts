import { api } from "@/lib/api/client";
import type { Student, ClassInfo } from "@/types";

export async function getStudents(skip = 0, limit = 100): Promise<Student[]> {
    return api.get<Student[]>(`/students?skip=${skip}&limit=${limit}`);
}

export async function getStudent(id: number): Promise<Student> {
    return api.get<Student>(`/students/${id}`);
}

export async function createStudent(data: Partial<Student>): Promise<Student> {
    return api.post<Student>("/students", data);
}

export async function getClasses(): Promise<ClassInfo[]> {
    return api.get<ClassInfo[]>("/academics/class-info");
}
