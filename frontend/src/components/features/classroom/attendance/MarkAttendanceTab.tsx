"use client";

import { useState } from "react";
import { Button, Input, Select } from "@/components/ui";
import { cn } from "cn";
import { pct, titleCase } from "@/lib/format";
import { ATTENDANCE_STATUSES, type Status } from "./useAttendance";
import {
    filterRoster,
    monthFigure,
    withRoll,
    type DayRow,
    type RosterFilter,
} from "@/lib/attendance/view";

// Roster grid — one row per child on the roll, three status chips each.
//
// The rows come from the **saved register** (`dayModel`), not from the student list, so
//
//   * a day already marked opens pre-filled, and the chip it carries wears the **locked**
//     shade: the database says so and this session has not touched it;
//   * tapping any chip on that row writes a draft, which unlocks the row (normal shade) and
//     flips the Save button back to "Save" - saving locks it again;
//   * an approved leave reads as **Absent**: the leave itself is decided in Leave &
//     Applications and is only read here, never written back as `leave`;
//   * a closed day (Sunday / holiday) disables every chip, because the server would refuse
//     the save anyway.
//
// The row above the list is the teacher's toolkit, in the order they reach for it:
// **search**, mark every child present, reset the day, and finally a filter that shows only
// the children still on one mark. Search and filter are display only - narrowing the list
// never drops a mark.
export default function MarkAttendanceTab({
    rows,
    onSetMark,
    onSetAll,
    onReset,
    disabled = false,
}: {
    rows: DayRow[];
    onSetMark: (id: string, status: Status) => void;
    onSetAll: (status: Status) => void;
    onReset: () => void;
    /** True on a Sunday/holiday: the register cannot be saved. */
    disabled?: boolean;
}) {
    const [query, setQuery] = useState("");
    const [filter, setFilter] = useState<RosterFilter>("all");

    if (rows.length === 0) {
        return (
            <p style={{ color: "var(--muted)" }}>
                No students in this class-section. Add students first.
            </p>
        );
    }

    const visible = filterRoster(withRoll(rows), query, filter);

    return (
        <div className="roster">
            <div className="roster-actions">
                <Input
                    value={query}
                    onChange={(event) => setQuery(event.target.value)}
                    placeholder="Search a student"
                    aria-label="Search a student"
                    className="roster-search"
                />
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
                <Select
                    value={filter}
                    onChange={(event) => setFilter(event.target.value as RosterFilter)}
                    aria-label="Show"
                >
                    <option value="all">All</option>
                    {ATTENDANCE_STATUSES.map((status) => (
                        <option key={status} value={status}>
                            {status}
                        </option>
                    ))}
                </Select>
            </div>

            {visible.length === 0 ? (
                <p style={{ color: "var(--muted)", fontSize: "0.88rem" }}>
                    No student matches that search or filter.
                </p>
            ) : (
                visible.map((row) => {
                    const name = titleCase(row.name);
                    return (
                        <div
                            key={row.studentId}
                            className={cn(
                                "roster-row",
                                row.locked
                                    ? "roster-row-saved"
                                    : row.mark
                                      ? "roster-row-touched"
                                      : null,
                            )}
                        >
                            <span className="cell-avatar cell-roll">{row.roll}</span>
                            <span className="roster-name">
                                <strong>{name}</strong>
                                {!row.active && (
                                    <span style={{ color: "var(--muted)", fontSize: "0.76rem" }}>
                                        left the school
                                    </span>
                                )}
                                {row.halfDay && !row.mark && (
                                    <span style={{ color: "var(--muted)", fontSize: "0.76rem" }}>
                                        saved as half day
                                    </span>
                                )}
                                {row.yearPercent !== undefined && (
                                    <span className="roster-figures">
                                        <span
                                            title={
                                                row.monthOpen
                                                    ? `${row.monthSaved ?? 0} of ${row.monthOpen} registers taken`
                                                    : undefined
                                            }
                                        >
                                            {monthFigure(
                                                row.monthPresent,
                                                row.monthOpen,
                                                row.monthSaved,
                                            )}
                                        </span>
                                        <span>Anu. Percentage {pct(row.yearPercent)}</span>
                                    </span>
                                )}
                            </span>

                            <div
                                className="roster-status"
                                role="radiogroup"
                                aria-label={`Attendance for ${name}`}
                            >
                                {ATTENDANCE_STATUSES.map((status) => {
                                    const on = row.mark === status;
                                    return (
                                        <button
                                            key={status}
                                            type="button"
                                            role="radio"
                                            aria-checked={on}
                                            disabled={disabled || !row.active}
                                            className={cn(
                                                "chip",
                                                `chip-${(row.mark ?? "none").toLowerCase()}`,
                                                on && "chip-on",
                                                on && row.locked && "chip-locked",
                                            )}
                                            onClick={() => onSetMark(row.studentId, status)}
                                        >
                                            {status}
                                        </button>
                                    );
                                })}
                            </div>
                        </div>
                    );
                })
            )}
        </div>
    );
}
