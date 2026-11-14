"use client";
import { useMemo, useState } from "react";
import { Tabs, PageHeader, Select, Input, Spinner } from "@/components/ui";
import RoleGuard from "@/components/auth/RoleGuard";
import { useAuth } from "@/providers/auth-context";
import { hasPermission, hasAnyRole, LEADERSHIP_ROLES, TEACHER_ROLES } from "@/lib/auth/rbac";
import { errorMessage } from "@/lib/api/client";
import { useStaff, type StaffStatusFilter, type StaffTab } from "./useStaff";
import StaffListTable from "./StaffListTable";
import StaffProfileSheet from "./StaffProfileSheet";
import AttendanceLeaveTab from "./AttendanceLeaveTab";
import StaffPerformanceTable from "./StaffPerformanceTable";
import AppraisalTab from "./AppraisalTab";
import MyStaffPanel from "./MyStaffPanel";
import SubstitutionTab from "./SubstitutionTab";
import WorkloadTab from "./WorkloadTab";

/**
 * People & Finance -> Teachers & Staff.
 *
 * Two rules this screen follows:
 *
 * * the **tiles are the server's counts** (`/teachers/summary`), so filtering or
 *   paging the table never rewrites the totals above it;
 * * a **tab is shown when the caller holds the right it needs**. A teacher has
 *   `teachers.read` but not `teachers.view_workload`, so they open their own
 *   record and no workload matrix - instead of clicking into a 403.
 */
const STATUS_OPTIONS: StaffStatusFilter[] = ["All", "Active", "On Leave", "Inactive"];

export default function TeachersPage() {
    const { user } = useAuth();
    /**
     * A teacher-only account: they read their own record, not the school's roster.
     * The server already scopes every directory read to their own row (Phase 2), so
     * this branch is the screen agreeing with the API rather than a second guard.
     */
    const selfOnly =
        hasAnyRole(user?.roles, TEACHER_ROLES) && !hasAnyRole(user?.roles, LEADERSHIP_ROLES);
    const canViewWorkload = hasPermission(user?.permissions, "teachers.view_workload");
    // Reshaping the week everybody is measured against is a narrower right than
    // reading it: without it the tab shows the numbers and offers no Edit.
    const canManageWorkload = hasPermission(user?.permissions, "teachers.manage_workload");
    const canViewLeave = hasPermission(user?.permissions, "leave.read");
    // The register is its own right: reading who was in school is not part of
    // reading the directory, and marking it is narrower again (the office's book).
    const canViewAttendance = hasPermission(user?.permissions, "staff_attendance.read");
    const canMarkAttendance = hasPermission(user?.permissions, "staff_attendance.mark");
    // The leave workflow is three rights on top of `leave.read`, and each buys a
    // different control in the Leave sub-view: filing a request, deciding one, and
    // writing the school's entitlements. The server re-checks all of them.
    const canApplyLeave = hasPermission(user?.permissions, "leave.create");
    const canApproveLeave = hasPermission(user?.permissions, "leave.approve");
    const canRejectLeave = hasPermission(user?.permissions, "leave.reject");
    const canManageLeavePolicy = hasPermission(user?.permissions, "leave.manage_policy");
    // Cover for an absent teacher: the board is readable by anybody with
    // `substitutions.read` (a teacher's own day is on it); arranging cover is the
    // office's and a department head's, and signing it off is the office's alone.
    const canViewSubstitution = hasPermission(user?.permissions, "substitutions.read");
    const canAssignSubstitution = hasPermission(user?.permissions, "substitutions.assign");
    const canApproveSubstitution = hasPermission(user?.permissions, "substitutions.approve");
    // Appraisal: everybody reads the season and fills in their own form; rating a
    // colleague is the HOD's (own department) and the office's, and opening/closing
    // or finalising a season is the office's alone.
    const canViewAppraisals = hasPermission(user?.permissions, "appraisals.read");
    const canSelfAppraise = hasPermission(user?.permissions, "appraisals.self");
    const canReviewAppraisals = hasPermission(user?.permissions, "appraisals.review");
    const canManageAppraisals = hasPermission(user?.permissions, "appraisals.manage");
    // Editing a profile is a different right from reading the directory; the
    // drawer hides its forms without it (the server refuses the write anyway).
    const canEditProfile = hasPermission(user?.permissions, "teachers.update");
    // Reading who changed what is a narrower right again: without it the drawer
    // does not even offer the Activity tab (the API answers `403`).
    const canViewAudit = hasPermission(user?.permissions, "teachers.audit_read");
    /** The person whose profile drawer is open. */
    const [profileId, setProfileId] = useState<string | null>(null);

    const tabs = useMemo(() => {
        const shown: StaffTab[] = ["List"];
        if (canViewWorkload) shown.push("Workload");
        // The tab holds two things - the leave requests and the daily register - so
        // it is shown when the caller holds either right, and each half checks its
        // own inside (`AttendanceLeaveTab`).
        if (canViewLeave || canViewAttendance) shown.push("Attendance & Leave");
        if (canViewSubstitution) shown.push("Substitution");
        if (canViewAppraisals) shown.push("Appraisal");
        shown.push("Performance");
        return shown;
    }, [canViewWorkload, canViewLeave, canViewAttendance, canViewSubstitution, canViewAppraisals]);

    const [tab, setTab] = useState<StaffTab>("List");
    const activeTab = tabs.includes(tab) ? tab : "List";
    const s = useStaff(activeTab, { canViewWorkload, canViewLeave });

    return (
        <RoleGuard
            allowedRoles={[
                "SYSTEM_ADMIN",
                "SCHOOL_ADMIN",
                "PRINCIPAL",
                "VICE_PRINCIPAL",
                "HOD",
                "TEACHER",
            ]}
        >
            <div>
                <PageHeader
                    title={selfOnly ? "My record" : "Teachers & Staff"}
                    subtitle={
                        selfOnly
                            ? "Your week, your month and your appraisal — read from the school's own records."
                            : "Staff directory, workload, leave & performance — read from the school's own records."
                    }
                />
                {/* A teacher and nothing else gets "my" reads, not the roster: the
                    server scopes every directory read to their own row, so a table of
                    one person is not a directory. */}
                {selfOnly ? (
                    <MyStaffPanel />
                ) : s.loading ? (
                    <Spinner />
                ) : (
                    <>
                        <div className="stat-tiles">
                            <div className="stat-tile">
                                {/* A count we do not have prints "—": `0` would be a
                                    claim about the school, not a missing number. */}
                                <b>{s.summary?.total ?? "—"}</b>
                                <span>Total Staff</span>
                            </div>
                            <div className="stat-tile">
                                <b>{s.summary?.active ?? "—"}</b>
                                <span>Active</span>
                            </div>
                            <div className="stat-tile">
                                <b>{s.summary?.onLeaveToday ?? "—"}</b>
                                <span>On Leave Today</span>
                            </div>
                            <div className="stat-tile">
                                <b>{s.summary?.periodsPerWeek ?? "—"}</b>
                                <span>Periods / wk</span>
                            </div>
                        </div>

                        {s.summary !== null && s.summary.withoutTimetable > 0 && (
                            <p style={{ color: "var(--muted)", margin: "0 0 0.75rem" }}>
                                {s.summary.withoutTimetable} staff on the roll have no period in the
                                timetable yet.
                            </p>
                        )}

                        <Tabs
                            tabs={tabs}
                            active={activeTab}
                            onChange={(t) => setTab(t as StaffTab)}
                        />

                        {s.error !== null && (
                            <p
                                style={{
                                    color: "var(--danger, #b42318)",
                                    marginBottom: "0.75rem",
                                }}
                            >
                                {errorMessage(s.error, "The staff directory could not be loaded.")}
                            </p>
                        )}

                        {activeTab === "List" && (
                            <>
                                <div className="toolbar">
                                    <div className="toolbar-search">
                                        <Input
                                            placeholder="Search name, subject, ID, department…"
                                            value={s.query}
                                            onChange={(e) => s.setQuery(e.target.value)}
                                        />
                                    </div>
                                    <Select
                                        value={s.dept}
                                        onChange={(e) => s.setDept(e.target.value)}
                                    >
                                        {s.departments.map((d) => (
                                            <option key={d} value={d}>
                                                {d}
                                            </option>
                                        ))}
                                    </Select>
                                    <Select
                                        value={s.status}
                                        onChange={(e) =>
                                            s.setStatus(e.target.value as StaffStatusFilter)
                                        }
                                    >
                                        {STATUS_OPTIONS.map((option) => (
                                            <option key={option} value={option}>
                                                {option === "All" ? "All statuses" : option}
                                            </option>
                                        ))}
                                    </Select>
                                </div>
                                <StaffListTable
                                    rows={s.paginated}
                                    totalItems={s.totalItems}
                                    page={s.page}
                                    pageSize={s.pageSize}
                                    onPageChange={s.setPage}
                                    onRowClick={(row) => setProfileId(row.id)}
                                />
                            </>
                        )}

                        {activeTab === "Workload" && (
                            <WorkloadTab rows={s.matrix} canManage={canManageWorkload} />
                        )}
                        {activeTab === "Attendance & Leave" && (
                            <AttendanceLeaveTab
                                leaves={s.leaves}
                                staff={s.staff}
                                canViewAttendance={canViewAttendance}
                                canMark={canMarkAttendance}
                                canViewLeave={canViewLeave}
                                canApplyLeave={canApplyLeave}
                                canApproveLeave={canApproveLeave}
                                canRejectLeave={canRejectLeave}
                                canManageLeavePolicy={canManageLeavePolicy}
                            />
                        )}
                        {activeTab === "Substitution" && (
                            <SubstitutionTab
                                canAssign={canAssignSubstitution}
                                canApprove={canApproveSubstitution}
                            />
                        )}
                        {activeTab === "Appraisal" && (
                            <AppraisalTab
                                canSelf={canSelfAppraise}
                                canReview={canReviewAppraisals}
                                canManage={canManageAppraisals}
                            />
                        )}
                        {activeTab === "Performance" && <StaffPerformanceTable rows={s.perf} />}

                        {/* The profile drawer: one person, opened from their row. */}
                        <StaffProfileSheet
                            teacherId={profileId}
                            onClose={() => setProfileId(null)}
                            canEdit={canEditProfile}
                            canViewAudit={canViewAudit}
                        />
                    </>
                )}
            </div>
        </RoleGuard>
    );
}
