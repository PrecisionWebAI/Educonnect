"use client";

import { useState } from "react";
import { Button, Spinner } from "@/components/ui";
import { DatePicker } from "@/components/ui/date-picker";
import { useToast } from "@/components/ui/toast";
import { useAuth } from "@/providers/auth-context";
import { ACADEMIC_STAFF_ROLES, hasAnyRole } from "@/lib/auth/rbac";
import { errorMessage } from "@/lib/api/client";
import { useAttendance } from "./useAttendance";
import MarkAttendanceTab from "./MarkAttendanceTab";
import AttendanceHistoryTab from "./AttendanceHistoryTab";
import { SummaryStrip, WeeklyTrendCard } from "./AttendanceWidgets";
import AttentionList from "./AttentionList";

// The attendance register **inside one class-section**.
//
// Same roster grid, same chips, same summary - but the section is fixed by the
// page it is mounted on, and Save writes the register for real
// (`POST /attendance/bulk`), so the Classroom card behind it updates too.

export default function AttendancePanel({
    sectionId,
    className,
    section,
}: {
    /** The `section.id` the register is written against. */
    sectionId: string;
    /** The class the page is showing ("Class 12"). */
    className: string;
    /** The section letter the page is showing ("J"). */
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
            const records = await att.save();
            if (!records) return;
            const present = records.filter((r) => r.status === "Present").length;
            toast.push(
                "success",
                `Saved · ${present}/${records.length} present on ${records[0].date}`,
            );
        } catch (cause) {
            const message = errorMessage(cause, "Could not save the register");
            setError(message);
            toast.push("error", message);
        }
    }

    if (att.loading) return <Spinner />;

    const sectionHistory = att.history.filter((row) =>
        row.className.startsWith(`${className}-${section}`),
    );

    return (
        <div className="space-y-4">
            <div className="toolbar">
                <DatePicker className="w-auto" value={att.date} onChange={att.setDate} />
                <span className="text-muted-foreground text-sm">
                    Register for {className}-{section} · {att.roster.length}{" "}
                    {att.roster.length === 1 ? "student" : "students"}
                </span>
                {canMark && (
                    <Button
                        onClick={handleSave}
                        disabled={att.saving || att.markedCount === 0}
                    >
                        {att.saving
                            ? "Saving…"
                            : `Save (${att.markedCount}/${att.roster.length})`}
                    </Button>
                )}
            </div>

            {error && <p className="text-sm text-red-500">{error}</p>}

            {canMark ? (
                <div className="two-col">
                    <div className="two-col-main">
                        <SummaryStrip counts={att.counts} />
                        <MarkAttendanceTab
                            roster={att.roster}
                            marks={att.marks}
                            onSetMark={att.setMark}
                            onSetAll={att.setAll}
                            onReset={att.reset}
                        />
                    </div>
                    <aside className="two-col-side">
                        <WeeklyTrendCard trend={att.weeklyTrend} />
                        <AttentionList alerts={att.alerts} />
                    </aside>
                </div>
            ) : (
                <AttendanceHistoryTab
                    rows={sectionHistory}
                    totalItems={sectionHistory.length}
                    page={1}
                    pageSize={Math.max(1, sectionHistory.length)}
                    onPageChange={() => {}}
                />
            )}
        </div>
    );
}
