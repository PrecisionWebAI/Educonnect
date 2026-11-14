"use client";
import { useState } from "react";
import { Button, Input, Label, Select, Spinner, Table } from "@/components/ui";
import {
    Sheet,
    SheetContent,
    SheetDescription,
    SheetHeader,
    SheetTitle,
} from "@/components/ui/sheet";
import { errorMessage } from "@/lib/api/client";
import type { StaffDutyInput } from "@/services";
import type { StaffDutyRows } from "./useWorkload";
import { useStaffWeek } from "./useWorkload";

/**
 * The duty types the API accepts (`labels.DUTY_TYPES` on the server).
 *
 * A copy on purpose, exactly like the drawer's `DOCUMENTS` list: the screen has to
 * offer the list before it can read a row. The server refuses anything outside
 * its own vocabulary with a `422` naming the allowed values, so a stale copy
 * fails loudly instead of quietly filing a duty nobody can filter.
 */
const DUTIES = [
    { value: "exam_duty", label: "Exam Duty" },
    { value: "gate_duty", label: "Gate Duty" },
    { value: "assembly", label: "Assembly" },
    { value: "library", label: "Library" },
    { value: "bus_escort", label: "Bus Escort" },
    { value: "club", label: "Club" },
    { value: "sports", label: "Sports" },
    { value: "other", label: "Other" },
];

/** The days a weekly duty can repeat on, Monday first (`labels.WEEK_DAYS`). */
const DAYS = [
    { value: "monday", label: "Monday" },
    { value: "tuesday", label: "Tuesday" },
    { value: "wednesday", label: "Wednesday" },
    { value: "thursday", label: "Thursday" },
    { value: "friday", label: "Friday" },
    { value: "saturday", label: "Saturday" },
    { value: "sunday", label: "Sunday" },
];

/**
 * `Monday · 09:00-11:00`, the date for a one-off, or `Standing` for a duty with
 * neither - the three shapes a duty can have, in the words the row carries.
 */
function whenLabel(duty: StaffDutyRows[number]): string {
    const when = duty.dayLabel ?? (duty.onDate ? duty.onDate : "Standing");
    return duty.slot ? `${when} · ${duty.slot}` : when;
}

/**
 * One person's week: the grid, and the duties that sit beside it.
 *
 * The grid draws **every day of the week**, empty columns included, because
 * "nothing on Wednesday" is a fact a principal is looking for - a grid that drops
 * empty days makes it invisible. Periods and duties share a row when they start
 * together: a teacher does not experience them as two weeks.
 */
export default function StaffWeekSheet({
    teacherId,
    onClose,
    canManage,
    busy,
    error,
    onAddDuty,
    onRemoveDuty,
}: {
    teacherId: string | null;
    onClose: () => void;
    /** `teachers.manage_workload` - without it the form and Remove are hidden. */
    canManage: boolean;
    /** Which write is in flight, so its own button can show it. */
    busy: string | null;
    error: unknown;
    onAddDuty: (teacherId: string, input: StaffDutyInput) => Promise<boolean>;
    onRemoveDuty: (teacherId: string, dutyId: string) => Promise<boolean>;
}) {
    const { week, duties, loading, error: loadError } = useStaffWeek(teacherId);
    const [dutyType, setDutyType] = useState("exam_duty");
    const [day, setDay] = useState("monday");
    const [start, setStart] = useState("");
    const [end, setEnd] = useState("");
    const [title, setTitle] = useState("");

    const days = week?.days ?? [];
    /**
     * The grid's rows: every start time in the week, ascending.
     *
     * `09:00-10:00` sorts correctly as text because the clock is zero-padded, so
     * the rows need no date parsing - and a duty with no hours has an empty
     * `slot`, which is why it is listed below the grid instead of in it.
     */
    const slots = Array.from(
        new Set(days.flatMap((column) => column.slots.map((slot) => slot.slot))),
    )
        .filter((slot) => slot !== "")
        .sort();

    async function submit() {
        const saved = await onAddDuty(teacherId as string, {
            dutyType,
            title: title.trim() || null,
            dayOfWeek: day,
            onDate: null,
            startTime: start || null,
            endTime: end || null,
        });
        if (saved) {
            setTitle("");
            setStart("");
            setEnd("");
        }
    }

    return (
        <Sheet open={teacherId !== null} onOpenChange={(open) => !open && onClose()}>
            <SheetContent
                side="right"
                className="flex w-full flex-col overflow-y-auto border-l border-(--border-subtle) bg-(--background) p-0 sm:max-w-3xl"
            >
                <div className="flex-1 p-6">
                    <SheetHeader className="mb-4 text-left">
                        <SheetTitle className="text-xl font-bold">
                            {week ? week.name : "Teaching Week"}
                        </SheetTitle>
                        <SheetDescription className="text-muted-foreground">
                            {week
                                ? `${week.department} · ${week.periods} periods · ${week.duties} duties · ${week.emptyDays} free days`
                                : "Loading…"}
                        </SheetDescription>
                    </SheetHeader>

                    {loading && <Spinner />}

                    {loadError !== null && (
                        <p style={{ color: "var(--danger, #b42318)" }}>
                            {errorMessage(loadError, "This week could not be loaded.")}
                        </p>
                    )}

                    {error !== null && (
                        <p className="mb-3 text-sm" style={{ color: "var(--danger, #b42318)" }}>
                            {errorMessage(error, "That change was not saved.")}
                        </p>
                    )}

                    {week && slots.length === 0 && (
                        <p className="text-muted-foreground rounded-md border border-dashed p-6 text-center text-sm">
                            Nothing is scheduled in this week.
                        </p>
                    )}

                    {week && slots.length > 0 && (
                        <div className="table-wrap">
                            <table className="tt-table">
                                <thead>
                                    <tr>
                                        <th>Slot</th>
                                        {days.map((column) => (
                                            <th key={column.day}>{column.dayLabel}</th>
                                        ))}
                                    </tr>
                                </thead>
                                <tbody>
                                    {slots.map((slot) => (
                                        <tr key={slot}>
                                            <th className="tt-period">
                                                <b>{slot}</b>
                                            </th>
                                            {days.map((column) => {
                                                const cells = column.slots.filter(
                                                    (entry) => entry.slot === slot,
                                                );
                                                return (
                                                    <td key={`${column.day}-${slot}`}>
                                                        {cells.length === 0 ? (
                                                            <div className="tt-cell tt-empty">
                                                                <span>·</span>
                                                            </div>
                                                        ) : (
                                                            cells.map((cell) => (
                                                                <div
                                                                    key={
                                                                        cell.periodId ??
                                                                        cell.dutyId ??
                                                                        cell.subject
                                                                    }
                                                                    className="tt-cell"
                                                                >
                                                                    <b>{cell.subject}</b>
                                                                    <small>
                                                                        {cell.kind === "duty"
                                                                            ? (cell.title ?? "Duty")
                                                                            : (cell.classLabel ??
                                                                              cell.room ??
                                                                              "")}
                                                                    </small>
                                                                </div>
                                                            ))
                                                        )}
                                                    </td>
                                                );
                                            })}
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}

                    <h3 className="mt-6 mb-2 text-sm font-semibold">Duties</h3>
                    <Table
                        columns={[
                            {
                                key: "dutyTypeLabel",
                                header: "Duty",
                                render: (row: StaffDutyRows[number]) => (
                                    <div style={{ lineHeight: 1.3 }}>
                                        <div>{row.dutyTypeLabel}</div>
                                        {row.title && (
                                            <div
                                                style={{
                                                    color: "var(--muted)",
                                                    fontSize: "0.74rem",
                                                }}
                                            >
                                                {row.title}
                                            </div>
                                        )}
                                    </div>
                                ),
                            },
                            {
                                key: "when",
                                header: "When",
                                render: (row: StaffDutyRows[number]) => whenLabel(row),
                            },
                            {
                                key: "hours",
                                header: "Hours",
                                render: (row: StaffDutyRows[number]) =>
                                    row.hours > 0 ? row.hours : "—",
                            },
                            ...(canManage
                                ? [
                                      {
                                          key: "actions",
                                          header: "",
                                          render: (row: StaffDutyRows[number]) => (
                                              <Button
                                                  size="sm"
                                                  variant="ghost"
                                                  loading={busy === "duty"}
                                                  onClick={() =>
                                                      onRemoveDuty(teacherId as string, row.id)
                                                  }
                                              >
                                                  Remove
                                              </Button>
                                          ),
                                      },
                                  ]
                                : []),
                        ]}
                        rows={duties}
                        rowKey={(row) => row.id}
                        empty="No duties on this file yet."
                    />

                    {canManage && (
                        <>
                            <h3 className="mt-6 mb-2 text-sm font-semibold">Add Duty</h3>
                            <div className="grid gap-3 sm:grid-cols-2">
                                <div>
                                    <Label htmlFor="duty-type">Duty Type</Label>
                                    <Select
                                        id="duty-type"
                                        value={dutyType}
                                        onChange={(event) => setDutyType(event.target.value)}
                                    >
                                        {DUTIES.map((option) => (
                                            <option key={option.value} value={option.value}>
                                                {option.label}
                                            </option>
                                        ))}
                                    </Select>
                                </div>
                                <div>
                                    <Label htmlFor="duty-day">Day</Label>
                                    <Select
                                        id="duty-day"
                                        value={day}
                                        onChange={(event) => setDay(event.target.value)}
                                    >
                                        {DAYS.map((option) => (
                                            <option key={option.value} value={option.value}>
                                                {option.label}
                                            </option>
                                        ))}
                                    </Select>
                                </div>
                                <div>
                                    <Label htmlFor="duty-start">Start Time</Label>
                                    <Input
                                        id="duty-start"
                                        type="time"
                                        value={start}
                                        onChange={(event) => setStart(event.target.value)}
                                    />
                                </div>
                                <div>
                                    <Label htmlFor="duty-end">End Time</Label>
                                    <Input
                                        id="duty-end"
                                        type="time"
                                        value={end}
                                        onChange={(event) => setEnd(event.target.value)}
                                    />
                                </div>
                                <div className="sm:col-span-2">
                                    <Label htmlFor="duty-title">Title</Label>
                                    <Input
                                        id="duty-title"
                                        placeholder="Half-Yearly Exam - Hall B"
                                        value={title}
                                        onChange={(event) => setTitle(event.target.value)}
                                    />
                                </div>
                            </div>
                            <div className="mt-3 flex justify-end">
                                <Button loading={busy === "duty"} onClick={submit}>
                                    Add Duty
                                </Button>
                            </div>
                        </>
                    )}
                </div>
            </SheetContent>
        </Sheet>
    );
}
