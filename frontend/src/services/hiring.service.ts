import type { HiringCandidateRow } from "@/types";

// ============================================================
// Operations ▸ Staff Hiring service.
//
// Hard-coded for this phase: the schema has no job/application table
// yet, so once it lands this becomes
// `api.get<HiringCandidateRow[]>("/hiring/candidates")`.
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

const CANDIDATES: HiringCandidateRow[] = [
    {
        id: 1,
        candidateNo: "CAN-2026-0031",
        empId: "",
        candidateName: "Rohan Deshmukh",
        role: "Physics Teacher",
        department: "Science",
        qualification: "M.Sc. Physics, B.Ed.",
        experience: 6,
        appliedOn: "2026-09-14",
        interviewOn: "2026-09-28",
        status: "Interview",
    },
    {
        id: 2,
        candidateNo: "CAN-2026-0032",
        empId: "",
        candidateName: "Sneha Kulkarni",
        role: "Mathematics Teacher",
        department: "Mathematics",
        qualification: "M.Sc. Maths, B.Ed.",
        experience: 4,
        appliedOn: "2026-09-15",
        interviewOn: "2026-09-29",
        status: "Shortlisted",
    },
    {
        id: 3,
        candidateNo: "CAN-2026-0033",
        empId: "",
        candidateName: "Imran Sheikh",
        role: "Lab Assistant",
        department: "Science",
        qualification: "B.Sc. Chemistry",
        experience: 2,
        appliedOn: "2026-09-17",
        interviewOn: "—",
        status: "Resume",
    },
    {
        id: 4,
        candidateNo: "CAN-2026-0034",
        empId: "EMP-0036",
        candidateName: "Priya Menon",
        role: "English Teacher",
        department: "Languages",
        qualification: "M.A. English, B.Ed.",
        experience: 8,
        appliedOn: "2026-09-10",
        interviewOn: "2026-09-22",
        status: "Hired",
    },
    {
        id: 5,
        candidateNo: "CAN-2026-0035",
        empId: "",
        candidateName: "Deepak Choudhary",
        role: "Sports Coach",
        department: "Sports",
        qualification: "B.P.Ed.",
        experience: 5,
        appliedOn: "2026-09-12",
        interviewOn: "2026-09-24",
        status: "Rejected",
    },
];

/** Open vacancies the school is actively hiring for (seed figure). */
export const OPEN_VACANCIES = 3;

/** First employee number handed out on the next hire (seed figure). */
export const NEXT_EMP_NUMBER = 37;

/** Formats an employee id: 37 -> "EMP-0037". */
export function formatEmpId(n: number): string {
    return `EMP-${String(n).padStart(4, "0")}`;
}

export async function getHiringCandidates(): Promise<HiringCandidateRow[]> {
    return CANDIDATES;
}
