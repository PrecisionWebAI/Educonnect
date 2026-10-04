"use client";

import { Button, Input, PageHeader, Select, Spinner, Tabs } from "@/components/ui";
import { useToast } from "@/components/ui/toast";
import RoleGuard from "@/components/auth/RoleGuard";
import { errorMessage } from "@/lib/api/client";
import CandidateFormModal from "./CandidateFormModal";
import HiringCandidatesTable from "./HiringCandidatesTable";
import { HIRING_STATUS_OPTIONS, useStaffHiring } from "./useStaffHiring";
import type { HiringCandidateRow, HiringStatus } from "@/types";

// Operations ▸ Staff Hiring (container).
// Hiring a candidate here is what used to be the "+ Add Staff" button on
// the Teachers & Staff page.

const TABS = ["Pipeline", "Hired"];

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

    return (
        <RoleGuard allowedRoles={["SYSTEM_ADMIN", "OWNER", "PRINCIPAL", "HOD"]}>
            <div className="page">
                <PageHeader
                    title="Staff Hiring"
                    actions={
                        <Button variant="primary" icon="＋" onClick={h.openForm}>
                            New Candidate
                        </Button>
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
                            tabs={TABS}
                            active={h.tab}
                            onChange={(t) => h.setTab(t as typeof h.tab)}
                        />

                        <div className="toolbar">
                            <div className="toolbar-search">
                                <Input
                                    placeholder="Search candidate, vacancy, department…"
                                    value={h.query}
                                    onChange={(e) => h.setQuery(e.target.value)}
                                />
                            </div>
                            <Select
                                value={h.status}
                                onChange={(e) => h.setStatus(e.target.value as HiringStatus | "All")}
                            >
                                {HIRING_STATUS_OPTIONS.map((s) => (
                                    <option key={s} value={s}>
                                        {s}
                                    </option>
                                ))}
                            </Select>
                        </div>

                        <HiringCandidatesTable
                            rows={h.filtered}
                            showEmployeeId={h.tab === "Hired"}
                            onStatusChange={changeStatus}
                        />

                        <p className="text-muted-foreground mt-3 text-sm">
                            Showing {h.filtered.length} of {h.scoped.length} candidates
                        </p>
                    </>
                )}

                <CandidateFormModal
                    open={h.formOpen}
                    draft={h.draft}
                    onChange={h.setDraft}
                    onClose={() => h.setFormOpen(false)}
                    onSubmit={submit}
                />
            </div>
        </RoleGuard>
    );
}
