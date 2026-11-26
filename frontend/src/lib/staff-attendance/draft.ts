import type { StaffAttendanceRow } from "@/types";

/**
 * Unsaved changes to a day's staff register.
 *
 * Changing a row's dropdown does **not** write anything: it is kept here as a draft, the
 * row says "Unsaved", and the cards above keep describing what is actually saved. One press
 * of "Save attendance" sends every draft in a single call, and only then do the cards move.
 * These are the pure rules; the tab owns the state and the button.
 */

/** The three words a person may record. */
export type DraftStatus = "present" | "absent" | "half_day";

/** `{employee id: the status chosen but not saved yet}`. */
export type Draft = Record<string, DraftStatus>;

/**
 * The draft after one dropdown change.
 *
 * Choosing what is **already saved** removes the draft (nothing changed, so nothing to
 * save and no "Unsaved" mark); anything else replaces the draft for that person.
 */
export function withDraftValue(
    draft: Draft,
    row: Pick<StaffAttendanceRow, "employeeId" | "isMarked" | "status">,
    value: DraftStatus,
): Draft {
    const saved = row.isMarked ? row.status : null;
    const next = { ...draft };
    if (value === saved) delete next[row.employeeId];
    else next[row.employeeId] = value;
    return next;
}

/**
 * What "Save attendance" sends: one entry per drafted person, in the register's order.
 *
 * The row's existing remarks travel with it - the server writes the remarks it is given, so
 * leaving them out would blank a note the office had written.
 */
export function draftEntries(
    rows: Pick<StaffAttendanceRow, "employeeId" | "remarks">[],
    draft: Draft,
): { employeeId: string; status: DraftStatus; remarks: string | null }[] {
    return rows
        .filter((row) => draft[row.employeeId] !== undefined)
        .map((row) => ({
            employeeId: row.employeeId,
            status: draft[row.employeeId],
            remarks: row.remarks ?? null,
        }));
}
