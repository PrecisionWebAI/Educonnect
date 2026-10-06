"use client";

import { useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
    DESIGNATIONS,
    DEPARTMENTS,
    blankStaffRegistration,
    createCandidate,
    getHiringCandidates,
    getHiringSummary,
    getStaffProfiles,
    registerStaff,
    resetStaffLogin,
    updateCandidateStatus,
} from "@/services";
import { useApiQuery } from "@/lib/api/use-api-query";
import { isoInDays } from "@/lib/format";
import type {
    HiringCandidateRow,
    HiringStatus,
    LoginCredential,
    StaffProfileRow,
    StaffRegistrationInput,
} from "@/types";

// Operations ▸ Staff Hiring — the state behind its three tabs.
//
//   Pipeline      candidates working through Resume → … → Hired (as before)
//   Hired         the staff the school actually has: `staffprofile` rows, each
//                 with the login and employee code its registration created
//   Registration  the short hire form — submitting it *is* the hiring action
//
// Registering never goes through the pipeline: the server creates the login
// (`tea.*` / `stf.*`), the staff record and the employee code in one step and
// returns the first-time password, which the page shows once — the same
// hand-over admission gives a new student.

export const HIRING_KEY = ["operations", "hiring"];

export type HiringTab = "Pipeline" | "Hired" | "Registration";

export const HIRING_TABS: HiringTab[] = ["Pipeline", "Hired", "Registration"];

export const HIRING_SUMMARY_KEY = ["operations", "hiring", "summary"];
export const STAFF_REGISTRATIONS_KEY = ["operations", "hiring", "registrations"];
export const STAFF_PROFILES_KEY = ["operations", "hiring", "profiles"];

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
    const profilesQuery = useApiQuery(STAFF_PROFILES_KEY, getStaffProfiles);

    const candidates = useMemo(() => candidatesQuery.data ?? [], [candidatesQuery.data]);
    const profiles = useMemo(() => profilesQuery.data ?? [], [profilesQuery.data]);

    const [tab, setTab] = useState<HiringTab>("Pipeline");
    const [query, setQuery] = useState("");
    const [status, setStatus] = useState<HiringStatus | "All">("All");
    const [formOpen, setFormOpen] = useState(false);
    const [draft, setDraft] = useState<CandidateDraft>(EMPTY_CANDIDATE);
    /** the short hire form on the Registration tab */
    const [registration, setRegistration] =
        useState<StaffRegistrationInput>(blankStaffRegistration);
    /** staffprofile whose logins the credentials panel is showing */
    const [credentialId, setCredentialId] = useState<number | null>(null);
    const [credentialTitle, setCredentialTitle] = useState("");
    const [credentials, setCredentials] = useState<LoginCredential[]>([]);
    const [resetting, setResetting] = useState<string | null>(null);

    const filtered = useMemo(() => {
        const q = query.trim().toLowerCase();
        return candidates.filter((c) => {
            const matchQ =
                !q ||
                c.candidateName.toLowerCase().includes(q) ||
                c.role.toLowerCase().includes(q) ||
                c.department.toLowerCase().includes(q) ||
                (c.empId ?? "").toLowerCase().includes(q);
            const matchS = status === "All" || c.status === status;
            return matchQ && matchS;
        });
    }, [candidates, query, status]);

    /** The Hired tab: search only — every row is a staff member. */
    const filteredProfiles = useMemo(() => {
        const q = query.trim().toLowerCase();
        if (!q) return profiles;
        return profiles.filter(
            (p) =>
                p.fullName.toLowerCase().includes(q) ||
                p.employeeCode.toLowerCase().includes(q) ||
                p.roleCodename.toLowerCase().includes(q) ||
                p.department.toLowerCase().includes(q) ||
                p.email.toLowerCase().includes(q),
        );
    }, [profiles, query]);

    /** Stat-tile figures: the pipeline from the list, vacancies from the API. */
    const counts = useMemo(
        () => ({
            total: candidates.length,
            shortlisted: candidates.filter((c) => c.status === "Shortlisted").length,
            interviews: candidates.filter((c) => c.status === "Interview").length,
            // People the school actually has, rather than pipeline rows.
            hired: profiles.length,
            openVacancies: summaryQuery.data?.openVacancies ?? 0,
        }),
        [candidates, profiles, summaryQuery.data],
    );

    async function refresh() {
        await queryClient.invalidateQueries({ queryKey: HIRING_KEY });
        await queryClient.invalidateQueries({ queryKey: HIRING_SUMMARY_KEY });
        await queryClient.invalidateQueries({ queryKey: STAFF_REGISTRATIONS_KEY });
        await queryClient.invalidateQueries({ queryKey: STAFF_PROFILES_KEY });
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

    /**
     * Submits the hire form. The response is the only place the first-time
     * password ever exists, so the credentials panel opens straight away; the
     * form is emptied and the person now shows up on the Hired tab.
     */
    async function submitRegistration() {
        if (!registration.fullName.trim()) return null;
        const row = await registerStaff({
            ...registration,
            fullName: registration.fullName.trim(),
            qualification: registration.qualification.trim(),
            contactEmail: registration.contactEmail.trim(),
        });
        await refresh();
        setRegistration(blankStaffRegistration());
        const created = row.credentials ?? [];
        if (created.length) {
            setCredentialId(row.staffProfileId);
            setCredentialTitle(`Logins for ${row.fullName}`);
            setCredentials(created);
        }
        return row;
    }

    /**
     * Reopens the logins panel for an existing hire. A password cannot be read
     * back — only its hash is stored — so the panel opens without one and offers
     * Reset, which is what the office needs once the password note is lost.
     */
    function openCredentials(profile: StaffProfileRow) {
        setCredentialId(profile.id);
        setCredentialTitle(`Logins for ${profile.fullName}`);
        setCredentials([
            {
                role: profile.roleCodename,
                fullName: profile.fullName,
                email: profile.email,
                password: null,
                created: true,
            },
        ]);
    }

    function closeCredentials() {
        setCredentialId(null);
        setCredentialTitle("");
        setCredentials([]);
    }

    /** Issues a new first-time password for the login the panel is showing. */
    async function resetLogin() {
        if (credentialId === null) return null;
        setResetting(credentials[0]?.role ?? "staff");
        try {
            const result = await resetStaffLogin(credentialId);
            setCredentials((prev) =>
                prev.map((credential) => ({
                    ...credential,
                    email: result.email,
                    password: result.password,
                })),
            );
            return result;
        } finally {
            setResetting(null);
        }
    }

    return {
        candidates,
        profiles,
        loading: candidatesQuery.isPending || profilesQuery.isPending,
        tab,
        setTab,
        query,
        setQuery,
        status,
        setStatus,
        filtered,
        filteredProfiles,
        counts,
        formOpen,
        setFormOpen,
        draft,
        setDraft,
        openForm,
        addCandidate,
        changeStatus,
        interviewDate,
        registration,
        setRegistration,
        submitRegistration,
        credentialId,
        credentialTitle,
        credentials,
        resetting,
        openCredentials,
        closeCredentials,
        resetLogin,
    };
}
