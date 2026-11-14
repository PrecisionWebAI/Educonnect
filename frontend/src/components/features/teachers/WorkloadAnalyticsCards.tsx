"use client";
import { Table } from "@/components/ui";
import type { WorkloadAnalyticsRow, WorkloadRuleRow } from "./useWorkload";

/**
 * The tiles above the matrix, and the one sentence that explains the denominator.
 *
 * Every number here is the **server's** count over the same rows the table shows
 * (`GET /teachers/workload/analytics`), so paging or filtering the table can
 * never rewrite the totals - the mistake the directory's own tiles made before
 * Phase 1. A value the server has not sent prints "—": `0` would be a claim about
 * the school, not a missing figure.
 *
 * The capacity line names both numbers on purpose: "a full week is 24 periods
 * (school rule) · the timetable runs 26 slots". One of those is the policy and
 * the other is what the week actually holds, and a reader who sees only the
 * percentage cannot tell which one it was.
 */
export default function WorkloadAnalyticsCards({
    analytics,
    rule,
}: {
    analytics: WorkloadAnalyticsRow | null;
    rule: WorkloadRuleRow | null;
}) {
    const capacityLine = analytics
        ? `A full week is ${analytics.capacity > 0 ? `${analytics.capacity} periods` : "not set"} ` +
          `(${analytics.capacitySource === "rule" ? "school rule" : "timetable"}) · ` +
          `the timetable runs ${analytics.weekSlots} ${analytics.weekSlots === 1 ? "slot" : "slots"}`
        : "Loading the school's week…";

    const columns = [
        { key: "department", header: "Department" },
        { key: "staff", header: "Staff" },
        { key: "periods", header: "Periods / Wk" },
        {
            key: "utilisation",
            header: "Utilisation",
            render: (r: { utilisation: number }) => `${r.utilisation}%`,
        },
        { key: "overloaded", header: "Overloaded" },
    ];

    return (
        <>
            <div className="stat-tiles">
                <div className="stat-tile">
                    <b>{analytics?.overloaded ?? "—"}</b>
                    <span>Overloaded</span>
                </div>
                <div className="stat-tile">
                    <b>{analytics ? `${analytics.averageUtilisation}%` : "—"}</b>
                    <span>Average Utilisation</span>
                </div>
                <div className="stat-tile">
                    <b>{analytics?.unassigned ?? "—"}</b>
                    <span>Without Timetable</span>
                </div>
                <div className="stat-tile">
                    <b>{analytics?.duties ?? "—"}</b>
                    <span>Duties This Week</span>
                </div>
            </div>

            <p className="text-muted-foreground mb-3 text-sm">
                {capacityLine}
                {rule?.isSet === false &&
                    " — set a capacity rule to measure against the school's own week."}
            </p>

            <Table
                columns={columns}
                rows={[...(analytics?.byDepartment ?? [])].sort((first, second) =>
                    first.department.localeCompare(second.department),
                )}
                rowKey={(r) => r.department}
                empty="No departments yet."
            />
        </>
    );
}
