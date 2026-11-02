import type { HiringCandidateRow, HiringStatus, LoginCredential } from "@/types";
import { api } from "@/lib/api/client";
import { toCamel, toSnake } from "@/lib/api/case";

// ============================================================
// Operations ▸ Staff Hiring service — talks to `hiringcandidate`.
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
}

export async function getHiringCandidates(): Promise<HiringCandidateRow[]> {
    return toCamel<HiringCandidateRow[]>(await api.get("/hiring/candidates"));
}

/** The interview-scheduling form payload. */
export interface CandidateInput {
    candidateName: string;
    department: string;
    /** role codename applied for (teacher, accountant, ...) */
    appliedFor: string | null;
    /** human label shown in the pipeline (legacy `role`) */
    role: string | null;
    qualification: string;
    experience: number;
    phone: string;
    email: string;
    subjectId: number | null;
    subjectName: string | null;
    interviewAt: string | null;
    interviewNote: string;
}

export async function createCandidate(input: CandidateInput): Promise<HiringCandidateRow> {
    return toCamel<HiringCandidateRow>(await api.post("/hiring/candidates", toSnake(input)));
}

/** The Hired response: the candidate plus the one-time login credentials. */
export interface HiringCandidateHireResult extends HiringCandidateRow {
    loginEmail: string | null;
    credentials: LoginCredential[] | null;
}

/** Moves a candidate along the pipeline; the response carries the employee id. */
export async function updateCandidateStatus(
    id: number,
    status: HiringStatus,
    interviewOn?: string | null,
): Promise<HiringCandidateRow> {
    return toCamel<HiringCandidateRow>(
        await api.put(`/hiring/candidates/${id}/status`, toSnake({ status, interviewOn })),
    );
}

/** Set / change a candidate's interview date+time. */
export async function scheduleCandidateInterview(
    id: number,
    interviewAt: string | null,
    interviewNote?: string,
): Promise<HiringCandidateRow> {
    return toCamel<HiringCandidateRow>(
        await api.put(`/hiring/candidates/${id}/interview`, toSnake({ interviewAt, interviewNote })),
    );
}

/** The gated Hired decision: the operator must type `Hired`. */
export async function hireCandidate(id: number): Promise<HiringCandidateHireResult> {
    return toCamel<HiringCandidateHireResult>(
        await api.put(`/hiring/candidates/${id}/hire`, { confirm_text: "Hired" }),
    );
}

/** Attaches a resume file to a candidate. */
export async function uploadCandidateResume(id: number, file: File): Promise<HiringCandidateRow> {
    const form = new FormData();
    form.append("file", file);
    return toCamel<HiringCandidateRow>(await api.postForm(`/hiring/candidates/${id}/resume`, form));
}

export async function getHiringSummary(): Promise<HiringSummary> {
    return toCamel<HiringSummary>(await api.get("/hiring/summary"));
}
