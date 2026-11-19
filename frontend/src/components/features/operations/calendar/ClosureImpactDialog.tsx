"use client";

import { Button, Modal } from "@/components/ui";
import { dayLabel } from "@/lib/attendance/view";
import type { ClosureImpact } from "@/types";

// The warning a closure must show before it is saved.
//
// The holiday form (every type, "Weekly off" included) reads the impact first, so the office
// is shown **which class-sections** would lose a day, by name and by count, and has to press
// a destructive button. Nothing is deleted by merely picking a date, and Cancel changes
// nothing at all.
//
// The Weekly off **card** does not use this dialog: a rule never deletes a register, so it
// has nothing to warn about (see `admin/settings/calendar.closures`).
export default function ClosureImpactDialog({
    open,
    title,
    impact,
    busy = false,
    confirmLabel,
    onCancel,
    onConfirm,
}: {
    open: boolean;
    title: string;
    impact: ClosureImpact;
    busy?: boolean;
    confirmLabel?: string;
    onCancel: () => void;
    onConfirm: () => void;
}) {
    const days = impact.days.filter((day) => day.totalRecords > 0);
    // The names in one line, so the reader sees who is affected before the numbers.
    const names = Array.from(
        new Set(
            days.flatMap((day) =>
                day.sections.map((section) =>
                    [section.className, section.sectionName].filter(Boolean).join(" - "),
                ),
            ),
        ),
    );

    return (
        <Modal open={open} title={title} onClose={onCancel}>
            <div className="space-y-3 text-sm">
                <p className="text-amber-600" role="alert">
                    {impact.totalRecords} {impact.totalRecords === 1 ? "record is" : "records are"}{" "}
                    already saved on {days.length === 1 ? "this day" : "these days"}. Confirming
                    deletes them permanently - the day then becomes a non-working day for every
                    class.
                </p>

                {names.length > 0 && (
                    <p className="text-muted-foreground">
                        <strong>Class-sections:</strong> {names.join(", ")}
                    </p>
                )}

                <ul className="feed">
                    {days.map((day) => (
                        <li key={day.date} className="feed-item">
                            <div className="feed-body">
                                <span className="feed-title">
                                    {dayLabel(day.date)}
                                    {day.reason ? ` · ${day.reason}` : ""}
                                </span>
                                <span className="feed-sub">
                                    {day.sections
                                        .map(
                                            (section) =>
                                                `${
                                                    [section.className, section.sectionName]
                                                        .filter(Boolean)
                                                        .join(" - ") || "Section"
                                                } (${section.students} students, ${
                                                    section.records
                                                } rows)`,
                                        )
                                        .join(" · ")}
                                </span>
                            </div>
                        </li>
                    ))}
                </ul>

                <p className="text-muted-foreground text-xs">
                    This cannot be undone: the attendance rows and their change history are removed,
                    and the day will read as “not marked” if the closure is later cancelled.
                </p>

                <div className="modal-actions">
                    <Button variant="ghost" onClick={onCancel} disabled={busy}>
                        Cancel
                    </Button>
                    <Button variant="danger" onClick={onConfirm} disabled={busy}>
                        {busy
                            ? "Deleting…"
                            : (confirmLabel ??
                              `Delete ${impact.totalRecords} ${
                                  impact.totalRecords === 1 ? "record" : "records"
                              } & continue`)}
                    </Button>
                </div>
            </div>
        </Modal>
    );
}
