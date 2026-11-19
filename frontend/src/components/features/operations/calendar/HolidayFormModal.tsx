"use client";

import { useMemo, useState } from "react";
import { Button, Input, Modal, Select } from "@/components/ui";
import { DatePicker } from "@/components/ui/date-picker";
import { useApiQuery } from "@/lib/api/use-api-query";
import { isoDate, rangeLabel } from "@/lib/attendance/view";
import { titleCase } from "@/lib/format";
import { deleteClosureRecords, getClosureImpact } from "@/services";
import type { HolidayInput } from "@/services";
import type { SchoolHoliday } from "@/types";
import ClosureImpactDialog from "./ClosureImpactDialog";

// Add or edit one holiday: a single day, or a range that may cross a month.
//
// The form warns about the two things a school can actually break:
//
//   * **a day already has a holiday** - two names for one day make every count ambiguous, so
//     the save stays shut and the message names the holiday to edit instead;
//   * **a day already has a register** - the button turns red and says "Delete N & save".
//     Pressing it opens the confirm, which names the class-sections and the rows; only that
//     confirm calls the delete. Cancel leaves everything exactly as it was.
//
// The same is true of **every** type, the "Weekly off" one included - a dated closure is a
// decision taken now. The Weekly off **card** is the other way round: it never deletes, and
// a day that already has a register is never closed by a rule.

/**
 * The one kind that is not a holiday: a dated extra weekly off.
 *
 * It closes the day exactly the way a Sunday does - no register, no place in any
 * percentage - but it is kept out of the holiday list, the holiday counts and the
 * holiday colour, and it needs no name of its own.
 */
export const WEEK_OFF_VALUE = "week_off";

const KINDS = [
    { value: "public", label: "Public holiday" },
    { value: "school", label: "School holiday" },
    { value: "vacation", label: "Vacation" },
    { value: "other", label: "Other" },
    { value: WEEK_OFF_VALUE, label: "Weekly off" },
];

export default function HolidayFormModal({
    open,
    holiday,
    defaultDate,
    holidays,
    saving,
    removing = false,
    onClose,
    onDelete,
    onSubmit,
}: {
    open: boolean;
    /** The row being edited, or `null` when adding. */
    holiday: SchoolHoliday | null;
    /** The day the calendar was clicked on - the form opens on it. */
    defaultDate?: string | null;
    /** Every holiday the screen already knows - the overlap check reads this. */
    holidays: SchoolHoliday[];
    saving: boolean;
    /** True while the parent's delete call is in flight. */
    removing?: boolean;
    onClose: () => void;
    /** Edit mode only: remove this row. The parent confirms and closes the form. */
    onDelete?: () => Promise<void>;
    onSubmit: (input: HolidayInput) => Promise<void>;
}) {
    const today = isoDate(new Date());
    // Seeded once. The parent gives this form a `key` that changes with the row, the
    // clicked day and the open/closed state, so a fresh form is remounted rather than an
    // effect writing state while React renders.
    const [name, setName] = useState(holiday?.name ?? "");
    const [kind, setKind] = useState(
        holiday?.kind && KINDS.some((option) => option.value === holiday.kind)
            ? holiday.kind
            : "public",
    );
    const [start, setStart] = useState(holiday?.startDate ?? defaultDate ?? today);
    const [end, setEnd] = useState(
        holiday && holiday.endDate !== holiday.startDate ? holiday.endDate : "",
    );

    const last = end || start;

    const overlap = useMemo(
        () =>
            holidays.find(
                (row) => row.id !== holiday?.id && row.startDate <= last && row.endDate >= start,
            ),
        [holidays, holiday, start, last],
    );

    const datesValid = start <= last;
    const isWeekOff = kind === WEEK_OFF_VALUE;
    // A weekly off is described by its type; only a holiday has to be named.
    const canSave = (isWeekOff || Boolean(name.trim())) && datesValid && !overlap;

    // The confirm step, and what this closure would throw away (read, never written, until
    // the confirm).
    const [confirmOpen, setConfirmOpen] = useState(false);
    const [deleting, setDeleting] = useState(false);
    // Edit mode only: the row can be removed from here too, so a weekly off added by
    // mistake has a way out even though the card no longer lists those dates.
    const [deleteOpen, setDeleteOpen] = useState(false);
    const impactQuery = useApiQuery(
        ["attendance", "closure-impact", start, last],
        () => getClosureImpact(start, last),
        { enabled: open && datesValid },
    );
    const impact = impactQuery.data;
    const impactRecords = impact?.totalRecords ?? 0;
    const impactNames = Array.from(
        new Set(
            (impact?.days ?? []).flatMap((day) =>
                day.sections.map((section) =>
                    [section.className, section.sectionName].filter(Boolean).join(" - "),
                ),
            ),
        ),
    );

    /** Delete first, then save: a half-done pair is worse than neither. */
    async function submit() {
        if (impactRecords > 0) {
            setDeleting(true);
            try {
                await deleteClosureRecords({ from: start, to: last });
            } finally {
                setDeleting(false);
            }
        }
        await onSubmit({ name: name.trim(), kind, startDate: start, endDate: end || null });
        setConfirmOpen(false);
    }

    return (
        <>
            <Modal
                open={open}
                title={holiday ? "Edit day" : isWeekOff ? "Add weekly off" : "Add holiday"}
                onClose={onClose}
            >
                <div className="space-y-3">
                    {!isWeekOff && (
                        <Input
                            label="Holiday name"
                            value={name}
                            onChange={(event) => setName(event.target.value)}
                            placeholder="Diwali break"
                        />
                    )}
                    <Select
                        label="Type"
                        value={kind}
                        onChange={(event) => setKind(event.target.value)}
                    >
                        {KINDS.map((option) => (
                            <option key={option.value} value={option.value}>
                                {option.label}
                            </option>
                        ))}
                    </Select>
                    {isWeekOff && (
                        <p className="text-muted-foreground text-xs">
                            The day is closed the way a Sunday is - no register, and it leaves every
                            percentage. It is not a holiday, so it never appears in the holiday list
                            or in the holiday colour.
                        </p>
                    )}
                    <div className="form-grid">
                        <DatePicker label="First day" value={start} onChange={setStart} />
                        <DatePicker
                            label="Last day"
                            value={end}
                            onChange={setEnd}
                            placeholder="Same day"
                        />
                    </div>

                    {!datesValid && (
                        <p className="text-sm text-red-500" role="alert">
                            A holiday cannot end before it starts.
                        </p>
                    )}

                    {overlap && (
                        <p className="text-sm text-amber-600" role="alert">
                            {overlap.kind === WEEK_OFF_VALUE
                                ? `The school is already closed on ${rangeLabel(overlap.startDate, overlap.endDate)} as a weekly off.`
                                : `${titleCase(overlap.name)} already covers ${rangeLabel(overlap.startDate, overlap.endDate)}.`}{" "}
                            A day holds one closure - open that row in the calendar to change it,
                            instead of adding a second one beside it.
                        </p>
                    )}

                    {impactRecords > 0 && (
                        <p className="text-sm text-amber-600" role="status">
                            {impactRecords} attendance{" "}
                            {impactRecords === 1 ? "record is" : "records are"} already saved here
                            {impactNames.length > 0 ? ` (${impactNames.join(", ")})` : ""}. Saving
                            asks you to delete them - a day cannot be both marked and closed.
                        </p>
                    )}

                    <div className="modal-actions">
                        {holiday && onDelete && (
                            <Button
                                variant="ghost"
                                className="mr-auto text-red-600"
                                onClick={() => setDeleteOpen(true)}
                                disabled={saving || deleting || removing}
                            >
                                Delete
                            </Button>
                        )}
                        <Button variant="ghost" onClick={onClose} disabled={saving || deleting}>
                            Cancel
                        </Button>
                        <Button
                            variant={impactRecords > 0 ? "danger" : "primary"}
                            disabled={!canSave || saving || deleting}
                            onClick={() => {
                                if (impactRecords > 0) {
                                    setConfirmOpen(true);
                                    return;
                                }
                                void submit();
                            }}
                        >
                            {saving || deleting
                                ? "Saving…"
                                : overlap
                                  ? "Change the dates"
                                  : impactRecords > 0
                                    ? `Delete ${impactRecords} & save`
                                    : "Save"}
                        </Button>
                    </div>
                </div>
            </Modal>

            {impact && (
                <ClosureImpactDialog
                    open={confirmOpen}
                    title={isWeekOff ? "Close this day as a weekly off?" : "Close this day?"}
                    impact={impact}
                    busy={saving || deleting}
                    onCancel={() => setConfirmOpen(false)}
                    onConfirm={() => void submit()}
                />
            )}
            {holiday && onDelete && (
                <Modal
                    open={deleteOpen}
                    title="Delete this closure?"
                    onClose={() => setDeleteOpen(false)}
                >
                    <div className="space-y-3 text-sm">
                        <p>
                            <strong>{isWeekOff ? "Weekly off" : titleCase(holiday.name)}</strong>
                            {` · ${rangeLabel(holiday.startDate, holiday.endDate)}`}
                        </p>
                        <p className="text-muted-foreground">
                            The date becomes a working day again for every class. Attendance rows
                            that were deleted when the day was closed do not come back - the
                            register opens empty.
                        </p>
                        <div className="modal-actions">
                            <Button
                                variant="ghost"
                                onClick={() => setDeleteOpen(false)}
                                disabled={removing}
                            >
                                Cancel
                            </Button>
                            <Button
                                variant="danger"
                                onClick={() => void onDelete()}
                                disabled={removing}
                            >
                                {removing ? "Deleting…" : "Delete"}
                            </Button>
                        </div>
                    </div>
                </Modal>
            )}
        </>
    );
}
