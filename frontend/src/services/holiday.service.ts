import { api } from "@/lib/api/client";
import { toCamel } from "@/lib/api/case";
import type {
    ClosureDelete,
    ClosureImpact,
    HolidayCalendar,
    HolidayImpact,
    SchoolOpenDay,
    WeeklyOffDays,
} from "@/types";

// The school's calendar (Phase 3.5). One set of holidays for every class, so none of
// these calls names a section: the server decides the school, the dates decide the rest.

/** What the form sends: one day, or a range (`endDate` empty). */
export interface HolidayInput {
    name: string;
    kind: string;
    startDate: string;
    endDate?: string | null;
}

/** Holidays, weekly offs and the days that already have a register, for a window. */
export async function getHolidayCalendar(from: string, to: string): Promise<HolidayCalendar> {
    const payload = await api.get<unknown>(`/attendance/holidays?from=${from}&to=${to}`);
    return toCamel<HolidayCalendar>(payload);
}

function body(input: HolidayInput) {
    return {
        name: input.name,
        kind: input.kind,
        start_date: input.startDate,
        end_date: input.endDate || null,
    };
}

export async function createHoliday(input: HolidayInput): Promise<HolidayImpact> {
    const payload = await api.post<unknown>("/attendance/holidays", body(input));
    return toCamel<HolidayImpact>(payload);
}

export async function updateHoliday(id: string, input: HolidayInput): Promise<HolidayImpact> {
    const payload = await api.patch<unknown>(`/attendance/holidays/${id}`, body(input));
    return toCamel<HolidayImpact>(payload);
}

export async function deleteHoliday(id: string): Promise<void> {
    await api.delete(`/attendance/holidays/${id}`);
}

/**
 * Reopen **one** date a weekly off (or a holiday) closes - "just this day".
 *
 * The weekly-off setting is untouched: every other Sunday stays closed, and the register may
 * be taken on this one date. `409` when the day is already open, or already reopened.
 */
export async function markOpenDay(date: string): Promise<SchoolOpenDay> {
    const payload = await api.post<unknown>("/attendance/open-days", { on_date: date });
    return toCamel<SchoolOpenDay>(payload);
}

/** Close the date again - the rule (or the holiday) takes over exactly as before. */
export async function clearOpenDay(date: string): Promise<void> {
    await api.delete(`/attendance/open-days/${date}`);
}

export async function getWeeklyOff(): Promise<WeeklyOffDays> {
    const payload = await api.get<unknown>("/attendance/weekly-off");
    return toCamel<WeeklyOffDays>(payload);
}

/**
 * The Calendar page's three cards: how many holidays, and how many vacation days.
 *
 * With no dates the window is the school's current **session** (`AcademicYear.is_current`),
 * falling back to the calendar year - "this year" has to mean the school's year.
 */
export async function setWeeklyOff(days: number[], nth?: string[]): Promise<WeeklyOffDays> {
    const payload = await api.put<unknown>("/attendance/weekly-off", { days, nth });
    return toCamel<WeeklyOffDays>(payload);
}

/**
 * What a closure of this window would throw away - by class-section, by name.
 *
 * With `days`/`nth` it can answer for a **proposed** weekly-off setting too, but the card no
 * longer asks: a rule never closes a day that already has a register, so the answer would
 * always be zero. Reading never deletes.
 */
export async function getClosureImpact(
    from: string,
    to: string,
    options: { days?: number[]; nth?: string[] } = {},
): Promise<ClosureImpact> {
    const query = new URLSearchParams({ from, to });
    for (const day of options.days ?? []) query.append("days", String(day));
    for (const token of options.nth ?? []) query.append("nth", token);
    const payload = await api.get<unknown>(`/attendance/closure-impact?${query}`);
    return toCamel<ClosureImpact>(payload);
}

/**
 * Delete the register rows of the days being closed - **only** after the warning is confirmed.
 *
 * `dates` is the safe form (exactly the days the warning listed); a holiday's own range sends
 * `from`/`to` instead, because there the range *is* the closure.
 */
export async function deleteClosureRecords(input: {
    from?: string;
    to?: string;
    dates?: string[];
    sectionIds?: string[];
}): Promise<ClosureDelete> {
    const payload = await api.post<unknown>("/attendance/closure-impact/delete", {
        from_date: input.from ?? null,
        to_date: input.to ?? null,
        dates: input.dates ?? [],
        section_ids: input.sectionIds ?? [],
    });
    return toCamel<ClosureDelete>(payload);
}
