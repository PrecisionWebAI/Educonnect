"use client";
import { useState } from "react";
import { Badge, Button, Input, Modal, Spinner, type BadgeTone } from "@/components/ui";
import { errorMessage } from "@/lib/api/client";
import { todayISO } from "@/lib/format";
import type { StaffAttendanceStatus } from "@/types";
import { useStaffMonth } from "./useAttendance";

/** The colour each status wears in the grid, the chips and the legend. */
const TONE: Record<StaffAttendanceStatus, BadgeTone> = {
    present: "green",
    absent: "red",
    half_day: "amber",
    on_leave: "teal",
    not_marked: "muted",
};

/** The current month, `YYYY-MM`, from the same clock the register uses. */
function thisMonth(): string {
    return todayISO().slice(0, 7);
}

/**
 * One person's month: the grid, the counts, and the percentage they are a share of.
 *
 * Three things this sheet refuses to do:
 *
 * * **divide by the calendar.** `92%` is a share of the days somebody *marked*
 *   (`marked`), and `notMarked` is printed beside it - a month that is half
 *   entered must not read as a month of absences;
 * * **count leave as absence.** `On Leave` has its own chip and its own count, and
 *   is in neither side of the fraction;
 * * **invent a working week.** Weekends are shaded only because a calendar has
 *   them; the register does not know a school's week, and colouring them "absent"
 *   would be a claim nobody made.
 */
export default function StaffMonthSheet({
    employeeId,
    employeeName,
    onClose,
}: {
    /** The person whose month this is - mounted only while somebody is picked. */
    employeeId: string;
    employeeName: string;
    onClose: () => void;
}) {
    const [month, setMonth] = useState(thisMonth());
    const m = useStaffMonth(employeeId, month);

    return (
        <Modal open title={`${employeeName} - ${m.month?.monthLabel ?? month}`} onClose={onClose}>
            <div className="toolbar">
                <Input
                    type="month"
                    aria-label="Month"
                    value={month}
                    onChange={(event) => setMonth(event.target.value || thisMonth())}
                />
                {m.month !== null && (
                    <Badge
                        tone={
                            m.month.percent >= 90
                                ? "green"
                                : m.month.percent >= 75
                                  ? "amber"
                                  : "red"
                        }
                    >
                        {m.month.percent}% attended
                    </Badge>
                )}
                {/* The next month is on its way; the grid below still shows the last
                    one, so this says "wait" without taking the screen away. */}
                {m.refreshing && <span className="text-muted-foreground text-xs">Updating…</span>}
            </div>

            {m.loading && <Spinner size="md" />}

            {!m.loading && m.error !== null && (
                <p className="text-sm" style={{ color: "var(--danger, #b42318)" }}>
                    {errorMessage(m.error, "This month could not be loaded.")}
                </p>
            )}

            {!m.loading && m.month !== null && (
                <>
                    <div className="mt-3 grid grid-cols-7 gap-1">
                        {m.month.days.map((day) => (
                            <div
                                key={day.date}
                                title={`${day.weekday} ${day.day} - ${day.statusLabel}${
                                    day.remarks ? ` (${day.remarks})` : ""
                                }`}
                                className="rounded-md border p-1 text-center"
                            >
                                <div className="text-muted-foreground text-[0.7rem]">{day.day}</div>
                                <Badge tone={TONE[day.status]}>{day.statusLabel}</Badge>
                            </div>
                        ))}
                    </div>

                    <div className="mt-4 grid gap-1 text-sm">
                        <div className="flex flex-wrap gap-2">
                            <Badge tone="green">Present {m.month.present}</Badge>
                            <Badge tone="amber">Half Day {m.month.halfDay}</Badge>
                            <Badge tone="red">Absent {m.month.absent}</Badge>
                            <Badge tone="teal">On Leave {m.month.onLeave}</Badge>
                            <Badge tone="muted">Not Marked {m.month.notMarked}</Badge>
                        </div>
                        <p className="text-muted-foreground mt-1 text-xs">
                            {m.month.percent}% is a share of the {m.month.marked}{" "}
                            {m.month.marked === 1 ? "day" : "days"} somebody marked - not of the
                            month. Approved leave is counted apart from both attendance and absence.
                        </p>
                    </div>
                </>
            )}

            <div className="mt-5 flex justify-end">
                <Button variant="ghost" onClick={onClose}>
                    Close
                </Button>
            </div>
        </Modal>
    );
}
