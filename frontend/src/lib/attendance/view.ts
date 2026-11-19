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

/** The three chips a teacher can press. `half_day` has no chip of its own. */
export const CHIP_STATUSES = ["Present", "Absent", "Late"] as const;
export type ChipStatus = (typeof CHIP_STATUSES)[number];

const LABELS: Record<string, ChipStatus | "Half day" | "Unmarked"> = {
    present: "Present",
    absent: "Absent",
    late: "Late",
    // An approved leave is shown as an absence here, exactly as the row marks it.
    leave: "Absent",
    half_day: "Half day",
    unmarked: "Unmarked",
};

/** The statuses a saved row may contribute to the editable grid. */
const PRELOAD: Record<string, ChipStatus> = {
    present: "Present",
    absent: "Absent",
    late: "Late",
    // An approved leave is decided in Leave & Applications; here the day is simply
    // recorded as an absence, so the row shows a mark the teacher can see and count.
    leave: "Absent",
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
 * A `leave` is still never written back: the server derives it from the approved request,
 * so a cancelled leave reverts to the real mark. The day itself reads as **Absent** here
 * (the spec: "here it is simply recorded as Absent"), which is what the cards and the
 * percentage count as well.
 *
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

/** One child as the register shows them. */
export interface DayRow {
    studentId: string;
    /** The name as the server sent it; the row prints it in Title Case. */
    name: string;
    /** This session's edit first, else the saved mark. */
    mark: ChipStatus | undefined;
    /**
     * The saved row was a **half day**. There is no chip for it, so the row says so
     * beside the name instead of pretending the day was unmarked.
     */
    halfDay: boolean;
    /** Present + late in the month the calendar shows (from the summary); the row prints it. */
    monthPresent?: number;
    /**
     * Open days of that month up to its cutoff - the `/12` in `Monthly attendance 5/12`.
     * An open day nobody marked still counts: the denominator is the calendar.
     */
    monthOpen?: number;
    /** Registers actually taken that month; zero means the row prints a dash. */
    monthSaved?: number;
    /** The annual percentage: (present + late) over the open days, up to the chosen day. */
    yearPercent?: number | null;
    /**
     * The mark came from the saved register and this session has not touched it, so the
     * chip shows the locked shade. Any tap on the row unlocks it again.
     */
    locked: boolean;
    /** False for a child who has left: still listed, but the chips cannot be pressed. */
    active: boolean;
}

/** The day's numbers, all counted from the same rows the teacher is looking at. */
export interface DayCounts {
    present: number;
    absent: number;
    late: number;
    marked: number;
    unmarked: number;
    total: number;
}

export interface DayModel {
    rows: DayRow[];
    counts: DayCounts;
    /** Rows the server already holds a mark for. */
    savedCount: number;
    /** Rows this session changed but has not saved. */
    draftCount: number;
    /**
     * True once the day has a saved mark. The Present/Absent/Late cards print a dash
     * until then: a number printed before the first save would describe taps, not
     * attendance.
     */
    hasSaved: boolean;
    /** True while something is waiting to be saved. */
    isDirty: boolean;
}

/**
 * The register as one object - every card, the Save counter and the roster read from here.
 *
 * "What the database says" and "what I just tapped" are kept apart on purpose:
 * `savedCount` is the first, `draftCount` the second, and `mark` merges them (the edit
 * wins), which is what the teacher expects to see in the row.
 */
export function dayModel(rows: RegisterRow[], draft: Record<string, ChipStatus>): DayModel {
    const saved = marksFromRows(rows);
    const counts: DayCounts = {
        present: 0,
        absent: 0,
        late: 0,
        marked: 0,
        unmarked: 0,
        total: 0,
    };
    let savedCount = 0;

    const view = rows.map((row) => {
        const fromServer = saved[row.studentId];
        const fromDraft = draft[row.studentId];
        const mark = fromDraft ?? fromServer;
        // A child who has left is on the sheet but not on today's register, so the cards
        // and the Save counter speak about the children who are actually in the room.
        const onRoll = row.active !== false;
        if (onRoll) {
            counts.total += 1;
            if (fromServer) savedCount += 1;
            if (mark === "Present") counts.present += 1;
            else if (mark === "Absent") counts.absent += 1;
            else if (mark === "Late") counts.late += 1;
            if (mark) counts.marked += 1;
        }
        return {
            studentId: row.studentId,
            name: row.name,
            mark,
            halfDay: row.status === "half_day",
            locked: Boolean(fromServer) && !fromDraft,
            active: onRoll,
        };
    });

    counts.unmarked = counts.total - counts.marked;
    const draftCount = Object.keys(draft).length;
    return {
        rows: view,
        counts,
        savedCount,
        draftCount,
        hasSaved: savedCount > 0,
        isDirty: draftCount > 0,
    };
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

/** One bar of the trend: the server's label, the span it stands for, and the counts. */
export interface TrendBar {
    /** The x-axis label ("Sat", "3rd wk Nov", "Nov") - chosen by the server. */
    label: string;
    /** The first day of the span - the tooltip names it. */
    date: string;
    /** The last day of the span; equal to `date` for a single day. */
    end: string;
    /** The bar's height: the span's percentage. */
    value: number;
    present: number;
    marked: number;
}

/**
 * The trend as bars: the spans somebody marked, oldest first.
 *
 * The label comes from the server (a week is "3rd wk Nov", not a weekday), and a label
 * that repeats - two Mondays inside one window - is cut back to its date, so the axis
 * never shows the same word twice. A span with no marks is dropped rather than drawn as
 * 0%: "no data" is an answer, and zero is an accusation.
 */
export function trendBars(points: AttendanceTrendPoint[]): TrendBar[] {
    const bars = points
        .filter((point) => point.percent !== null && point.percent !== undefined)
        .map((point) => ({
            label: point.label?.trim() || weekdayLabel(point.date),
            date: point.date,
            end: point.endDate ?? point.date,
            value: Math.round(point.percent as number),
            present: point.present ?? 0,
            marked: point.marked ?? 0,
        }));
    const seen = new Map<string, number>();
    for (const bar of bars) seen.set(bar.label, (seen.get(bar.label) ?? 0) + 1);
    return bars.map((bar) =>
        (seen.get(bar.label) ?? 0) > 1 ? { ...bar, label: shortDateLabel(bar.date) } : bar,
    );
}

/** "2026-11-16" -> "16 Nov" - the axis word a repeated label falls back to. */
export function shortDateLabel(iso: string): string {
    const date = new Date(`${iso}T00:00:00`);
    return Number.isNaN(date.getTime())
        ? iso
        : date.toLocaleDateString("en-IN", { day: "numeric", month: "short" });
}

/**
 * The roster's roll numbers: 1..n in the order the server sent (alphabetical).
 *
 * Numbered **before** the search and the filter run, so a child's number never changes
 * because a classmate is hidden by a filter. A child who has left keeps their number in
 * place - the sheet is the section, not the children who happen to be present today.
 */
export function withRoll<T>(rows: T[]): (T & { roll: number })[] {
    return rows.map((row, index) => ({ ...row, roll: index + 1 }));
}

/** "Mon" for "2026-11-16" - the chart's own label. */
export function weekdayLabel(iso: string): string {
    const date = new Date(`${iso}T00:00:00`);
    return Number.isNaN(date.getTime())
        ? iso
        : date.toLocaleDateString("en-IN", { weekday: "short" });
}

/** "2026-11-21" -> "21 Nov 2026" - the day the chart's tooltip names. */
export function dayLabel(iso: string): string {
    const date = new Date(`${iso}T00:00:00`);
    return Number.isNaN(date.getTime())
        ? iso
        : date.toLocaleDateString("en-IN", {
              day: "numeric",
              month: "short",
              year: "numeric",
          });
}

/** A row that owns a range of dates - a holiday, or a dated extra weekly off. */
export interface DatedRow {
    startDate: string;
    endDate: string;
}

/**
 * The row that already covers `iso`, if any (both ends included).
 *
 * A day holds **one** closure, and the server refuses a second one. The calendar reads this
 * before it opens a form: a day that is already closed opens *that* row for editing instead
 * of offering an "add" that could only end in the overlap error.
 */
export function coveringRow<T extends DatedRow>(rows: T[], iso: string): T | null {
    return rows.find((row) => row.startDate <= iso && row.endDate >= iso) ?? null;
}

/**
 * A closure's dates in words: `"1 Oct 2026"` for one day, `"1 Oct – 15 Oct 2026"` for a range.
 *
 * One date prints once - the "2026-10-01 – 2026-10-01" a raw range produces reads like a
 * mistake, and it was one: the sentence is shown to the operator who clicked that day.
 */
export function rangeLabel(startIso: string, endIso: string): string {
    if (startIso === endIso) return dayLabel(startIso);
    const start = new Date(`${startIso}T00:00:00`);
    const end = new Date(`${endIso}T00:00:00`);
    if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) {
        return `${startIso} – ${endIso}`;
    }
    // The year is written once, at the end, unless the range crosses into another one.
    const short = start.toLocaleDateString("en-IN", {
        day: "numeric",
        month: "short",
        ...(start.getFullYear() === end.getFullYear() ? {} : { year: "numeric" }),
    });
    return `${short} – ${dayLabel(endIso)}`;
}

/** What the roster's filter dropdown shows: everything, or one mark. */
export type RosterFilter = "all" | ChipStatus;

/**
 * The rows a search word and the status filter leave on screen.
 *
 * Filtering is **display only**: the marks stay in `dayModel`, so narrowing the list never
 * drops a mark and nothing has to be re-tapped after clearing the filter.
 */
export function filterRoster<T extends { name: string; mark: ChipStatus | undefined }>(
    rows: T[],
    query: string,
    filter: RosterFilter,
): T[] {
    const needle = query.trim().toLowerCase();
    return rows.filter((row) => {
        if (needle && !row.name.toLowerCase().includes(needle)) return false;
        if (filter !== "all" && row.mark !== filter) return false;
        return true;
    });
}

/** The weekday names a weekly off is printed with - the same words the server sends. */
const WEEKDAY_NAMES = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
];

/**
 * Is this closed-day reason a weekly off ("Sunday") and not a holiday ("diwali break")?
 *
 * The server sends both through one field, and the screen prints them differently: a
 * weekly off says "Weekly off", a holiday says its own name.
 */
export function isWeeklyOffReason(reason: string | null | undefined): boolean {
    return Boolean(reason) && WEEKDAY_NAMES.includes(String(reason));
}

/**
 * The row's month figure: `Monthly attendance 5/12`.
 *
 * Twelve is the month's **open days** up to its cutoff - the days the school was open -
 * not the days somebody remembered to take the register: `10/22` is the honest reading of
 * a month that stopped being marked, while `10/10` would flatter it. A month with no
 * register at all (`taken` is 0) and a window with no open days are both a **dash**, never
 * `0/0` or `0/27`: "the register was not taken" and "nobody came" are not the same
 * sentence.
 */
export function monthFigure(
    present: number | undefined,
    open: number | undefined,
    taken: number | undefined,
): string {
    if (!open || !taken) return "Monthly attendance —";
    return `Monthly attendance ${present ?? 0}/${open}`;
}

/** Which colour a closed day wears. */
export type ClosedTone = "off" | "holiday";

/**
 * The colour of a closed day, from the `kind` the server sent - `weekly_off` and
 * `week_off` both read as a weekly off, because both close the day the way Sunday does.
 * The screen never matches the reason text: a holiday may be called anything.
 */
export function closedTone(kind: string | null | undefined): ClosedTone {
    return kind === "holiday" ? "holiday" : "off";
}

/** The nth-weekday token's words: `"5#1"` -> `"1st Saturday"`. */
export function nthOffLabel(token: string): string {
    const [weekday, nth] = String(token).split("#");
    const index = Number(weekday);
    const week = Number(nth);
    if (!Number.isInteger(index) || index < 0 || index > 6) return token;
    const ordinal = ["1st", "2nd", "3rd", "4th"][week - 1] ?? `${week}th`;
    return `${ordinal} ${WEEKDAY_NAMES[index]}`;
}
