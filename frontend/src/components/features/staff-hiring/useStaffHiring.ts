"use client";

import { useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
    DESIGNATIONS,
    DEPARTMENTS,
    createCandidate,
    getHiringCandidates,
    getHiringSummary,
    updateCandidateStatus,
} from "@/services";
import { useApiQuery } from "@/lib/api/use-api-query";
import { isoInDays } from "@/lib/format";
import type { HiringCandidateRow, HiringStatus } from "@/types";

// Operations ▸ Staff Hiring — candidate pipeline state for the hiring page.
//
// The pipeline, the employee ids and the open-vacancy count all come from the
// API; the write paths below change a stage (which is where EMP-#### is
// assigned, server-side) and then refresh the list so the row shows the stored
// interview date and employee id.

export const HIRING_KEY = ["operations", "hiring"];
export const HIRING_SUMMARY_KEY = ["operations", "hiring", "summary"];

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
    const summaryQuery = useApiQuery(HIRING_SUMMARY_KEY, getHiringSummary);
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
                (c.empId ?? "").toLowerCase().includes(q);
            const matchS = status === "All" || c.status === status;
            return matchQ && matchS;
        });
    }, [scoped, query, status]);

    /** Stat-tile figures: the pipeline from the list, vacancies from the API. */
    const counts = useMemo(
        () => ({
            total: candidates.length,
            shortlisted: candidates.filter((c) => c.status === "Shortlisted").length,
            interviews: candidates.filter((c) => c.status === "Interview").length,
            hired: candidates.filter((c) => c.status === "Hired").length,
            openVacancies: summaryQuery.data?.openVacancies ?? 0,
        }),
        [candidates, summaryQuery.data],
    );

    async function refresh() {
        await queryClient.invalidateQueries({ queryKey: HIRING_KEY });
        await queryClient.invalidateQueries({ queryKey: HIRING_SUMMARY_KEY });
    }

    /**
     * Status dropdown handler. Moving a candidate to "Hired" makes the server
     * assign the employee id; this returns it so the page can name it in the
     * confirmation toast.
     */
    async function changeStatus(
        candidate: HiringCandidateRow,
        next: HiringStatus,
        interviewOn?: string,
    ): Promise<string> {
        const updated = await updateCandidateStatus(candidate.id, next, interviewOn);
        await refresh();
        return updated.empId ?? "";
    }

    /** Interview scheduled five working days out (demo scheduling rule). */
    function interviewDate(): string {
        return isoInDays(5);
    }

    function openForm() {
        setDraft(EMPTY_CANDIDATE);
        setFormOpen(true);
    }

    async function addCandidate(): Promise<boolean> {
        if (!draft.candidateName.trim()) return false;
        await createCandidate({
            candidateName: draft.candidateName.trim(),
            role: draft.role,
            department: draft.department,
            qualification: draft.qualification.trim(),
            experience: Number(draft.experience) || 0,
        });
        await refresh();
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
