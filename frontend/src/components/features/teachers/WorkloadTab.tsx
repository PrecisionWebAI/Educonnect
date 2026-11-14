"use client";
import { useState } from "react";
import { Button } from "@/components/ui";
import StaffWeekSheet from "./StaffWeekSheet";
import WorkloadAnalyticsCards from "./WorkloadAnalyticsCards";
import WorkloadCapacityModal from "./WorkloadCapacityModal";
import WorkloadMatrixTable from "./WorkloadMatrixTable";
import type { WorkloadMatrixRows } from "./useStaff";
import { useWorkload } from "./useWorkload";

/**
 * The Workload tab: the four counts, the table, the capacity rule and one week.
 *
 * The pieces are held here rather than in `TeachersPage` because they share one
 * hook: a refusal from the capacity dialog and one from a duty belong in the same
 * place, and the sheet needs the same `busy` flag as the button that opened it.
 *
 * The matrix comes in as a **prop** - `useStaff` already fetched it for this tab,
 * and a second read of the same URL would let the table and the tiles beside it
 * describe two different weeks while one of them refetches.
 */
export default function WorkloadTab({
    rows,
    canManage,
}: {
    rows: WorkloadMatrixRows;
    /** `teachers.manage_workload` - capacity and duties are the office's. */
    canManage: boolean;
}) {
    const w = useWorkload({ canView: true });
    const [capacityOpen, setCapacityOpen] = useState(false);
    /** The person whose week is open, or null. */
    const [weekId, setWeekId] = useState<string | null>(null);

    return (
        <>
            <WorkloadAnalyticsCards analytics={w.analytics} rule={w.rule} />

            <div className="toolbar">
                <span className="text-muted-foreground text-sm">
                    {w.rule?.isSet
                        ? `A full week is ${w.rule.weeklyPeriods} periods. Above ${w.rule.overloadPercent}% is Overloaded, below ${w.rule.underloadPercent}% is Light.`
                        : "No capacity rule yet - each percentage is a share of the slots the timetable runs."}
                </span>
                {canManage && (
                    <Button variant="outline" onClick={() => setCapacityOpen(true)}>
                        Set Capacity
                    </Button>
                )}
            </div>

            <WorkloadMatrixTable rows={rows} onRowClick={(row) => setWeekId(row.id)} />

            <StaffWeekSheet
                teacherId={weekId}
                onClose={() => setWeekId(null)}
                canManage={canManage}
                busy={w.busy}
                error={w.error}
                onAddDuty={w.addDuty}
                onRemoveDuty={w.removeDuty}
            />

            {/* Mounted only while open: its fields start from the stored rule each
                time, so a cancelled edit cannot leak back into the next one. */}
            {capacityOpen && (
                <WorkloadCapacityModal
                    rule={w.rule}
                    weekSlots={w.analytics?.weekSlots ?? 0}
                    busy={w.busy === "rule"}
                    error={w.error}
                    onSave={w.saveRule}
                    onClose={() => setCapacityOpen(false)}
                />
            )}
        </>
    );
}
