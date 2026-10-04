import { api } from "@/lib/api/client";
import type {
    ClassCatalog,
    ClassMatrixRow,
    DisputeRow,
    MarksEntry,
    ResultRow,
} from "@/types";

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

/** Every class with its sections, plus the section names and stages in use.
 *
 * The single source for class/section dropdowns and filters: screens must not
 * ship a hardcoded class list, or a class added in the database would be
 * invisible to them.
 */
export async function getClassCatalog(): Promise<ClassCatalog> {
    return api.get<ClassCatalog>("/academics/catalog");
}
