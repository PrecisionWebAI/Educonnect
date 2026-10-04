import type { HiringCandidateRow, HiringStatus } from "@/types";
import { api } from "@/lib/api/client";
import { toCamel, toSnake } from "@/lib/api/case";

// ============================================================
// Operations ▸ Staff Hiring service — talks to `hiringcandidate` +
// `staffvacancy`.
//
//   GET  /hiring/candidates                 the pipeline (newest first)
//   POST /hiring/candidates                 add a candidate (server mints CAN-…)
//   PUT  /hiring/candidates/{id}/status     move a stage — Hired assigns EMP-…
//   GET  /hiring/vacancies                  the posts being hired for
//   GET  /hiring/summary                    stat-tile counts incl. open vacancies
//
// DESIGNATIONS / DEPARTMENTS are the option lists the New Candidate form offers
// (the same role the class list plays on the admission form) — the pipeline,
// the employee ids and the open-vacancy count all come from the API.
// ============================================================

export const DESIGNATIONS = [
    "Physics Teacher",
    "Mathematics Teacher",
    "English Teacher",
    "Computer Teacher",
    "Lab Assistant",
    "Sports Coach",
    "Front Office Executive",
    "Accountant",
];

export const DEPARTMENTS = [
    "Science",
    "Mathematics",
    "Languages",
    "Sports",
    "Administration",
    "Finance",
];

export interface HiringSummary {
    total: number;
    shortlisted: number;
    interviews: number;
    hired: number;
    openVacancies: number;
}

export interface StaffVacancyRow {
    id: number;
    role: string;
    department: string;
    openings: number;
    status: string;
}

export async function getHiringCandidates(): Promise<HiringCandidateRow[]> {
    return toCamel<HiringCandidateRow[]>(await api.get("/hiring/candidates"));
}

export async function createCandidate(input: {
    candidateName: string;
    role: string;
    department: string;
    qualification: string;
    experience: number;
}): Promise<HiringCandidateRow> {
    return toCamel<HiringCandidateRow>(
        await api.post("/hiring/candidates", toSnake(input)),
    );
}

/** Moves a candidate along the pipeline; the response carries the employee id. */
export async function updateCandidateStatus(
    id: number,
    status: HiringStatus,
    interviewOn?: string | null,
): Promise<HiringCandidateRow> {
    return toCamel<HiringCandidateRow>(
        await api.put(
            `/hiring/candidates/${id}/status`,
            toSnake({ status, interviewOn }),
        ),
    );
}

export async function getHiringSummary(): Promise<HiringSummary> {
    return toCamel<HiringSummary>(await api.get("/hiring/summary"));
}

export async function getStaffVacancies(): Promise<StaffVacancyRow[]> {
    return toCamel<StaffVacancyRow[]>(await api.get("/hiring/vacancies"));
}
