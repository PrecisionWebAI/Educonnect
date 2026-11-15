import type { AttendanceTrendPoint, ClosedDay, RegisterRow } from "@/types";

/**
 * The register's rules, as **pure functions**.
 *
 * They live here (not inside the hook) for two reasons: the screen stays readable, and
 * the rules can be tested without a browser. The repository has no component-test stack
 * (no vitest/jest), so `view.test.ts` runs on Node's built-in runner instead of adding
 * one - see the Phase 4 notes in `backend/phase.md`.
 *
 * Everything the backend decides (a percentage, a threshold flag, a leave day) arrives
 * decided; this module only chooses the **words and the colours** for it.
 */

/** The four chips a teacher can press. `half_day` has no chip of its own. */
export const CHIP_STATUSES = ["Present", "Absent", "Late", "Leave"] as const;
export type ChipStatus = (typeof CHIP_STATUSES)[number];

const LABELS: Record<string, ChipStatus | "Half day" | "Unmarked"> = {
    present: "Present",
    absent: "Absent",
    late: "Late",
    leave: "Leave",
    half_day: "Half day",
    unmarked: "Unmarked",
};

/** The statuses a saved row may contribute to the editable grid (never `leave`). */
const PRELOAD: Record<string, ChipStatus> = {
    present: "Present",
    absent: "Absent",
    late: "Late",
};

/** What the row's chip says for a stored status. */
export function chipLabel(status: string): ChipStatus | "Half day" | "Unmarked" {
    return LABELS[status] ?? "Unmarked";
}

/** The value a chip writes to the register. */
export function storedStatus(chip: ChipStatus): string {
    return chip.toLowerCase();
}

/**
 * Pre-fill the grid from the saved register.
 *
 * Only a mark a teacher actually made becomes a chip:
 *
 * * `leave` is **derived** from an approved request (`service.register`). Pre-loading it
 *   would make the next Save write `leave` into the row, and cancelling the request
 *   would then no longer revert to the mark - the one thing the derivation exists to
 *   guarantee. So a leave row is shown, never re-sent.
 * * `half_day` has no chip of its own, and `unmarked` is the absence of a mark.
 */
export function marksFromRows(rows: RegisterRow[]): Record<string, ChipStatus> {
    const marks: Record<string, ChipStatus> = {};
    for (const row of rows) {
        const label = PRELOAD[row.status];
        if (label) marks[row.studentId] = label;
    }
    return marks;
}

/** "yyyy-MM-dd" for a Date in **local** time (the picker's own format). */
export function isoDate(date: Date): string {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
}

/** Why the school is closed that day ("Sunday", "Diwali break"), or `null`. */
export function closedReasonOn(days: ClosedDay[], iso: string): string | null {
    return days.find((day) => day.date === iso)?.reason ?? null;
}

/** Should the picker refuse this day? (Sundays and the school's holidays.) */
export function isClosedDay(days: ClosedDay[], date: Date): boolean {
    return days.some((day) => day.date === isoDate(date));
}

export type ThresholdTone = "none" | "ok" | "below";

/**
 * The threshold chip: `below` when the child is under the school's mark, `ok` when at
 * or above it, and `none` when there is no data - a `0%` would accuse a child nobody
 * has marked yet.
 */
export function thresholdTone(
    percent: number | null | undefined,
    threshold: number,
): ThresholdTone {
    if (percent === null || percent === undefined) return "none";
    return percent < threshold ? "below" : "ok";
}

/** The trend as bars: open days that were marked, labelled by weekday. */
export function trendBars(points: AttendanceTrendPoint[]): { label: string; value: number }[] {
    return points
        .filter((point) => point.percent !== null && point.percent !== undefined)
        .map((point) => ({
            label: weekdayLabel(point.date),
            value: Math.round(point.percent as number),
        }));
}

/** "Mon" for "2026-11-16" - the chart's own label. */
export function weekdayLabel(iso: string): string {
    const date = new Date(`${iso}T00:00:00`);
    return Number.isNaN(date.getTime())
        ? iso
        : date.toLocaleDateString("en-IN", { weekday: "short" });
}
