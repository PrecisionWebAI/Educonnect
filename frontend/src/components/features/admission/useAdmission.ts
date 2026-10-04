"use client";

import { useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { blankAdmissionForm, getAdmissionApplications } from "@/services";
import { useApiQuery } from "@/lib/api/use-api-query";
import { todayISO } from "@/lib/format";
import type {
    AdmissionApplicationRow,
    AdmissionFormValues,
    AdmissionStatus,
    AdmissionStudentStatus,
    SeparationRecord,
    SeparationSession,
} from "@/types";
import {
    DRAFT_FILTER_FIELDS,
    REGISTERED_FILTER_FIELDS,
    filterApplications,
    filterRegistered,
    studentStatus,
} from "./admission-options";

// Admission — form state, drafts, registered list and the two filters.
// The page stays thin (same shape as usePayroll / useLibrary).

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

    function writeApplications(
        updater: (rows: AdmissionApplicationRow[]) => AdmissionApplicationRow[],
    ) {
        queryClient.setQueryData<AdmissionApplicationRow[]>(ADMISSION_KEY, (prev) =>
            updater(prev ?? []),
        );
    }

    function nextApplicationNo(rows: AdmissionApplicationRow[]) {
        const nextId = rows.reduce((max, a) => Math.max(max, a.id), 0) + 1;
        return { nextId, applicationNo: `ADM-2026-${String(146 + nextId).padStart(4, "0")}` };
    }

    function resetForm() {
        setForm(blankAdmissionForm());
        setEditingId(null);
    }

    /** Saves the form as a Draft (creates a row or updates the loaded one). */
    function saveDraft() {
        writeApplications((rows) => {
            if (editingId !== null) {
                return rows.map((a) =>
                    a.id === editingId ? { ...a, ...form, status: "Draft" as AdmissionStatus } : a,
                );
            }
            const { nextId, applicationNo } = nextApplicationNo(rows);
            return [
                { id: nextId, applicationNo, ...form, status: "Draft", createdOn: todayISO() },
                ...rows,
            ];
        });
        resetForm();
        setTab("Draft");
    }

    /** Submits the form — the student is registered. */
    function submitApplication() {
        writeApplications((rows) => {
            if (editingId !== null) {
                return rows.map((a) =>
                    a.id === editingId
                        ? { ...a, ...form, status: "Registered" as AdmissionStatus }
                        : a,
                );
            }
            const { nextId, applicationNo } = nextApplicationNo(rows);
            return [
                {
                    id: nextId,
                    applicationNo,
                    ...form,
                    status: "Registered",
                    createdOn: todayISO(),
                },
                ...rows,
            ];
        });
        resetForm();
        setTab("Registered");
    }

    /** Updates an already registered application in place. */
    function updateRegistered(id: number, values: AdmissionFormValues) {
        writeApplications((rows) =>
            rows.map((a) => (a.id === id ? { ...a, ...values, status: "Registered" } : a)),
        );
    }

    /** Saves the changes made to a registered row and returns to the list. */
    function updateEditing() {
        if (editingId === null) return;
        updateRegistered(editingId, form);
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
    function recordSeparation(id: number, record: SeparationRecord) {
        writeApplications((rows) =>
            rows.map((a) => (a.id === id ? { ...a, separation: record } : a)),
        );
        setSeparationTarget(null);
    }

    /** Opens the Separation form for a student. */
    function openSeparation(row: AdmissionApplicationRow) {
        setSeparationTarget(row);
    }

    function closeSeparation() {
        setSeparationTarget(null);
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

