"use client";

import { Button, Modal, PageHeader, Spinner, Tabs } from "@/components/ui";
import { useToast } from "@/components/ui/toast";
import RoleGuard from "@/components/auth/RoleGuard";
import { errorMessage } from "@/lib/api/client";
import { phoneProblem } from "@/lib/format";
import AdmissionDetailModal from "./AdmissionDetailModal";
import AdmissionCredentials from "./AdmissionCredentials";
import AdmissionFilter from "./AdmissionFilter";
import AdmissionForm from "./AdmissionForm";
import DraftApplicationsTable from "./DraftApplicationsTable";
import RegisteredFilters from "./RegisteredFilters";
import RegisteredStudentsTable from "./RegisteredStudentsTable";
import SeparationModal from "./SeparationModal";
import ConfirmDeleteAdmissionModal from "./ConfirmDeleteAdmissionModal";
import { ADMISSION_TABS, useAdmission, type AdmissionTab } from "./useAdmission";
import { DRAFT_FILTER_FIELDS, droppedClassOf, missingRequiredFields, studentName } from "./admission-options";
import type { AdmissionApplicationRow, SeparationRecord } from "@/types";

// Operations ▸ Admission.
// Tab 1 Application — the full admission form (save as draft or submit).
// Tab 2 Draft       — half-filled forms, filterable, resumable.
// Tab 3 Registered  — registered students with a read-only detail view.

export default function AdmissionPage() {
    const toast = useToast();
    const a = useAdmission();

    async function saveDraft() {
        const name = studentName(a.form);
        try {
            await a.saveDraft();
            toast.push("success", `${name || "Application"} saved as draft`);
        } catch (error) {
            toast.push("error", errorMessage(error, "Could not save the application"));
        }
    }

    /**
     * Register asks first - but only once the mandatory fields are filled.
     *
     * The server refuses the same way (`REQUIRED_TO_REGISTER`), so this is a
     * courtesy: the office is told which fields are missing on the form it is
     * looking at instead of after a round-trip. Saving a **draft** asks nothing.
     */
    function submit() {
        const missing = missingRequiredFields(a.form);
        if (missing.length) {
            toast.push("error", `Fill in ${missing.join(", ")} before registering the student`);
            return;
        }
        // Every number on the form has to be exactly ten digits - the server
        // refuses anything else (`phone_problem` in `app/core/text.py`).
        const phoneIssue = [
            phoneProblem(a.form.guardianPhone, "Guardian phone"),
            phoneProblem(a.form.fatherPhone, "Father's phone"),
            phoneProblem(a.form.motherPhone, "Mother's phone"),
        ].find((problem) => problem !== null);
        if (phoneIssue) {
            toast.push("error", phoneIssue);
            return;
        }
        a.requestSubmit();
    }

    async function confirmSubmit() {
        const name = studentName(a.form);
        try {
            await a.confirmSubmit();
            toast.push("success", `${name || "Student"} registered`);
        } catch (error) {
            toast.push("error", errorMessage(error, "Could not register the student"));
        }
    }

    async function update() {
        const name = studentName(a.form);
        try {
            await a.updateEditing();
            toast.push("success", `${name || "Application"} updated`);
        } catch (error) {
            toast.push("error", errorMessage(error, "Could not update the application"));
        }
    }

    function editFromDetail(row: AdmissionApplicationRow) {
        a.editFromDetail(row);
        toast.push("info", `${studentName(row)} loaded into the application form`);
    }

    /** Issues a new first-time password for the student or the guardian login. */
    async function resetLogin(target: string) {
        try {
            const result = await a.resetLogin(target);
            if (result) {
                toast.push(
                    "success",
                    `New password for ${result.email} — copy it now, it is not shown again`,
                );
            }
        } catch (error) {
            toast.push("error", errorMessage(error, "Could not reset the password"));
        }
    }

    async function separate(row: AdmissionApplicationRow, record: SeparationRecord) {
        try {
            await a.recordSeparation(row.id, record);
            toast.push(
                "error",
                `${studentName(row)} separated from ${droppedClassOf(row)} — ${record.reason}`,
            );
        } catch (error) {
            toast.push("error", errorMessage(error, "Could not record the separation"));
        }
    }

    async function handleDeleteConfirm() {
        const name = a.deleteTarget ? studentName(a.deleteTarget) : "Student";
        try {
            const result = await a.confirmDelete();
            toast.push(
                "success",
                result?.classroomRemoved
                    ? `${name} deleted — they were the last student of ${result.classroomRemoved}, so that class-section and its records were removed too.`
                    : `${name} deleted`,
            );
        } catch (error) {
            toast.push("error", errorMessage(error, "Could not delete the student"));
        }
    }

    return (
        <RoleGuard
            allowedRoles={[
                "SYSTEM_ADMIN",
                "SCHOOL_ADMIN",
                "PRINCIPAL",
                "VICE_PRINCIPAL",
                "HOD",
                "STAFF",
            ]}
        >
            <div className="page">
                <PageHeader title="Admission" />

                {a.loadError && (
                    <div
                        role="alert"
                        className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-md border border-red-300/70 bg-red-50 p-4 text-sm text-red-600 dark:border-red-400/30 dark:bg-red-500/10 dark:text-red-300"
                    >
                        <span>
                            <b>Could not load the admission records.</b> {a.loadError}
                        </span>
                        <Button variant="outline" onClick={a.reload}>
                            Try again
                        </Button>
                    </div>
                )}

                {a.loading ? (
                    <Spinner />
                ) : (
                    <>
                        <div className="stat-tiles">
                            <div className="stat-tile">
                                <b>{a.counts.registered}</b>
                                <span>Total Registered</span>
                            </div>
                            <div className="stat-tile">
                                <b>{a.counts.drafts}</b>
                                <span>Draft Applications</span>
                            </div>
                            <div className="stat-tile">
                                <b>{a.counts.active}</b>
                                <span>Active Students</span>
                            </div>
                            <div className="stat-tile">
                                <b>{a.counts.inactive}</b>
                                <span>Inactive Students</span>
                            </div>
                            <div className="stat-tile">
                                <b>{a.counts.midDropped}</b>
                                <span>Mid-session Dropped</span>
                            </div>
                        </div>

                        <Tabs
                            tabs={ADMISSION_TABS}
                            active={a.tab}
                            onChange={(t) => a.setTab(t as AdmissionTab)}
                        />

                        {a.tab === "Application" && (
                            <>
                                {a.editingRow && (
                                    <p className="text-muted-foreground mb-4 text-sm">
                                        Editing <b>{studentName(a.editingRow)}</b> (
                                        {a.editingRow.status}) —{" "}
                                        {a.editingRow.status === "Registered"
                                            ? "Update saves the changes to this record."
                                            : "Submit registers the student."}
                                    </p>
                                )}
                                <AdmissionForm value={a.form} onChange={a.setForm} />
                                <div className="modal-actions">
                                    <Button variant="ghost" onClick={a.resetForm}>
                                        Clear form
                                    </Button>
                                    {a.editingRow?.status === "Registered" ? (
                                        <Button variant="primary" onClick={update}>
                                            Update
                                        </Button>
                                    ) : (
                                        <>
                                            <Button variant="outline" onClick={saveDraft}>
                                                Save as Draft
                                            </Button>
                                            <Button variant="primary" onClick={submit}>
                                                Submit
                                            </Button>
                                        </>
                                    )}
                                </div>
                            </>
                        )}

                        {a.tab === "Draft" && (
                            <>
                                <AdmissionFilter
                                    fields={DRAFT_FILTER_FIELDS}
                                    field={a.draftField}
                                    onFieldChange={a.setDraftField}
                                    value={a.draftValue}
                                    onValueChange={a.setDraftValue}
                                />
                                <DraftApplicationsTable
                                    rows={a.filteredDrafts}
                                    onResume={a.loadIntoForm}
                                    onView={a.setDetail}
                                />
                                <p className="text-muted-foreground mt-3 text-sm">
                                    Showing {a.filteredDrafts.length} of {a.drafts.length} drafts
                                </p>
                            </>
                        )}

                        {a.tab === "Registered" && (
                            <>
                                <RegisteredFilters
                                    field={a.registeredField}
                                    onFieldChange={a.setRegisteredField}
                                    value={a.registeredValue}
                                    onValueChange={a.setRegisteredValue}
                                    status={a.registeredStatus}
                                    onStatusChange={a.setRegisteredStatus}
                                    reason={a.registeredReason}
                                    onReasonChange={a.setRegisteredReason}
                                    session={a.registeredSession}
                                    onSessionChange={a.setRegisteredSession}
                                />
                                <RegisteredStudentsTable
                                    rows={a.filteredRegistered}
                                    onView={a.setDetail}
                                    onAction={a.openSeparation}
                                    onLogins={a.openCredentials}
                                    onDelete={a.openDelete}
                                />
                                <p className="text-muted-foreground mt-3 text-sm">
                                    Showing {a.filteredRegistered.length} of {a.registered.length}{" "}
                                    registered students
                                </p>
                            </>
                        )}
                    </>
                )}

                <AdmissionDetailModal
                    application={a.detail}
                    onClose={() => a.setDetail(null)}
                    onEdit={editFromDetail}
                />

                <AdmissionCredentials
                    open={a.credentialRow !== null}
                    title={a.credentialRow ? `Logins — ${studentName(a.credentialRow)}` : "Logins"}
                    credentials={a.credentials}
                    resetting={a.resetting}
                    onReset={resetLogin}
                    onClose={a.closeCredentials}
                />

                <SeparationModal
                    student={a.separationTarget}
                    onClose={a.closeSeparation}
                    onSubmit={(id, record) => {
                        const row = a.separationTarget;
                        if (row) separate(row, record);
                        else a.recordSeparation(id, record);
                    }}
                />

                <ConfirmDeleteAdmissionModal
                    student={a.deleteTarget}
                    deleting={a.deleting}
                    onClose={a.closeDelete}
                    onConfirm={handleDeleteConfirm}
                />

                <Modal
                    open={a.submitConfirmOpen}
                    title="Register student?"
                    onClose={a.cancelSubmit}
                >
                    <div className="space-y-4">
                        <p className="text-muted-foreground text-sm">
                            This registers <b>{studentName(a.form) || "the student"}</b> and creates
                            the student and guardian logins from the emails on the form. Continue?
                        </p>
                        <div className="flex justify-end gap-2">
                            <Button variant="outline" onClick={a.cancelSubmit}>
                                Cancel
                            </Button>
                            <Button variant="primary" onClick={confirmSubmit}>
                                Done
                            </Button>
                        </div>
                    </div>
                </Modal>
            </div>
        </RoleGuard>
    );
}
