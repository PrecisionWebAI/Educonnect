import { api } from "@/lib/api/client";
import type { ClassMatrixRow, DisputeRow, MarksEntry, ResultRow } from "@/types";

export async function getMarks(): Promise<MarksEntry[]> {
    return api.get<MarksEntry[]>("/exams/marks");
}

export async function getResults(): Promise<ResultRow[]> {
    return api.get<ResultRow[]>("/exams/results");
}

export async function getDisputes(): Promise<DisputeRow[]> {
    return api.get<DisputeRow[]>("/exams/disputes");
}

export async function getClassMatrix(): Promise<ClassMatrixRow[]> {
    return api.get<ClassMatrixRow[]>("/academics/class-matrix");
}
