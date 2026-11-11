"use client";

import { useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
    blankAdmissionForm,
    createApplication,
    deleteStudent,
    getAdmissionApplications,
    getAdmissionStats,
    resetLoginCredential,
    saveSeparation,
    updateApplication,
} from "@/services";
import { useApiQuery } from "@/lib/api/use-api-query";
import { errorMessage } from "@/lib/api/client";
import type {
    AdmissionApplicationRow,
    AdmissionFormValues,
    AdmissionStats,
    AdmissionStudentStatus,
    LoginCredential,
    SeparationRecord,
    SeparationSession,
    StudentDeleteResult,
} from "@/types";
import {
    STUDENT_FILTER_FIELDS,
    filterStudents,
    primaryGuardian,
    studentName,
} from "./admission-options";

// Admission — the form, the student list and the filters.
// The page stays thin (same shape as usePayroll / useLibrary).
//
// There is no draft to track: the form is filled once and saved once, and what it
// saves is a student. Every write goes through the service layer (`student` on the
// server) and then refreshes the query, so the table shows what was actually
// stored - including the admission number the server minted.
//
// Two tabs, because there are two things to do here:
//   Admission - the form (a new student, or an edit of one already on the roll)
//   Students  - the list, with the filters and the row actions

export const ADMISSION_KEY = ["operations", "admission"];

export type AdmissionTab = "Admission" | "Students";

export const ADMISSION_TABS: AdmissionTab[] = ["Admission", "Students"];

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

    /**
     * The tiles: counted by the server, for this school.
     *
     * They used to be counted here, over `applications` — which is the list the
     * table shows, not the roll: a school with more students than the endpoint
     * returned saw that cap on every tile. A second query (same key prefix, so a
     * write refreshes both) reads `GET /admissions/stats` instead.
     */
    const statsQuery = useApiQuery<AdmissionStats>([...ADMISSION_KEY, "stats"], getAdmissionStats);
    const counts: AdmissionStats = statsQuery.data ?? {
        students: 0,
        active: 0,
        inactive: 0,
        midDropped: 0,
    };

    /**
     * Why the students could not be read, or `null`.
     *
     * A failed request used to be invisible here: the table simply rendered empty,
     * so an API that answered 500 looked exactly like a school with no students yet
     * - and saving then failed for a reason nobody could see. The page says so, and
     * offers a retry.
     */
    const loadError = applicationsQuery.error
        ? errorMessage(applicationsQuery.error, "Could not load the admission records")
        : null;

    const [tab, setTab] = useState<AdmissionTab>("Admission");
    const [form, setForm] = useState<AdmissionFormValues>(() => blankAdmissionForm());
    /** id of the saved row currently loaded into the form (null = a new student). */
    const [editingId, setEditingId] = useState<string | null>(null);
    const [detail, setDetail] = useState<AdmissionApplicationRow | null>(null);
    /** true while a save is in flight, so the button cannot be pressed twice. */
    const [saving, setSaving] = useState(false);

    const [filterField, setFilterField] = useState(STUDENT_FILTER_FIELDS[0].value);
    const [filterValue, setFilterValue] = useState("");
    const [filterStatus, setFilterStatus] = useState<AdmissionStudentStatus | "All">("All");
    const [filterReason, setFilterReason] = useState("");
    const [filterSession, setFilterSession] = useState<SeparationSession | "All">("All");
    /** student currently open in the Separation form */
    const [separationTarget, setSeparationTarget] = useState<AdmissionApplicationRow | null>(null);
    /** student currently open in the Delete-confirmation dialog */
    const [deleteTarget, setDeleteTarget] = useState<AdmissionApplicationRow | null>(null);
    const [deleting, setDeleting] = useState(false);
    /** true while the "Admit this student?" confirmation popup is open */
    const [submitConfirmOpen, setSubmitConfirmOpen] = useState(false);

    // --- the logins admitting a student created ------------------------------
    // The first-time password can only be shown at the moment it is made, so the
    // panel is opened from the save response (passwords present) or from a student's
    // row (emails only, with Reset to issue a new password).
    const [credentialRow, setCredentialRow] = useState<AdmissionApplicationRow | null>(null);
    const [credentials, setCredentials] = useState<LoginCredential[]>([]);
    const [resetting, setResetting] = useState<LoginCredential["role"] | null>(null);

    const students = applications;

    const filteredStudents = useMemo(
        () =>
            filterStudents(students, {
                field: filterField,
                value: filterValue,
                status: filterStatus,
                reason: filterReason,
                session: filterSession,
            }),
        [students, filterField, filterValue, filterStatus, filterReason, filterSession],
    );

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

    /** "Admit student" asks first: nothing is written until the operator confirms. */
    function requestSubmit() {
        setSubmitConfirmOpen(true);
    }

    function cancelSubmit() {
        setSubmitConfirmOpen(false);
    }

    /**
     * Saves the form - which *is* the admission.
     *
     * A new form creates a student (the server mints the admission number, creates
     * the guardian and the logins the form's emails make); an edit writes that
     * student back. There is no second kind of row to keep in step, and no draft
     * that nobody can find in the directory.
     */
    async function saveStudent(): Promise<AdmissionApplicationRow> {
        setSaving(true);
        try {
            const row =
                editingId !== null
                    ? await updateApplication(editingId, form)
                    : await createApplication(form);
            await refresh();
            resetForm();
            setTab("Students");
            return row;
        } finally {
            setSaving(false);
        }
    }

    /** The action behind the confirmation popup's "Done" button. */
    async function confirmSubmit(): Promise<AdmissionApplicationRow> {
        setSubmitConfirmOpen(false);
        const row = await saveStudent();
        // Admitting creates the student's and the guardian's logins; the server
        // returns them exactly once, so they are surfaced straight away.
        showCredentials(row);
        return row;
    }

    /** Saves the changes made to a student and returns to the list. */
    async function updateEditing() {
        if (editingId === null) return;
        await saveStudent();
    }

    /** Loads a saved student into the form so they can be corrected. */
    function loadIntoForm(row: AdmissionApplicationRow) {
        setForm(formValuesOf(row));
        setEditingId(row.id);
        setTab("Admission");
    }

    /** From the detail modal: "Edit" opens the row in the form. */
    function editFromDetail(row: AdmissionApplicationRow) {
        loadIntoForm(row);
        setDetail(null);
    }

    /** Records why/when the student left (→ Inactive). */
    async function recordSeparation(id: string, record: SeparationRecord) {
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

    /** Deletion: opens the type-to-confirm dialog for a student. */
    function openDelete(row: AdmissionApplicationRow) {
        setDeleteTarget(row);
    }

    function closeDelete() {
        setDeleteTarget(null);
    }

    async function confirmDelete(): Promise<StudentDeleteResult | null> {
        if (!deleteTarget || !deleteTarget.studentId) return null;
        setDeleting(true);
        try {
            // The response names the class-section when this was its last student -
            // the page toasts it, so the operator sees exactly what went.
            const result = await deleteStudent(deleteTarget.studentId);
            await refresh();
            setDeleteTarget(null);
            return result;
        } finally {
            setDeleting(false);
        }
    }

    /** Shows the logins of a student that was just admitted (passwords included). */
    function showCredentials(row: AdmissionApplicationRow) {
        const rows = row.credentials ?? [];
        if (!rows.length) return;
        setCredentialRow(row);
        setCredentials(rows);
    }

    /**
     * Opens the logins panel for a student already on the roll.
     *
     * A password cannot be read back - only its hash is stored - so the panel opens
     * without one and offers Reset, which is exactly what the office needs a week
     * later when the note with the password has gone missing.
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
            const result = await resetLoginCredential(
                credentialRow.id,
                target as "student" | "guardian",
            );
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
        loading: applicationsQuery.isPending || statsQuery.isPending,
        loadError,
        /** Re-reads the list (and the tiles) after a failed load - "Try again". */
        reload: () => {
            void applicationsQuery.refetch();
            void statsQuery.refetch();
        },
        tab,
        setTab,
        form,
        setForm,
        resetForm,
        editingRow,
        saving,
        submitConfirmOpen,
        requestSubmit,
        cancelSubmit,
        confirmSubmit,
        updateEditing,
        students,
        filteredStudents,
        filterField,
        setFilterField,
        filterValue,
        setFilterValue,
        filterStatus,
        setFilterStatus,
        filterReason,
        setFilterReason,
        filterSession,
        setFilterSession,
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
        deleteTarget,
        deleting,
        openDelete,
        closeDelete,
        confirmDelete,
        counts,
        detail,
        setDetail,
        loadIntoForm,
        editFromDetail,
    };
}
