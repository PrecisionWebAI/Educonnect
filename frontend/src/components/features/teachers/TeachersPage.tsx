"use client";
import { useState } from "react";
import { Tabs, PageHeader, Select, Input, Button, Spinner } from "@/components/ui";
import { useStaff, type StaffTab } from "./useStaff";
import StaffListTable from "./StaffListTable";
import WorkloadMatrixTable from "./WorkloadMatrixTable";
import StaffLeaveTable from "./StaffLeaveTable";
import StaffPerformanceTable from "./StaffPerformanceTable";

const TABS: StaffTab[] = ["List", "Workload", "Leave & Substitute", "Performance"];

export default function TeachersPage() {
    const [tab, setTab] = useState<StaffTab>("List");
    const s = useStaff(tab);

    return (
        <div>
            <PageHeader
                title="Teachers & Staff"
                subtitle="Staff directory, workload matrix, leave & performance."
                actions={<Button variant="primary">+ Add Staff</Button>}
            />

            {s.loading ? (
                <Spinner />
            ) : (
                <>
                    <div className="stat-tiles">
                        <div className="stat-tile">
                            <b>{s.staff.length}</b>
                            <span>Total Staff</span>
                        </div>
                        <div className="stat-tile">
                            <b>{s.activeCount}</b>
                            <span>Active</span>
                        </div>
                        <div className="stat-tile">
                            <b>{s.leaveCount}</b>
                            <span>On Leave</span>
                        </div>
                        <div className="stat-tile">
                            <b>{s.matrix.reduce((a, r) => a + r.periods, 0)}</b>
                            <span>Periods / wk</span>
                        </div>
                    </div>

                    <Tabs tabs={TABS} active={tab} onChange={(t) => setTab(t as StaffTab)} />

                    {tab === "List" && (
                        <>
                            <div className="toolbar">
                                <div className="toolbar-search">
                                    <Input
                                        placeholder="Search name, subject, ID…"
                                        value={s.query}
                                        onChange={(e) => s.setQuery(e.target.value)}
                                    />
                                </div>
                                <Select value={s.dept} onChange={(e) => s.setDept(e.target.value)}>
                                    {s.departments.map((d) => (
                                        <option key={d} value={d}>
                                            {d}
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

                    {tab === "Workload" && <WorkloadMatrixTable rows={s.matrix} />}
                    {tab === "Leave & Substitute" && <StaffLeaveTable rows={s.leaves} />}
                    {tab === "Performance" && <StaffPerformanceTable rows={s.perf} />}
                </>
            )}
        </div>
    );
}
