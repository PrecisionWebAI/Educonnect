"use client";

import { Button, Modal, PageHeader, Spinner, Tabs } from "@/components/ui";
import { useToast } from "@/components/ui/toast";
import RoleGuard from "@/components/auth/RoleGuard";
import { errorMessage } from "@/lib/api/client";
import { phoneProblem } from "@/lib/format";
import AdmissionDetailModal from "./AdmissionDetailModal";
import AdmissionCredentials from "./AdmissionCredentials";
import AdmissionForm from "./AdmissionForm";
import StudentFilters from "./StudentFilters";
import StudentsTable from "./StudentsTable";
import SeparationModal from "./SeparationModal";
import ConfirmDeleteAdmissionModal from "./ConfirmDeleteAdmissionModal";
import { ADMISSION_TABS, useAdmission, type AdmissionTab } from "./useAdmission";
import { droppedClassOf, missingRequiredFields, studentName } from "./admission-options";
import type { AdmissionApplicationRow, SeparationRecord } from "@/types";

// Operations ▸ Admission.
// Tab 1 Admission — the form. It is saved once, and saving it **is** the admission.
// Tab 2 Students  — the school's students, filterable, with the row actions.

export default function AdmissionPage() {
    const toast = useToast();
    const a = useAdmission();

    /**
     * "Admit student" asks first - but only once the mandatory fields are filled.
     *
     * The server refuses the same way (`REQUIRED_TO_ADMIT`), so this is a courtesy:
     * the office is told which fields are missing on the form it is looking at
     * instead of after a round-trip.
     */
    function submit() {
        const missing = missingRequiredFields(a.form);
        if (missing.length) {
            toast.push("error", `Fill in ${missing.join(", ")} before admitting the student`);
            return;
        }
        // The **guardian's** number has to be exactly ten digits - the server refuses
        // anything else (`phone_problem` in `app/core/text.py`). The father / mother
        // blocks are family detail, and the form no longer collects a number for them.
        const phoneIssue = phoneProblem(a.form.guardianPhone, "Guardian phone");
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
            toast.push("success", `${name || "Student"} admitted`);
        } catch (error) {
            toast.push("error", errorMessage(error, "Could not admit the student"));
        }
    }

    async function update() {
        const name = studentName(a.form);
        try {
            await a.updateEditing();
            toast.push("success", `${name || "Student"} updated`);
        } catch (error) {
            toast.push("error", errorMessage(error, "Could not update the student"));
        }
    }

    function editFromDetail(row: AdmissionApplicationRow) {
        a.editFromDetail(row);
        toast.push("info", `${studentName(row)} loaded into the admission form`);
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
                            <b>Could not load the students.</b> {a.loadError}
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
                                <b>{a.counts.students}</b>
                                <span>Students</span>
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

                        {a.tab === "Admission" && (
                            <>
                                {a.editingRow && (
                                    <p className="text-muted-foreground mb-4 text-sm">
                                        Editing <b>{studentName(a.editingRow)}</b> (
                                        {a.editingRow.admissionNumber || "no number"}) — Update
                                        saves the changes to this student.
                                    </p>
                                )}
                                <AdmissionForm value={a.form} onChange={a.setForm} />
                                <div className="modal-actions">
                                    <Button variant="ghost" onClick={a.resetForm}>
                                        Clear form
                                    </Button>
                                    {a.editingRow ? (
                                        <Button
                                            variant="primary"
                                            onClick={update}
                                            loading={a.saving}
                                        >
                                            Update
                                        </Button>
                                    ) : (
                                        <Button
                                            variant="primary"
                                            onClick={submit}
                                            loading={a.saving}
                                        >
                                            Admit student
                                        </Button>
                                    )}
                                </div>
                            </>
                        )}

                        {a.tab === "Students" && (
                            <>
                                <StudentFilters
                                    field={a.filterField}
                                    onFieldChange={a.setFilterField}
                                    value={a.filterValue}
                                    onValueChange={a.setFilterValue}
                                    status={a.filterStatus}
                                    onStatusChange={a.setFilterStatus}
                                    reason={a.filterReason}
                                    onReasonChange={a.setFilterReason}
                                    session={a.filterSession}
                                    onSessionChange={a.setFilterSession}
                                />
                                <StudentsTable
                                    rows={a.filteredStudents}
                                    onView={a.setDetail}
                                    onAction={a.openSeparation}
                                    onLogins={a.openCredentials}
                                    onDelete={a.openDelete}
                                />
                                <p className="text-muted-foreground mt-3 text-sm">
                                    Showing {a.filteredStudents.length} of {a.students.length}{" "}
                                    students
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
                    title="Admit student?"
                    onClose={a.cancelSubmit}
                >
                    <div className="space-y-4">
                        <p className="text-muted-foreground text-sm">
                            This admits <b>{studentName(a.form) || "the student"}</b> and creates
                            the student and guardian logins from the emails on the form.
                            Continue?
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

