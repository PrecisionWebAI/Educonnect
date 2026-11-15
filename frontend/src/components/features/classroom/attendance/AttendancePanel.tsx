"use client";

import { useState } from "react";
import { Button, Spinner } from "@/components/ui";
import { DatePicker } from "@/components/ui/date-picker";
import { useToast } from "@/components/ui/toast";
import { useAuth } from "@/providers/auth-context";
import { ACADEMIC_STAFF_ROLES, hasAnyRole } from "@/lib/auth/rbac";
import { errorMessage } from "@/lib/api/client";
import { isClosedDay } from "@/lib/attendance/view";
import { useAttendance } from "./useAttendance";
import MarkAttendanceTab from "./MarkAttendanceTab";
import { SummaryStrip, TotalsPanel, WeeklyTrendCard } from "./AttendanceWidgets";
import AttentionList from "./AttentionList";

// The attendance register **inside one class-section**.
//
// Phase 4 wires it to the register the server actually holds:
//
//   * opening a date loads `GET /attendance/section/{id}?date=`, so a saved day comes
//     back pre-filled and a child on approved leave shows `leave`;
//   * the calendar greys out Sundays and the school's holidays, and Save is disabled
//     with the reason printed (`closedReason`);
//   * the strip, the trend and the attention list are the section's real numbers;
//   * Save sends only the rows that were changed.

export default function AttendancePanel({
    sectionId,
    className,
    section,
}: {
    /** The `section.id` the register is written against. */
    sectionId: string;
    /** The class the page is showing (e.g. "Class 12"). */
    className: string;
    /** The section letter the page is showing (e.g. "J"). */
    section: string;
}) {
    const toast = useToast();
    const { user } = useAuth();
    const canMark = hasAnyRole(user?.roles, ACADEMIC_STAFF_ROLES);
    const att = useAttendance({ sectionId, className, section });
    const [error, setError] = useState<string | null>(null);

    async function handleSave() {
        setError(null);
        try {
            const result = await att.save();
            if (!result) return;
            toast.push(
                "success",
                `Saved · ${result.present}/${result.total} present on ${att.date}`,
            );
        } catch (cause) {
            const message = errorMessage(cause, "Could not save the register");
            setError(message);
            toast.push("error", message);
        }
    }

    if (att.loading) return <Spinner />;

    const closedNote = att.isClosed
        ? `School closed — ${att.closedReason}. The register cannot be saved.`
        : null;

    return (
        <div className="space-y-4">
            <div className="toolbar">
                <DatePicker
                    className="w-auto"
                    value={att.date}
                    onChange={att.setDate}
                    isClosedDay={(day) => isClosedDay(att.closedDays, day)}
                />
                <span className="text-muted-foreground text-sm">
                    Register for {className}-{section} · {att.rows.length}{" "}
                    {att.rows.length === 1 ? "student" : "students"}
                    {att.savedPercent !== null ? ` · ${att.savedPercent}% present` : ""}
                </span>
                {canMark && (
                    <Button
                        onClick={handleSave}
                        disabled={att.saving || att.dirtyCount === 0 || att.isClosed}
                        title={closedNote ?? undefined}
                    >
                        {att.saving ? "Saving…" : `Save (${att.dirtyCount}/${att.rows.length})`}
                    </Button>
                )}
            </div>

            {closedNote && (
                <p className="text-sm text-amber-600" role="status">
                    {closedNote}
                </p>
            )}
            {error && <p className="text-sm text-red-500">{error}</p>}

            {canMark ? (
                <div className="two-col">
                    <div className="two-col-main">
                        <SummaryStrip counts={att.counts} />
                        <MarkAttendanceTab
                            rows={att.rows}
                            marks={att.marks}
                            onSetMark={att.setMark}
                            onSetAll={att.setAll}
                            onReset={att.reset}
                            disabled={att.isClosed}
                        />
                    </div>
                    <aside className="two-col-side">
                        <WeeklyTrendCard trend={att.trendValues} />
                        <AttentionList rows={att.attention} />
                        <TotalsPanel
                            rows={att.totals}
                            threshold={att.threshold}
                            workingDays={att.workingDays}
                            range={att.range}
                            onRangeChange={att.setRange}
                            loading={att.loadingWidgets}
                        />
                    </aside>
                </div>
            ) : (
                <TotalsPanel
                    rows={att.totals}
                    threshold={att.threshold}
                    workingDays={att.workingDays}
                    range={att.range}
                    onRangeChange={att.setRange}
                    loading={att.loadingWidgets}
                />
            )}
        </div>
    );
}
