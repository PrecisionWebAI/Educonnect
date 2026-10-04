"use client";

import { Button, PageHeader, Spinner, Tabs } from "@/components/ui";
import { useToast } from "@/components/ui/toast";
import RoleGuard from "@/components/auth/RoleGuard";
import AdmissionDetailModal from "./AdmissionDetailModal";
import AdmissionFilter from "./AdmissionFilter";
import AdmissionForm from "./AdmissionForm";
import DraftApplicationsTable from "./DraftApplicationsTable";
import RegisteredFilters from "./RegisteredFilters";
import RegisteredStudentsTable from "./RegisteredStudentsTable";
import SeparationModal from "./SeparationModal";
import { ADMISSION_TABS, useAdmission, type AdmissionTab } from "./useAdmission";
import { DRAFT_FILTER_FIELDS, droppedClassOf, studentName } from "./admission-options";
import type { AdmissionApplicationRow, SeparationRecord } from "@/types";

// Operations ▸ Admission.
// Tab 1 Application — the full admission form (save as draft or submit).
// Tab 2 Draft       — half-filled forms, filterable, resumable.
// Tab 3 Registered  — registered students with a read-only detail view.

export default function AdmissionPage() {
    const toast = useToast();
    const a = useAdmission();

    function saveDraft() {
        const name = studentName(a.form);
        a.saveDraft();
        toast.push("success", `${name || "Application"} saved as draft`);
    }

    function submit() {
        const name = studentName(a.form);
        a.submitApplication();
        toast.push("success", `${name || "Student"} registered`);
    }

    function update() {
        const name = studentName(a.form);
        a.updateEditing();
        toast.push("success", `${name || "Application"} updated`);
    }

    function editFromDetail(row: AdmissionApplicationRow) {
        a.editFromDetail(row);
        toast.push("info", `${studentName(row)} loaded into the application form`);
    }

    function separate(row: AdmissionApplicationRow, record: SeparationRecord) {
        a.recordSeparation(row.id, record);
        toast.push(
            "error",
            `${studentName(row)} separated from ${droppedClassOf(row)} — ${record.reason}`,
        );
    }

    return (
        <RoleGuard allowedRoles={["ADMIN", "DIRECTOR", "PRINCIPAL", "HOD", "STAFF"]}>
            <div className="page">
                <PageHeader title="Admission" />

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

                <SeparationModal
                    student={a.separationTarget}
                    onClose={a.closeSeparation}
                    onSubmit={(id, record) => {
                        const row = a.separationTarget;
                        if (row) separate(row, record);
                        else a.recordSeparation(id, record);
                    }}
                />
            </div>
        </RoleGuard>
    );
}

