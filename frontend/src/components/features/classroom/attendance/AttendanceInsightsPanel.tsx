"use client";

import { Badge, Spinner, Table } from "@/components/ui";
import { getIrregularStudents, getLeaveSync } from "@/services";
import { useApiQuery } from "@/lib/api/use-api-query";
import type { IrregularStudent, LeaveSyncRow } from "@/types";

// School-wide attendance insights: who is missing school, and whether approved
// leave reached the register. Both are about every class at once, so they belong
// to the Classroom grid - not to one class-section's page.

export default function AttendanceInsightsPanel() {
    const irregular = useApiQuery(["attendance", "irregular"], getIrregularStudents);
    const leaveSync = useApiQuery(["attendance", "leave-sync"], getLeaveSync);

    if (irregular.isPending || leaveSync.isPending) return <Spinner />;

    return (
        <div className="space-y-8">
            <section>
                <h3 className="mb-3 text-lg font-semibold">Irregular attendance</h3>
                <Table
                    columns={[
                        {
                            key: "name",
                            header: "Student",
                            render: (r: IrregularStudent) => <b>{r.name}</b>,
                        },
                        { key: "className", header: "Class" },
                        { key: "absences", header: "Absences (term)" },
                        { key: "pattern", header: "AI pattern insight" },
                        {
                            key: "risk",
                            header: "Risk",
                            render: (r: IrregularStudent) => (
                                <Badge
                                    tone={
                                        r.risk === "High"
                                            ? "red"
                                            : r.risk === "Medium"
                                              ? "amber"
                                              : "green"
                                    }
                                >
                                    {r.risk}
                                </Badge>
                            ),
                        },
                    ]}
                    rows={irregular.data ?? []}
                    rowKey={(r) => r.id}
                    empty="No irregular attendance patterns detected."
                />
            </section>

            <section>
                <h3 className="mb-3 text-lg font-semibold">Leave sync</h3>
                <Table
                    columns={[
                        {
                            key: "student",
                            header: "Student",
                            render: (r: LeaveSyncRow) => <b>{r.student}</b>,
                        },
                        { key: "className", header: "Class" },
                        { key: "from", header: "From" },
                        { key: "days", header: "Days" },
                        { key: "autoMarked", header: "Attendance auto-marked as" },
                        {
                            key: "status",
                            header: "Sync status",
                            render: (r: LeaveSyncRow) => (
                                <Badge
                                    tone={
                                        r.status === "Synced"
                                            ? "green"
                                            : r.status === "Pending"
                                              ? "amber"
                                              : "muted"
                                    }
                                >
                                    {r.status}
                                </Badge>
                            ),
                        },
                    ]}
                    rows={leaveSync.data ?? []}
                    rowKey={(r) => r.id}
                    empty="No leave-attendance sync records."
                />
            </section>
        </div>
    );
}
