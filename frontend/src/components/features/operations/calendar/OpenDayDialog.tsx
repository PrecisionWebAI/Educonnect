"use client";

import { Button, Modal } from "@/components/ui";
import { dayLabel } from "@/lib/attendance/view";

// "Just this day": the calendar's one-date override.
//
// A weekly off (every Sunday, "the 2nd Saturday") and a holiday row close a day for the
// whole school. An exam or a make-up class needs one date back **without** unsaving the
// rule - turning "Sunday off" off and on again would reopen every Sunday of the year - so
// this dialog offers exactly one thing besides Cancel, and the date is all it changes.
//
// `reopened` flips the same dialog: a date that already carries an override offers "close it
// again". A register saved on that date is never deleted by either direction - the office
// takes a register on the day, and a weekly off never takes back a marked day.
export default function OpenDayDialog({
    open,
    date,
    reason,
    reopened = false,
    busy = false,
    onCancel,
    onConfirm,
}: {
    open: boolean;
    /** The date the calendar was clicked on (`YYYY-MM-DD`). */
    date: string;
    /** Why the day is closed, in the calendar's own words ("Sunday", "Diwali break"). */
    reason?: string;
    /** True when the date is already open on purpose - the dialog offers to close it. */
    reopened?: boolean;
    busy?: boolean;
    onCancel: () => void;
    onConfirm: () => void;
}) {
    return (
        <Modal
            open={open}
            title={reopened ? "Close this day again?" : "Open just this day?"}
            onClose={onCancel}
        >
            <div className="space-y-3 text-sm">
                <p>
                    <strong>{dayLabel(date)}</strong>
                    {reason ? ` · ${reason}` : ""}
                </p>

                <p className="text-muted-foreground">
                    {reopened
                        ? "This date was opened on purpose. Closing it again hands the date back to the rule - a register already saved here stays, and keeps counting."
                        : "This date is closed for the whole school. Opening it does not change the weekly off or the holiday: every other matching day stays closed, and a register can be taken here."}
                </p>

                <div className="modal-actions">
                    <Button variant="ghost" onClick={onCancel} disabled={busy}>
                        Cancel
                    </Button>
                    <Button
                        variant={reopened ? "outline" : "primary"}
                        onClick={onConfirm}
                        disabled={busy}
                    >
                        {busy
                            ? "Saving…"
                            : reopened
                              ? "Close this day again"
                              : "Open just this day"}
                    </Button>
                </div>
            </div>
        </Modal>
    );
}
