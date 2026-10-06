"use client";

import { useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
    blankAdmissionForm,
    createApplication,
    getAdmissionApplications,
    resetLoginCredential,
    saveSeparation,
    updateApplication,
} from "@/services";
import { useApiQuery } from "@/lib/api/use-api-query";
import type {
    AdmissionApplicationRow,
    AdmissionFormValues,
    AdmissionStudentStatus,
    LoginCredential,
    SeparationRecord,
    SeparationSession,
} from "@/types";
import {
    DRAFT_FILTER_FIELDS,
    REGISTERED_FILTER_FIELDS,
    filterApplications,
    filterRegistered,
    primaryGuardian,
    studentName,
    studentStatus,
} from "./admission-options";

// Admission — form state, drafts, registered list and the two filters.
// The page stays thin (same shape as usePayroll / useLibrary).
//
// Every write goes to `admissionapplication` through the service layer and then
// refreshes the query, so the tables show what was actually stored — including
// the form number the server minted for a new row.

export const ADMISSION_KEY = ["operations", "admission"];

export type AdmissionTab = "Application" | "Draft" | "Registered";

export const ADMISSION_TABS: AdmissionTab[] = ["Application", "Draft", "Registered"];

/** Copies just the form fields out of a saved row. */
export function formValuesOf(row: AdmissionApplicationRow): AdmissionFormValues {
    const values = blankAdmissionForm();
    (Object.keys(values) as (keyof AdmissionFormValues)[]).forEach((key) => {
        values[key] = row[key];
    });
    return values;
}

export function useAdmission() {
    const queryClient = useQueryClient();
    const applicationsQuery = useApiQuery(ADMISSION_KEY, getAdmissionApplications);
    const applications = useMemo(() => applicationsQuery.data ?? [], [applicationsQuery.data]);

    const [tab, setTab] = useState<AdmissionTab>("Application");
    const [form, setForm] = useState<AdmissionFormValues>(() => blankAdmissionForm());
    /** id of the saved row currently loaded into the form (null = new form). */
    const [editingId, setEditingId] = useState<number | null>(null);
    const [detail, setDetail] = useState<AdmissionApplicationRow | null>(null);

    const [draftField, setDraftField] = useState(DRAFT_FILTER_FIELDS[0].value);
    const [draftValue, setDraftValue] = useState("");
    const [registeredField, setRegisteredField] = useState(REGISTERED_FILTER_FIELDS[0].value);
    const [registeredValue, setRegisteredValue] = useState("");
    const [registeredStatus, setRegisteredStatus] = useState<AdmissionStudentStatus | "All">(
        "All",
    );
    const [registeredReason, setRegisteredReason] = useState("");
    const [registeredSession, setRegisteredSession] = useState<SeparationSession | "All">("All");
    /** student currently open in the Separation form */
    const [separationTarget, setSeparationTarget] = useState<AdmissionApplicationRow | null>(null);

    // --- the logins an admission created ------------------------------------
    // The first-time password can only be shown at the moment it is made, so the
    // panel is opened from the register response (passwords present) or from a
    // registered row (emails only, with Reset to issue a new password).
    const [credentialRow, setCredentialRow] =
        useState<AdmissionApplicationRow | null>(null);
    const [credentials, setCredentials] = useState<LoginCredential[]>([]);
    const [resetting, setResetting] = useState<LoginCredential["role"] | null>(null);

    const drafts = useMemo(() => applications.filter((a) => a.status === "Draft"), [applications]);
    const registered = useMemo(
        () => applications.filter((a) => a.status === "Registered"),
        [applications],
    );

    const filteredDrafts = useMemo(
        () => filterApplications(drafts, DRAFT_FILTER_FIELDS, draftField, draftValue),
        [drafts, draftField, draftValue],
    );
    const filteredRegistered = useMemo(
        () =>
            filterRegistered(registered, {
                field: registeredField,
                value: registeredValue,
                status: registeredStatus,
                reason: registeredReason,
                session: registeredSession,
            }),
        [
            registered,
            registeredField,
            registeredValue,
            registeredStatus,
            registeredReason,
            registeredSession,
        ],
    );

    const counts = useMemo(() => {
        const active = registered.filter((r) => studentStatus(r) === "Active").length;
        return {
            registered: registered.length,
            drafts: drafts.length,
            active,
            inactive: registered.length - active,
            /** dropped mid-session — the "Incomplete Session" separations */
            midDropped: registered.filter((r) => r.separation?.session === "Incomplete Session")
                .length,
        };
    }, [registered, drafts]);

    const editingRow = useMemo(
        () => applications.find((a) => a.id === editingId) ?? null,
        [applications, editingId],
    );

    /** Re-reads the list after a write so the table shows stored values. */
    async function refresh() {
        await queryClient.invalidateQueries({ queryKey: ADMISSION_KEY });
    }

    function resetForm() {
        setForm(blankAdmissionForm());
        setEditingId(null);
    }

    /** Saves the form as a Draft (creates a row, or updates the loaded one). */
    async function saveDraft() {
        if (editingId !== null) {
            await updateApplication(editingId, form, "Draft");
        } else {
            await createApplication(form, "Draft");
        }
        await refresh();
        resetForm();
        setTab("Draft");
    }

    /** Submits the form — the student is registered. */
    async function submitApplication() {
        const row =
            editingId !== null
                ? await updateApplication(editingId, form, "Registered")
                : await createApplication(form, "Registered");
        await refresh();
        resetForm();
        setTab("Registered");
        // Registering creates the student's and the guardian's logins; the server
        // returns them exactly once, so they are surfaced straight away.
        showCredentials(row);
    }

    /** Updates an already registered application in place. */
    async function updateRegistered(id: number, values: AdmissionFormValues) {
        await updateApplication(id, values, "Registered");
        await refresh();
    }

    /** Saves the changes made to a registered row and returns to the list. */
    async function updateEditing() {
        if (editingId === null) return;
        await updateRegistered(editingId, form);
        resetForm();
        setTab("Registered");
    }

    /** Loads a saved row into the Application tab so it can be finished. */
    function loadIntoForm(row: AdmissionApplicationRow) {
        setForm(formValuesOf(row));
        setEditingId(row.id);
        setTab("Application");
    }

    /** From the detail modal: "Edit" opens the row in the form. */
    function editFromDetail(row: AdmissionApplicationRow) {
        loadIntoForm(row);
        setDetail(null);
    }

    /** Separation: records why/when the student left (→ Inactive). */
    async function recordSeparation(id: number, record: SeparationRecord) {
        await saveSeparation(id, record);
        await refresh();
        setSeparationTarget(null);
    }

    /** Opens the Separation form for a student. */
    function openSeparation(row: AdmissionApplicationRow) {
        setSeparationTarget(row);
    }

    function closeSeparation() {
        setSeparationTarget(null);
    }

    /** Shows the logins of a just-registered application (passwords included). */
    function showCredentials(row: AdmissionApplicationRow) {
        const rows = row.credentials ?? [];
        if (!rows.length) return;
        setCredentialRow(row);
        setCredentials(rows);
    }

    /** Opens the logins panel for an already registered application.
     *
     * A password cannot be read back - only its hash is stored - so the panel
     * opens without one and offers Reset, which is exactly what the office needs
     * a week later when the note with the password has gone missing.
     */
    function openCredentials(row: AdmissionApplicationRow) {
        const rows: LoginCredential[] = [];
        if (row.studentLoginEmail) {
            rows.push({
                role: "student",
                fullName: studentName(row),
                email: row.studentLoginEmail,
                password: null,
                created: true,
            });
        }
        if (row.guardianLoginEmail) {
            rows.push({
                role: "guardian",
                fullName: primaryGuardian(row),
                email: row.guardianLoginEmail,
                password: null,
                created: true,
            });
        }
        if (!rows.length) return;
        setCredentialRow(row);
        setCredentials(rows);
    }

    function closeCredentials() {
        setCredentialRow(null);
        setCredentials([]);
    }

    /** Issues a new first-time password and swaps it into the panel. */
    async function resetLogin(target: LoginCredential["role"]) {
        if (!credentialRow) return null;
        setResetting(target);
        try {
            const result = await resetLoginCredential(credentialRow.id, target as "student" | "guardian");
            setCredentials((prev) =>
                prev.map((credential) =>
                    credential.role === target
                        ? { ...credential, email: result.email, password: result.password }
                        : credential,
                ),
            );
            return result;
        } finally {
            setResetting(null);
        }
    }

    return {
        applications,
        loading: applicationsQuery.isPending,
        tab,
        setTab,
        form,
        setForm,
        resetForm,
        editingRow,
        saveDraft,
        submitApplication,
        updateRegistered,
        updateEditing,
        drafts,
        registered,
        filteredDrafts,
        filteredRegistered,
        draftField,
        setDraftField,
        draftValue,
        setDraftValue,
        registeredField,
        setRegisteredField,
        registeredValue,
        setRegisteredValue,
        registeredStatus,
        setRegisteredStatus,
        registeredReason,
        setRegisteredReason,
        registeredSession,
        setRegisteredSession,
        separationTarget,
        openCredentials,
        showCredentials,
        closeCredentials,
        credentials,
        credentialRow,
        resetLogin,
        resetting,
        openSeparation,
        closeSeparation,
        recordSeparation,
        counts,
        detail,
        setDetail,
        loadIntoForm,
        editFromDetail,
    };
}

