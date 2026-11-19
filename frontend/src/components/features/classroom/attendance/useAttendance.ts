"use client";

import { useCallback, useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
    getClosedDays,
    getSectionAttention,
    getSectionCalendar,
    getSectionLateLastMonth,
    getSectionRegister,
    getSectionSummary,
    getSectionTrend,
    markAttendanceBulk,
} from "@/services";
import { useApiQuery } from "@/lib/api/use-api-query";
import { useClassCatalog } from "@/hooks/use-class-catalog";
import {
    CHIP_STATUSES,
    closedReasonOn,
    dayModel,
    isoDate,
    marksFromRows,
    storedStatus,
    trendBars,
    type ChipStatus,
} from "@/lib/attendance/view";
import type {
    AttendanceAttentionRow,
    ClosedDay,
    RegisterRow,
    SectionCalendarDay,
    SectionRegister,
    SectionSummary,
    SectionTrend,
    StudentAttendanceTotal,
} from "@/types";

// ============================================================
// useAttendance — the register, and the three widgets beside it.
//
// Phase 4 replaces browser-side arithmetic with the server's answers:
//
//   * the **grid** is `GET /attendance/section/{id}?date=` - the whole roll, every
//     child marked *or* unmarked, a `leave` row where an approved request covers the
//     day. Opening a date pre-fills it; nothing is remembered in the browser.
//   * a **closed day** (Sunday, a holiday) comes back with its reason, so Save is
//     disabled and the toolbar says why.
//   * the **summary**, **trend** and **attention** widgets read their own endpoints -
//     the fake weekday percentages and the "marked absent today" list are gone.
//   * Save sends **only the rows the user changed**. The old flow sent every row with
//     `?? "Present"`, which silently marked the untouched children present.
// ============================================================

export const ATTENDANCE_STATUSES = CHIP_STATUSES;
export type Status = ChipStatus;

/**
 * Where the register is. Inside the Classroom screen the section is fixed by the page;
 * on the school-wide Attendance page the class/section pickers feed the same fields and
 * the catalogue turns them into the room id the API wants.
 */
export interface AttendanceScope {
    sectionId?: string;
    className?: string;
    section?: string;
}

/** The period the trend card draws. */
export type TrendRange = "week" | "month";

export function useAttendance(scope: AttendanceScope = {}) {
    const queryClient = useQueryClient();
    const catalog = useClassCatalog();

    const [className, setClassName] = useState(scope.className ?? "");
    const [section, setSection] = useState(scope.section ?? "");
    const [date, setDate] = useState(() => isoDate(new Date()));
    const [trendRange, setTrendRange] = useState<TrendRange>("week");
    // Only what this session changed: the saved register is the server's answer.
    // Keyed by (room, day), so changing either starts from the server again without an
    // effect that would reset state on every render.
    const [draftState, setDraftState] = useState<{
        key: string;
        marks: Record<string, Status>;
    }>({ key: "", marks: {} });
    const [saving, setSaving] = useState(false);

    /**
     * The room the register belongs to.
     *
     * A scope from the page wins; otherwise the pickers are resolved through the class
     * catalogue, so the school-wide page writes to the room it names instead of only
     * changing the cache (which is what it used to do).
     */
    const sectionId = useMemo(() => {
        if (scope.sectionId) return scope.sectionId;
        if (!className || !section) return undefined;
        return catalog.sectionsOf(className).find((item) => item.name === section)?.classroomId;
    }, [scope.sectionId, className, section, catalog]);

    // The register for the chosen day - the read the old screen never made.
    const registerQuery = useApiQuery(
        ["attendance", "register", sectionId ?? "none", date],
        () => getSectionRegister(sectionId as string, date),
        { enabled: Boolean(sectionId) },
    );
    const register: SectionRegister | undefined = registerQuery.data;

    // The whole year the chosen day belongs to (plus today's year, so stepping across New
    // Year still lands on a painted grid). A weekly off is a rule for **every** matching day
    // of that year, and the register refuses each of them - so the picker must not stop
    // shading at an arbitrary horizon two months out and then let a tap reach a day the API
    // will refuse. The chosen day is always read again on its own
    // (`/section/{id}?date=`), so Save stays exact even for a date outside this window.
    const closedWindow = useMemo(() => {
        const anchor = new Date(`${date}T00:00:00`);
        const year = anchor.getFullYear();
        const thisYear = new Date().getFullYear();
        return {
            from: isoDate(new Date(Math.min(year, thisYear), 0, 1)),
            to: isoDate(new Date(Math.max(year, thisYear), 11, 31)),
        };
    }, [date]);

    const closedQuery = useApiQuery(["attendance", "closed-days", closedWindow.from], () =>
        getClosedDays(closedWindow.from, closedWindow.to),
    );
    const closedDays: ClosedDay[] = closedQuery.data ?? [];

    // The calendar's own read: every day of the same window, with the reason it is
    // closed (a weekly off, a Saturday rule, a dated weekly off or a holiday) and whether
    // this class-section already has a register there. One request, one source.
    const calendarQuery = useApiQuery(
        ["attendance", "section-calendar", sectionId ?? "none", closedWindow.from, closedWindow.to],
        () => getSectionCalendar(sectionId as string, closedWindow.from, closedWindow.to),
        { enabled: Boolean(sectionId) },
    );
    const calendarDays: SectionCalendarDay[] = calendarQuery.data?.days ?? [];

    // The rows print the month the calendar is showing, and the annual percentage stops on
    // the day on screen - so both come from the server, and the figure and its caption can
    // never describe different windows.
    const summaryQuery = useApiQuery(
        ["attendance", "summary", sectionId ?? "none", date],
        () => getSectionSummary(sectionId as string, { until: date, month: date }),
        { enabled: Boolean(sectionId) },
    );
    const summary: SectionSummary | undefined = summaryQuery.data;

    // The late list is the last complete month, so it needs no date from the screen.
    const lateQuery = useApiQuery(
        ["attendance", "late-last-month", sectionId ?? "none"],
        () => getSectionLateLastMonth(sectionId as string),
        { enabled: Boolean(sectionId) },
    );

    // The trend is anchored on the day being looked at: a week is seven days ending that
    // day, a month is the first of its month up to it. Closed days are skipped server-side.
    const trendWindow = useMemo(() => {
        const anchor = new Date(`${date}T00:00:00`);
        const days = trendRange === "week" ? 7 : Math.max(1, anchor.getDate());
        return { days, end: isoDate(anchor) };
    }, [date, trendRange]);

    const trendQuery = useApiQuery(
        ["attendance", "trend", sectionId ?? "none", trendWindow.end, trendWindow.days],
        () => getSectionTrend(sectionId as string, trendWindow.days, trendWindow.end),
        { enabled: Boolean(sectionId) },
    );
    const trend: SectionTrend | undefined = trendQuery.data;

    const attentionQuery = useApiQuery(
        ["attendance", "attention", sectionId ?? "none"],
        () => getSectionAttention(sectionId as string),
        { enabled: Boolean(sectionId) },
    );
    const attention: AttendanceAttentionRow[] = attentionQuery.data ?? [];

    // A new day (or a new room) starts from what the server says, not from yesterday.
    const draftKey = `${sectionId ?? ""}:${date}`;
    const draft: Record<string, Status> = useMemo(
        () => (draftState.key === draftKey ? draftState.marks : {}),
        [draftState, draftKey],
    );

    const writeDraft = useCallback(
        (next: Record<string, Status>) => setDraftState({ key: draftKey, marks: next }),
        [draftKey],
    );

    const rows: RegisterRow[] = useMemo(() => register?.rows ?? [], [register]);

    /** The day as the grid shows it: the saved register, with this session's edits on top. */
    const marks: Record<string, Status> = useMemo(
        () => ({ ...marksFromRows(rows), ...draft }),
        [rows, draft],
    );

    const closedReason = register?.closedReason ?? closedReasonOn(closedDays, date);
    const isClosed = Boolean(closedReason);

    const roster = useMemo(
        () =>
            rows.map((row) => ({
                id: row.studentId,
                name: row.name,
                admissionNo: row.admissionNo,
            })),
        [rows],
    );

    /**
     * The day as one object: the cards, the Save counter and the roster all read from
     * this, so none of them can disagree with the chips (Phase 3's single source).
     */
    const day = useMemo(() => dayModel(rows, draft), [rows, draft]);
    const counts = day.counts;

    const setMark = useCallback(
        (id: string, status: Status) => {
            writeDraft({ ...draft, [id]: status });
        },
        [draft, writeDraft],
    );

    const setAll = useCallback(
        (status: Status) => {
            // A child who has left the school is on the sheet but not in the room: marking
            // them present would invent a day they never had.
            writeDraft(
                Object.fromEntries(
                    rows
                        .filter((row) => row.active !== false)
                        .map((row) => [row.studentId, status]),
                ),
            );
        },
        [rows, writeDraft],
    );

    const reset = useCallback(() => writeDraft({}), [writeDraft]);

    /**
     * Save the rows this session changed (`POST /attendance/bulk` upserts them).
     *
     * Only the draft is sent: a child nobody touched keeps the mark they already had,
     * which is the difference between "I marked these" and "everything is present".
     */
    const save = useCallback(async (): Promise<{ present: number; total: number } | null> => {
        if (!sectionId) return null;
        const changes = Object.entries(draft);
        if (changes.length === 0) return null;

        setSaving(true);
        try {
            await markAttendanceBulk(
                sectionId,
                date,
                changes.map(([studentId, status]) => ({
                    studentId,
                    status: storedStatus(status),
                })),
            );
            writeDraft({});
            for (const key of [
                ["attendance", "register"],
                ["attendance", "summary"],
                ["attendance", "trend"],
                ["attendance", "attention"],
                ["attendance", "irregular"],
                ["classroom"],
            ]) {
                await queryClient.invalidateQueries({ queryKey: key });
            }
            const present = changes.filter(([, status]) => status === "Present").length;
            return { present, total: changes.length };
        } finally {
            setSaving(false);
        }
    }, [sectionId, draft, date, writeDraft, queryClient]);

    // Stable identity, so the merge below does not recompute on every render.
    const totals: StudentAttendanceTotal[] = useMemo(() => summary?.rows ?? [], [summary]);

    /**
     * The rows the roster prints: the day's own state plus the figures the summary holds -
     * the month's present-and-late over the days a register was saved in that month, and
     * the annual percentage up to the day on screen.
     * One merge, so a row cannot show numbers from a different window than the caption.
     * While the summary is still loading the figures stay `undefined` and the row prints
     * nothing, rather than a confident `0` it would have to take back a moment later.
     */
    const rosterRows = useMemo(() => {
        const byId = new Map(totals.map((row) => [row.studentId, row]));
        return day.rows.map((row) => {
            const summaryRow = byId.get(row.studentId);
            return {
                ...row,
                monthPresent: summaryRow?.monthPresentTotal,
                monthSaved: summaryRow?.monthSaved,
                yearPercent: summaryRow?.percent,
            };
        });
    }, [day, totals]);
    const trendValues = useMemo(() => trendBars(trend?.points ?? []), [trend]);

    return {
        // where
        className,
        setClassName,
        section,
        setSection,
        sectionId,
        classNames: catalog.classNames,
        sectionNames: catalog.sectionNames,
        sectionsOf: catalog.sectionsOf,
        catalogLoading: catalog.loading,
        // when
        date,
        setDate,
        closedDays,
        calendarDays,
        closedReason,
        closedKind: register?.closedKind ?? null,
        isClosed,
        // the register
        loading: sectionId ? registerQuery.isPending : catalog.loading,
        rows,
        roster,
        marks,
        setMark,
        setAll,
        reset,
        savedPercent: register?.percent ?? null,
        day,
        rosterRows,
        counts,
        marked: day.counts.marked,
        unmarked: day.counts.unmarked,
        total: day.counts.total,
        hasSaved: day.hasSaved,
        isDirty: day.isDirty,
        saving,
        save,
        // the widgets
        trendRange,
        setTrendRange,
        summary,
        totals,
        workingDays: summary?.workingDays ?? 0,
        threshold: summary?.threshold ?? 75,
        trendValues,
        attention,
        late: lateQuery.data,
        lateLoading: lateQuery.isPending,
        loadingWidgets: summaryQuery.isPending || trendQuery.isPending,
    };
}
