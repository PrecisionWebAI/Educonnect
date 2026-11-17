import type { BellSlot } from "@/types";
import type { TimetablePeriodItem } from "@/services";

/**
 * The timetable grid's rules, as **pure functions**.
 *
 * The day's shape now comes from the school's own `bell_schedule` rows, so the grid
 * cannot carry a six-period array of its own: these functions turn the bell slots and
 * the week's periods into what the table draws, and `node --test` covers the parts that
 * would otherwise only be checked by looking at a screen.
 */

/** A row of the grid's body. */
export interface DayRow {
    /** "P1" … "Break". */
    label: string;
    /** `HH:MM`. */
    start: string;
    end: string;
    isBreak: boolean;
    /** The cell key a period is matched on: `start-end`. */
    key: string;
}

/** `"08:00:00"` -> `"08:00"` (the API sends seconds, the grid does not). */
export function hhmm(value: string): string {
    return value.slice(0, 5);
}

/**
 * The grid's rows, in the order the school runs its day.
 *
 * A break keeps its place: dropping it would make "P3" sit directly under "P2" and hide
 * the fact that the class has a gap there.
 */
export function dayRows(slots: BellSlot[]): DayRow[] {
    return [...slots]
        .sort((a, b) => a.periodNo - b.periodNo)
        .map((slot) => {
            const start = hhmm(slot.startTime);
            const end = hhmm(slot.endTime);
            return {
                label: slot.label,
                start,
                end,
                isBreak: slot.isBreak,
                key: `${start}-${end}`,
            };
        });
}

/** The period in one cell, or `undefined` when the slot is free. */
export function cellPeriod(
    periods: TimetablePeriodItem[],
    day: string,
    row: DayRow,
): TimetablePeriodItem | undefined {
    return periods.find(
        (period) => period.dayOfWeek === day && hhmm(period.startTime) === row.start,
    );
}

/**
 * Which bell slot a saved period starts in, for a diary line or a sorted list.
 *
 * `""` when the period starts outside the school's day - a slot written before the bell
 * schedule existed, which the grid still draws rather than losing.
 */
export function slotLabelAt(slots: BellSlot[], start: string): string {
    const slot = slots.find((item) => hhmm(item.startTime) === hhmm(start));
    return slot ? slot.label : "";
}

/** The rows the grid must draw: the bell slots, plus any saved period outside them. */
export function gridRows(slots: BellSlot[], periods: TimetablePeriodItem[]): DayRow[] {
    const rows = dayRows(slots);
    const known = new Set(rows.map((row) => row.start));
    const extra = periods
        .filter((period) => !known.has(hhmm(period.startTime)))
        .map((period) => ({
            label: "",
            start: hhmm(period.startTime),
            end: hhmm(period.endTime),
            isBreak: false,
            key: `${hhmm(period.startTime)}-${hhmm(period.endTime)}`,
        }));
    // A period outside the bell schedule is still on the week, so it still gets a row.
    return [...rows, ...extra].sort((a, b) => (a.start < b.start ? -1 : 1));
}
