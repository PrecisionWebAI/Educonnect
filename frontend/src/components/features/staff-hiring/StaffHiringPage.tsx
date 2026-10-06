"use client";

import { Button, Input, PageHeader, Select, Spinner, Tabs } from "@/components/ui";
import { useToast } from "@/components/ui/toast";
import RoleGuard from "@/components/auth/RoleGuard";
import { errorMessage } from "@/lib/api/client";
import AdmissionCredentials from "../admission/AdmissionCredentials";
import CandidateFormModal from "./CandidateFormModal";
import HiredStaffTable from "./HiredStaffTable";
import HiringCandidatesTable from "./HiringCandidatesTable";
import StaffRegistrationForm from "./StaffRegistrationForm";
import { HIRING_STATUS_OPTIONS, HIRING_TABS, useStaffHiring } from "./useStaffHiring";
import type { HiringCandidateRow, HiringStatus } from "@/types";

// Operations ▸ Staff Hiring (container).
//
// Two flows live here, kept apart on purpose:
//   * Pipeline — candidates the school is still deciding about (Resume →
//     Shortlisted → Interview → Hired) and the vacancies behind them.
//   * Registration — a hire that is already decided. The short form creates the
//     login, the staff record and the employee code in one step, and the person
//     then appears on the Hired tab (and can be paid from the salary register
//     under that employee code).
//
// The Hired tab lists `staffprofile` rows — the staff the school actually has —
// so "hired" and "on the staff roll" are the same thing.

const CREDENTIALS_NOTE =
    "These logins were created for this hire. A first-time password is shown " +
    "only now - only its hash is stored - so copy it and hand it over. Press " +
    "Reset to issue a new one (the old password stops working).";

export default function StaffHiringPage() {
    const toast = useToast();
    const h = useStaffHiring();

    async function changeStatus(candidate: HiringCandidateRow, status: HiringStatus) {
        try {
            const empId = await h.changeStatus(candidate, status);
            if (status === "Hired") {
                toast.push(
                    "success",
                    `${candidate.candidateName} hired — employee ID ${empId} assigned`,
                );
                return;
            }
            toast.push("info", `${candidate.candidateName} marked as ${status}`);
        } catch (error) {
            toast.push("error", errorMessage(error, "Could not move the candidate"));
        }
    }

    async function submit() {
        const name = h.draft.candidateName.trim();
        try {
            if (!(await h.addCandidate())) {
                toast.push("error", "Candidate name is required");
                return;
            }
            toast.push("success", `${name} added to the hiring pipeline`);
        } catch (error) {
            toast.push("error", errorMessage(error, "Could not add the candidate"));
        }
    }

    /** The hire form: the server creates the login + staff record in one step. */
    async function register() {
        const name = h.registration.fullName.trim();
        try {
            const row = await h.submitRegistration();
            if (!row) {
                toast.push("error", "Staff name is required");
                return;
            }
            toast.push("success", `${name} hired — login ${row.loginEmail ?? "created"}`);
            h.setTab("Hired");
        } catch (error) {
            toast.push("error", errorMessage(error, "Could not register the hire"));
        }
    }

    return (
        <RoleGuard allowedRoles={["SYSTEM_ADMIN", "OWNER", "PRINCIPAL", "HOD"]}>
            <div className="page">
                <PageHeader
                    title="Staff Hiring"
                    actions={
                        h.tab === "Pipeline" ? (
                            <Button variant="primary" icon="＋" onClick={h.openForm}>
                                New Candidate
                            </Button>
                        ) : undefined
                    }
                />

                {h.loading ? (
                    <Spinner />
                ) : (
                    <>
                        <div className="stat-tiles">
                            <div className="stat-tile">
                                <b>{h.counts.total}</b>
                                <span>Candidates</span>
                            </div>
                            <div className="stat-tile">
                                <b>{h.counts.shortlisted}</b>
                                <span>Shortlisted</span>
                            </div>
                            <div className="stat-tile">
                                <b>{h.counts.interviews}</b>
                                <span>Interviews</span>
                            </div>
                            <div className="stat-tile">
                                <b>{h.counts.hired}</b>
                                <span>Hired</span>
                            </div>
                            <div className="stat-tile">
                                <b>{h.counts.openVacancies}</b>
                                <span>Open Vacancies</span>
                            </div>
                        </div>

                        <Tabs
                            tabs={HIRING_TABS}
                            active={h.tab}
                            onChange={(t) => h.setTab(t as typeof h.tab)}
                        />

                        {h.tab === "Registration" ? (
                            <StaffRegistrationForm
                                value={h.registration}
                                onChange={h.setRegistration}
                                onSubmit={register}
                            />
                        ) : (
                            <>
                                <div className="toolbar">
                                    <div className="toolbar-search">
                                        <Input
                                            placeholder={
                                                h.tab === "Hired"
                                                    ? "Search name, role, employee code…"
                                                    : "Search candidate, vacancy, department…"
                                            }
                                            value={h.query}
                                            onChange={(e) => h.setQuery(e.target.value)}
                                        />
                                    </div>
                                    {h.tab === "Pipeline" && (
                                        <Select
                                            value={h.status}
                                            onChange={(e) =>
                                                h.setStatus(e.target.value as HiringStatus | "All")
                                            }
                                        >
                                            {HIRING_STATUS_OPTIONS.map((s) => (
                                                <option key={s} value={s}>
                                                    {s}
                                                </option>
                                            ))}
                                        </Select>
                                    )}
                                </div>

                                {h.tab === "Hired" ? (
                                    <HiredStaffTable
                                        rows={h.filteredProfiles}
                                        onShowLogins={h.openCredentials}
                                    />
                                ) : (
                                    <HiringCandidatesTable
                                        rows={h.filtered}
                                        showEmployeeId={h.status === "Hired"}
                                        onStatusChange={changeStatus}
                                    />
                                )}

                                <p className="text-muted-foreground mt-3 text-sm">
                                    Showing{" "}
                                    {h.tab === "Hired"
                                        ? h.filteredProfiles.length
                                        : h.filtered.length}{" "}
                                    of {h.tab === "Hired" ? h.profiles.length : h.candidates.length}{" "}
                                    {h.tab === "Hired" ? "staff" : "candidates"}
                                </p>
                            </>
                        )}
                    </>
                )}

                <CandidateFormModal
                    open={h.formOpen}
                    draft={h.draft}
                    onChange={h.setDraft}
                    onClose={() => h.setFormOpen(false)}
                    onSubmit={submit}
                />

                <AdmissionCredentials
                    open={h.credentials.length > 0}
                    title={h.credentialTitle}
                    note={CREDENTIALS_NOTE}
                    credentials={h.credentials}
                    resetting={h.resetting}
                    onReset={h.resetLogin}
                    onClose={h.closeCredentials}
                />
            </div>
        </RoleGuard>
    );
}
