"use client";

import type { RegisterRow } from "@/types";
import { Button } from "@/components/ui";
import { ATTENDANCE_STATUSES, type Status } from "./useAttendance";
import { chipLabel } from "@/lib/attendance/view";

function initials(name: string) {
    return name
        .split(" ")
        .map((p) => p[0])
        .slice(0, 2)
        .join("")
        .toUpperCase();
}

// Roster grid — one row per child on the roll, four status chips each.
//
// Phase 4: the rows come from the **saved register**, not from the student list, so
//
//   * a day already marked opens pre-filled (the chip shows what the database says);
//   * a child on approved leave shows `leave` with the request it came from and no
//     chips — a leave is decided in Leave & Applications, never here;
//   * a closed day (Sunday / holiday) disables every chip, because the server would
//     refuse the save anyway.
export default function MarkAttendanceTab({
    rows,
    marks,
    onSetMark,
    onSetAll,
    onReset,
    disabled = false,
}: {
    rows: RegisterRow[];
    marks: Record<string, Status>;
    onSetMark: (id: string, status: Status) => void;
    onSetAll: (status: Status) => void;
    onReset: () => void;
    /** True on a Sunday/holiday: the register cannot be saved. */
    disabled?: boolean;
}) {
    if (rows.length === 0) {
        return (
            <p style={{ color: "var(--muted)" }}>
                No students in this class-section. Add students first.
            </p>
        );
    }

    return (
        <div className="roster">
            <div className="roster-actions">
                <Button
                    size="sm"
                    variant="success"
                    onClick={() => onSetAll("Present")}
                    disabled={disabled}
                >
                    Mark all present
                </Button>
                <Button size="sm" variant="ghost" onClick={onReset} disabled={disabled}>
                    Reset
                </Button>
            </div>

            {rows.map((row) => {
                const onLeave = row.status === "leave";
                return (
                    <div key={row.studentId} className="roster-row">
                        <span className="cell-avatar">{initials(row.name)}</span>
                        <span className="roster-name">
                            <strong>{row.name}</strong>
                            <span style={{ color: "var(--muted)", fontSize: "0.76rem" }}>
                                {row.admissionNo ?? "—"}
                                {row.status === "half_day" && !marks[row.studentId]
                                    ? " · saved as half day"
                                    : ""}
                            </span>
                        </span>

                        {onLeave ? (
                            <div className="roster-status">
                                <span className="chip chip-leave chip-on">
                                    {chipLabel("leave")}
                                </span>
                                <span
                                    style={{ color: "var(--muted)", fontSize: "0.72rem" }}
                                    title={row.leaveRequestId ?? undefined}
                                >
                                    approved in Leave &amp; Applications
                                </span>
                            </div>
                        ) : (
                            <div
                                className="roster-status"
                                role="radiogroup"
                                aria-label={`Attendance for ${row.name}`}
                            >
                                {ATTENDANCE_STATUSES.filter((st) => st !== "Leave").map((st) => (
                                    <button
                                        key={st}
                                        type="button"
                                        role="radio"
                                        aria-checked={marks[row.studentId] === st}
                                        disabled={disabled}
                                        className={`chip chip-${(
                                            marks[row.studentId] ?? ""
                                        ).toLowerCase()}${
                                            marks[row.studentId] === st ? "chip-on" : ""
                                        }`}
                                        onClick={() => onSetMark(row.studentId, st)}
                                    >
                                        {st}
                                    </button>
                                ))}
                                {marks[row.studentId] === "Leave" && (
                                    <span className="chip chip-leave chip-on">Leave</span>
                                )}
                            </div>
                        )}
                    </div>
                );
            })}
        </div>
    );
}
