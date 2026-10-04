"use client";

import { useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
    DESIGNATIONS,
    DEPARTMENTS,
    NEXT_EMP_NUMBER,
    OPEN_VACANCIES,
    formatEmpId,
    getHiringCandidates,
} from "@/services";
import { useApiQuery } from "@/lib/api/use-api-query";
import { isoInDays, todayISO } from "@/lib/format";
import type { HiringCandidateRow, HiringStatus } from "@/types";

// Operations ▸ Staff Hiring — candidate pipeline state for the hiring page.

export const HIRING_KEY = ["operations", "hiring"];

export type HiringTab = "Pipeline" | "Hired";

/** Pipeline stages offered by the per-row status dropdown. */
export const HIRING_STATUSES: HiringStatus[] = [
    "Resume",
    "Shortlisted",
    "Interview",
    "Hired",
    "Rejected",
];

export const HIRING_STATUS_OPTIONS: (HiringStatus | "All")[] = ["All", ...HIRING_STATUSES];

export const EMPTY_CANDIDATE = {
    candidateName: "",
    role: DESIGNATIONS[0],
    department: DEPARTMENTS[0],
    qualification: "",
    experience: 0,
};

export type CandidateDraft = typeof EMPTY_CANDIDATE;

export function useStaffHiring() {
    const queryClient = useQueryClient();
    const candidatesQuery = useApiQuery(HIRING_KEY, getHiringCandidates);
    const candidates = useMemo(() => candidatesQuery.data ?? [], [candidatesQuery.data]);

    const [tab, setTab] = useState<HiringTab>("Pipeline");
    const [query, setQuery] = useState("");
    const [status, setStatus] = useState<HiringStatus | "All">("All");
    const [formOpen, setFormOpen] = useState(false);
    const [draft, setDraft] = useState<CandidateDraft>(EMPTY_CANDIDATE);

    const scoped = useMemo(
        () =>
            tab === "Hired"
                ? candidates.filter((c) => c.status === "Hired")
                : candidates,
        [candidates, tab],
    );

    const filtered = useMemo(() => {
        const q = query.trim().toLowerCase();
        return scoped.filter((c) => {
            const matchQ =
                !q ||
                c.candidateName.toLowerCase().includes(q) ||
                c.role.toLowerCase().includes(q) ||
                c.department.toLowerCase().includes(q) ||
                c.empId.toLowerCase().includes(q);
            const matchS = status === "All" || c.status === status;
            return matchQ && matchS;
        });
    }, [scoped, query, status]);

    const counts = useMemo(
        () => ({
            total: candidates.length,
            shortlisted: candidates.filter((c) => c.status === "Shortlisted").length,
            interviews: candidates.filter((c) => c.status === "Interview").length,
            hired: candidates.filter((c) => c.status === "Hired").length,
            openVacancies: OPEN_VACANCIES,
        }),
        [candidates],
    );

    function writeCandidates(
        updater: (rows: HiringCandidateRow[]) => HiringCandidateRow[],
    ) {
        queryClient.setQueryData<HiringCandidateRow[]>(HIRING_KEY, (prev) => updater(prev ?? []));
    }

    /** Moves a candidate to a stage, optionally stamping an interview date. */
    function setCandidateStatus(id: number, next: HiringStatus, interviewOn?: string) {
        writeCandidates((rows) =>
            rows.map((c) =>
                c.id === id ? { ...c, status: next, interviewOn: interviewOn ?? c.interviewOn } : c,
            ),
        );
    }

    /** Next free employee number, based on the ids already handed out. */
    function nextEmployeeNumber(rows: HiringCandidateRow[]): number {
        const used = rows
            .map((c) => Number.parseInt(c.empId.replace("EMP-", ""), 10))
            .filter((n) => !Number.isNaN(n));
        return (used.length ? Math.max(...used) : NEXT_EMP_NUMBER - 1) + 1;
    }

    /**
     * Status dropdown handler. Moving a candidate to "Hired" assigns the
     * employee id shown in place of the candidate id.
     */
    function changeStatus(candidate: HiringCandidateRow, next: HiringStatus): string {
        let assignedEmpId = candidate.empId;
        if (next === "Hired" && !candidate.empId) {
            writeCandidates((rows) => {
                assignedEmpId = formatEmpId(nextEmployeeNumber(rows));
                return rows.map((c) => (c.id === candidate.id ? { ...c, empId: assignedEmpId } : c));
            });
        }
        setCandidateStatus(candidate.id, next);
        return assignedEmpId;
    }

    /** Interview scheduled five working days out (demo scheduling rule). */
    function interviewDate(): string {
        return isoInDays(5);
    }

    function openForm() {
        setDraft(EMPTY_CANDIDATE);
        setFormOpen(true);
    }

    function addCandidate(): boolean {
        if (!draft.candidateName.trim()) return false;
        writeCandidates((rows) => {
            const nextId = rows.reduce((max, c) => Math.max(max, c.id), 0) + 1;
            return [
                {
                    id: nextId,
                    candidateNo: `CAN-2026-${String(35 + nextId).padStart(4, "0")}`,
                    empId: "",
                    candidateName: draft.candidateName.trim(),
                    role: draft.role,
                    department: draft.department,
                    qualification: draft.qualification.trim() || "—",
                    experience: Number(draft.experience) || 0,
                    appliedOn: todayISO(),
                    interviewOn: "—",
                    status: "Resume",
                },
                ...rows,
            ];
        });
        setFormOpen(false);
        setDraft(EMPTY_CANDIDATE);
        return true;
    }

    return {
        candidates,
        loading: candidatesQuery.isPending,
        tab,
        setTab,
        query,
        setQuery,
        status,
        setStatus,
        scoped,
        filtered,
        counts,
        formOpen,
        setFormOpen,
        draft,
        setDraft,
        openForm,
        addCandidate,
        changeStatus,
        interviewDate,
    };
}
