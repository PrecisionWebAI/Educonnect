"use client";

import { useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
    DEPARTMENTS,
    STAFF_ROLE_OPTIONS,
    blankStaffRegistration,
    createCandidate,
    deactivateStaffProfile,
    deleteStaffProfile,
    getHiringCandidates,
    getStaffProfiles,
    getSubjects,
    reactivateStaffProfile,
    registerStaff,
    resetStaffLogin,
    staffRoleLabel,
    updateCandidateStatus,
    updateStaffProfile,
    uploadCandidateResume,
} from "@/services";
import { useApiQuery } from "@/lib/api/use-api-query";
import { usePermission } from "@/hooks/use-authorization";
import { isoInDays } from "@/lib/format";
import type {
    HiringCandidateRow,
    HiringStatus,
    LoginCredential,
    StaffLifecycleInput,
    StaffLifecycleResult,
    StaffProfileCreateResult,
    StaffProfileRow,
    StaffRegistrationInput,
    SubjectRow,
} from "@/types";

// Operations ▸ Staff Hiring — the state behind its three tabs.
//
//   Pipeline      candidates working through Resume → … → Hired (as before)
//   Hired         the staff the school actually has: `staffprofile` rows, each
//                 with the login and employee code its registration created
//   Registration  the short hire form — submitting it *is* the hiring action
//
// Registering never goes through the pipeline: the server creates the login from
// the email the form supplied, the staff record and the employee code in one step
// and returns the first-time password, which the page shows once — the same
// hand-over admission gives a new student.

/**
 * What the hire form cannot be submitted without: a label plus the field that
 * satisfies it.
 *
 * Mirrors `REQUIRED_TO_HIRE` on the server, which is the real gate — this copy
 * only tells the office *before* the round-trip. A name, a way to reach the
 * person, the role their login opens and the bank their salary is paid into are
 * the identity of the record.
 */
const REQUIRED_HIRE_FIELDS: {
    label: string;
    filled: (registration: StaffRegistrationInput) => boolean;
}[] = [
    { label: "Full name", filled: (r) => Boolean(r.fullName.trim()) },
    { label: "Contact email", filled: (r) => Boolean(r.contactEmail.trim()) },
    { label: "Phone", filled: (r) => Boolean(r.phone.trim()) },
    { label: "Roles", filled: (r) => r.roleCodenames.length > 0 },
    { label: "Bank name", filled: (r) => Boolean(r.bankName.trim()) },
];

/** The mandatory labels still empty on the hire form, in form order. */
export function missingHireFields(registration: StaffRegistrationInput): string[] {
    return REQUIRED_HIRE_FIELDS.filter((entry) => !entry.filled(registration)).map(
        (entry) => entry.label,
    );
}

export const HIRING_KEY = ["operations", "hiring"];

export type HiringTab = "Pipeline" | "Hired" | "Registration";

/**
 * The tabs in the order the work happens: the pipeline first (people still being
 * decided about), then Registration — the form whose submission *is* the hire — and
 * the Hired roll last, which is what the other two feed.
 */
export const HIRING_TABS: HiringTab[] = ["Pipeline", "Registration", "Hired"];

export const HIRING_SUMMARY_KEY = ["operations", "hiring", "summary"];
export const STAFF_PROFILES_KEY = ["operations", "hiring", "profiles"];

/** All pipeline stages (Hired is still a valid stored status). */
export const HIRING_STATUSES: HiringStatus[] = [
    "Resume",
    "Shortlisted",
    "Interview",
    "Hired",
    "Rejected",
];

/** Stages the per-row dropdown offers — "Hired" is reached via the gated button. */
export const PIPELINE_STATUSES: HiringStatus[] = [
    "Resume",
    "Shortlisted",
    "Interview",
    "Rejected",
];

export const HIRING_STATUS_OPTIONS: (HiringStatus | "All")[] = [
    "All",
    ...PIPELINE_STATUSES,
];

export const EMPTY_CANDIDATE = {
    candidateName: "",
    department: DEPARTMENTS[0],
    appliedFor: STAFF_ROLE_OPTIONS[0].value,
    qualification: "",
    experience: 0,
    phone: "",
    email: "",
    subjectId: null as string | null,
    subjectName: "",
    interviewAt: "",
    interviewNote: "",
    resumeFile: null as File | null,
};

export type CandidateDraft = typeof EMPTY_CANDIDATE;

export function useStaffHiring() {
    const queryClient = useQueryClient();
    const candidatesQuery = useApiQuery(HIRING_KEY, getHiringCandidates);
    const profilesQuery = useApiQuery(STAFF_PROFILES_KEY, getStaffProfiles);
    const subjectsQuery = useApiQuery(["academics", "subjects"], getSubjects);

    const candidates = useMemo(() => candidatesQuery.data ?? [], [candidatesQuery.data]);
    const profiles = useMemo(() => profilesQuery.data ?? [], [profilesQuery.data]);
    const subjects = useMemo<SubjectRow[]>(() => subjectsQuery.data ?? [], [subjectsQuery.data]);

    /** Only admin / principal / above may take the Hired decision. */
    const canHire = usePermission("hiring.hire");

    const [tab, setTab] = useState<HiringTab>("Pipeline");
    const [query, setQuery] = useState("");
    const [status, setStatus] = useState<HiringStatus | "All">("All");
    const [formOpen, setFormOpen] = useState(false);
    const [draft, setDraft] = useState<CandidateDraft>(EMPTY_CANDIDATE);

    /** The staff member the View popup shows (the Hired tab's View / Deactivate). */
    const [detail, setDetail] = useState<StaffProfileRow | null>(null);
    /** Which part of that popup the row's button meant to open. */
    const [detailFocus, setDetailFocus] = useState<"record" | "lifecycle">("record");
    /** The lifecycle call in flight, so the popup's buttons can show a spinner. */
    const [lifecycleBusy, setLifecycleBusy] = useState<string | null>(null);
    /** the short hire form on the Registration tab */
    const [registration, setRegistration] =
        useState<StaffRegistrationInput>(blankStaffRegistration);
    /** staffprofile whose logins the credentials panel is showing */
    const [credentialId, setCredentialId] = useState<string | null>(null);
    const [credentialTitle, setCredentialTitle] = useState("");
    const [credentials, setCredentials] = useState<LoginCredential[]>([]);
    const [resetting, setResetting] = useState<string | null>(null);
    /** the candidate the Hired confirmation modal is asking about */
    /** candidate the "Hired" button promoted into the registration form */
    const [candidateId, setCandidateId] = useState<string | null>(null);
    /** employee being edited (the Hired tab's Edit action) */
    const [editingId, setEditingId] = useState<string | null>(null);
    /** employee the delete confirmation is asking about */
    const [deleteTarget, setDeleteTarget] = useState<StaffProfileRow | null>(null);
    const [deleting, setDeleting] = useState(false);

    const filtered = useMemo(() => {
        const q = query.trim().toLowerCase();
        return candidates.filter((c) => {
            // Hired candidates move to the Hired tab (they are staff now).
            if (c.status === "Hired") return false;
            const matchQ =
                !q ||
                c.candidateName.toLowerCase().includes(q) ||
                (c.appliedFor ?? c.role).toLowerCase().includes(q) ||
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
                p.roleCodenames.join(" ").toLowerCase().includes(q) ||
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
        }),
        [candidates, profiles],
    );

    async function refresh() {
        await queryClient.invalidateQueries({ queryKey: HIRING_KEY });
        await queryClient.invalidateQueries({ queryKey: HIRING_SUMMARY_KEY });
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
        // `datetime-local` gives `YYYY-MM-DDTHH:mm`; append seconds for the API.
        const interviewAt = draft.interviewAt ? `${draft.interviewAt}:00` : null;
        const row = await createCandidate({
            candidateName: draft.candidateName.trim(),
            department: draft.department,
            appliedFor: draft.appliedFor,
            role: staffRoleLabel(draft.appliedFor),
            qualification: draft.qualification.trim(),
            experience: Number(draft.experience) || 0,
            phone: draft.phone.trim(),
            email: draft.email.trim(),
            subjectId: draft.subjectId,
            subjectName: draft.subjectName.trim(),
            interviewAt,
            interviewNote: draft.interviewNote.trim(),
        });
        if (draft.resumeFile) {
            await uploadCandidateResume(row.id, draft.resumeFile);
        }
        await refresh();
        setFormOpen(false);
        setDraft(EMPTY_CANDIDATE);
        return true;
    }

    /** The "Hired" button: pre-fill the registration form from the candidate. */
    function openHire(candidate: HiringCandidateRow) {
        setRegistration({
            ...blankStaffRegistration(),
            fullName: candidate.candidateName,
            roleCodenames: [candidate.appliedFor ?? "staff"],
            department: candidate.department,
            qualification: candidate.qualification ?? "",
            experienceYears: candidate.experience,
            contactEmail: candidate.email ?? "",
            phone: candidate.phone ?? "",
            subjectIds: candidate.subjectId ? [candidate.subjectId] : [],
        });
        setCandidateId(candidate.id);
        setEditingId(null);
        setTab("Registration");
    }

    /** The Hired tab's Edit action: pre-fill the form from an employee. */
    function editEmployee(profile: StaffProfileRow) {
        setRegistration({
            ...blankStaffRegistration(),
            fullName: profile.fullName,
            roleCodenames:
                profile.roleCodenames.length > 0
                    ? profile.roleCodenames
                    : [profile.roleCodename],
            department: profile.department,
            qualification: profile.qualification ?? "",
            experienceYears: profile.experienceYears,
            contactEmail: profile.email,
            joiningDate: profile.joiningDate,
            phone: profile.phone ?? "",
            subjectIds: profile.subjectIds,
            address: profile.address ?? "",
            emergencyContact: profile.emergencyContact ?? "",
            aadhaarNo: profile.aadhaarNo ?? "",
            panNo: profile.panNo ?? "",
            bankName: profile.bankName ?? "",
            bankAccountNo: profile.bankAccountNo ?? "",
            ifsc: profile.ifsc ?? "",
            salaryMonthly: profile.salaryMonthly,
            previousEmployerMonthlySalary: profile.previousEmployerMonthlySalary,
        });
        setCandidateId(null);
        setEditingId(profile.id);
        setTab("Registration");
    }

    /** Leave the registration form (clear any edit / candidate link). */
    function cancelEdit() {
        setRegistration(blankStaffRegistration());
        setCandidateId(null);
        setEditingId(null);
    }

    /**
     * Submits the hire form. The response is the only place the first-time
     * password ever exists, so the credentials panel opens straight away; the
     * form is emptied and the person now shows up on the Hired tab.
     */
    async function submitRegistration() {
        // The same mandatory fields the server insists on; the page has already
        // told the office which ones are missing.
        if (missingHireFields(registration).length) return null;
        const payload: StaffRegistrationInput = {
            ...registration,
            fullName: registration.fullName.trim(),
            qualification: registration.qualification.trim(),
            contactEmail: registration.contactEmail.trim(),
            candidateId,
        };
        const row =
            editingId !== null
                ? await updateStaffProfile(editingId, payload)
                : await registerStaff(payload);
        await refresh();
        setRegistration(blankStaffRegistration());
        setCandidateId(null);
        setEditingId(null);
        if (editingId === null) {
            const createdRow = row as StaffProfileCreateResult;
            const created = createdRow.credentials ?? [];
            if (created.length) {
                setCredentialId(row.id);
                setCredentialTitle(`Logins for ${row.fullName}`);
                setCredentials(created);
            }
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
                role: profile.roleCodenames.join(", ") || profile.roleCodename,
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

    /**
     * Open the read-only popup for a staff member (the Hired tab's View).
     *
     * `focus` is how the row's buttons say what they meant: View opens the record,
     * Deactivate opens the same popup on its lifecycle panel — the office sees the whole
     * person (their login, their children, what they hold) before switching anything off.
     * One place to do it, not two.
     */
    function openDetail(profile: StaffProfileRow, focus: "record" | "lifecycle" = "record") {
        setDetail(profile);
        setDetailFocus(focus);
    }

    function closeDetail() {
        setDetail(null);
        setDetailFocus("record");
    }

    /** Apply a lifecycle answer to the row the popup is showing. */
    function applyLifecycle(profile: StaffProfileRow, result: StaffLifecycleResult) {
        setDetail((prev) =>
            prev && prev.id === profile.id
                ? {
                      ...prev,
                      isActive: result.action === "reactivated",
                      leftOn: result.leftOn,
                      deactivatedAt: result.deactivatedAt,
                      deactivatedRoles:
                          result.action === "reactivated" ? [] : result.rolesWithdrawn,
                      loginActive: result.loginActive,
                      roleCodenames:
                          result.action === "reactivated"
                              ? [...prev.roleCodenames, ...result.rolesRestored]
                              : prev.roleCodenames.filter(
                                    (name) => !result.rolesWithdrawn.includes(name),
                                ),
                  }
                : prev,
        );
    }

    /**
     * The Hired tab's Deactivate: switch their staff side off.
     *
     * Nothing is deleted and no password changes: the server withdraws the roles, stamps
     * the day they left and leaves the records in place. Their login is only switched off
     * when it opened nothing else, so a teacher who is also a parent still signs in.
     */
    async function deactivateEmployee(
        profile: StaffProfileRow,
        input: StaffLifecycleInput = {},
    ): Promise<StaffLifecycleResult> {
        setLifecycleBusy(profile.id);
        try {
            const result = await deactivateStaffProfile(profile.id, input);
            applyLifecycle(profile, result);
            await refresh();
            return result;
        } finally {
            setLifecycleBusy(null);
        }
    }

    /** Put them back on the staff roll, with exactly the roles they had. */
    async function reactivateEmployee(
        profile: StaffProfileRow,
        input: StaffLifecycleInput = {},
    ): Promise<StaffLifecycleResult> {
        setLifecycleBusy(profile.id);
        try {
            const result = await reactivateStaffProfile(profile.id, input);
            applyLifecycle(profile, result);
            await refresh();
            return result;
        } finally {
            setLifecycleBusy(null);
        }
    }

    /** The Hired tab's Delete action: remove the confirmed employee. */
    async function confirmDelete() {
        if (deleteTarget === null) return;
        setDeleting(true);
        try {
            await deleteStaffProfile(deleteTarget.id);
            await refresh();
            setDeleteTarget(null);
        } finally {
            setDeleting(false);
        }
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
        subjects,
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
        canHire,
        candidateId,
        editingId,
        openHire,
        editEmployee,
        cancelEdit,
        deleteTarget,
        setDeleteTarget,
        deleting,
        confirmDelete,
        detail,
        detailFocus,
        openDetail,
        closeDetail,
        lifecycleBusy,
        deactivateEmployee,
        reactivateEmployee,
    };
}
