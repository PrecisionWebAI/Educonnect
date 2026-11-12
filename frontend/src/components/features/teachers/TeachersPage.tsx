"use client";
import { useMemo, useState } from "react";
import { Tabs, PageHeader, Select, Input, Spinner } from "@/components/ui";
import RoleGuard from "@/components/auth/RoleGuard";
import { useAuth } from "@/providers/auth-context";
import { hasPermission } from "@/lib/auth/rbac";
import { errorMessage } from "@/lib/api/client";
import { useStaff, type StaffStatusFilter, type StaffTab } from "./useStaff";
import StaffListTable from "./StaffListTable";
import WorkloadMatrixTable from "./WorkloadMatrixTable";
import StaffLeaveTable from "./StaffLeaveTable";
import StaffPerformanceTable from "./StaffPerformanceTable";

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
    const canViewWorkload = hasPermission(user?.permissions, "teachers.view_workload");
    const canViewLeave = hasPermission(user?.permissions, "leave.read");

    const tabs = useMemo(() => {
        const shown: StaffTab[] = ["List"];
        if (canViewWorkload) shown.push("Workload");
        if (canViewLeave) shown.push("Attendance & Leave");
        shown.push("Performance");
        return shown;
    }, [canViewWorkload, canViewLeave]);

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
                    title="Teachers & Staff"
                    subtitle="Staff directory, workload, leave & performance — read from the school's own records."
                />
                {s.loading ? (
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
                                />
                            </>
                        )}

                        {activeTab === "Workload" && <WorkloadMatrixTable rows={s.matrix} />}
                        {activeTab === "Attendance & Leave" && <StaffLeaveTable rows={s.leaves} />}
                        {activeTab === "Performance" && <StaffPerformanceTable rows={s.perf} />}
                    </>
                )}
            </div>
        </RoleGuard>
    );
}
