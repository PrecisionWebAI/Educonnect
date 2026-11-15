"use client";

import { useCallback, useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
    getClosedDays,
    getSectionAttention,
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

/** The period the totals panel covers. */
export type SummaryRange = "month" | "fortnight" | "week";

export function useAttendance(scope: AttendanceScope = {}) {
    const queryClient = useQueryClient();
    const catalog = useClassCatalog();

    const [className, setClassName] = useState(scope.className ?? "");
    const [section, setSection] = useState(scope.section ?? "");
    const [date, setDate] = useState(() => isoDate(new Date()));
    const [range, setRange] = useState<SummaryRange>("month");
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

    // Two months either side of the chosen day: enough for the picker's month view and
    // the "this month" totals without asking again on every date change.
    const closedWindow = useMemo(() => {
        const anchor = new Date(`${date}T00:00:00`);
        const from = new Date(anchor);
        from.setDate(1);
        from.setMonth(from.getMonth() - 1);
        const to = new Date(anchor);
        to.setMonth(to.getMonth() + 2, 0);
        return { from: isoDate(from), to: isoDate(to) };
    }, [date]);

    const closedQuery = useApiQuery(["attendance", "closed-days", closedWindow.from], () =>
        getClosedDays(closedWindow.from, closedWindow.to),
    );
    const closedDays: ClosedDay[] = closedQuery.data ?? [];

    const summaryWindow = useMemo(() => {
        const anchor = new Date(`${date}T00:00:00`);
        const from = new Date(anchor);
        if (range === "month") from.setDate(1);
        if (range === "fortnight") from.setDate(Math.max(1, anchor.getDate() - 13));
        if (range === "week") from.setDate(Math.max(1, anchor.getDate() - 6));
        return { from: isoDate(from), to: isoDate(anchor) };
    }, [date, range]);

    const summaryQuery = useApiQuery(
        ["attendance", "summary", sectionId ?? "none", summaryWindow.from, summaryWindow.to],
        () => getSectionSummary(sectionId as string, summaryWindow.from, summaryWindow.to),
        { enabled: Boolean(sectionId) },
    );
    const summary: SectionSummary | undefined = summaryQuery.data;

    const trendQuery = useApiQuery(
        ["attendance", "trend", sectionId ?? "none"],
        () => getSectionTrend(sectionId as string, 7),
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

    const markedCount = useMemo(
        () => rows.filter((row) => marks[row.studentId]).length,
        [rows, marks],
    );

    const setMark = useCallback(
        (id: string, status: Status) => {
            writeDraft({ ...draft, [id]: status });
        },
        [draft, writeDraft],
    );

    const setAll = useCallback(
        (status: Status) => {
            // `leave` is derived from a request: "mark all" never invents one.
            if (status === "Leave") return;
            writeDraft(Object.fromEntries(rows.map((row) => [row.studentId, status])));
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

    /** The strip: the register's own counts, so it describes the saved day as well. */
    const counts = useMemo(() => {
        if (!register) {
            return { Present: 0, Absent: 0, Late: 0, Leave: 0, Unmarked: rows.length };
        }
        return {
            Present: register.counts.present,
            Absent: register.counts.absent,
            Late: register.counts.late,
            Leave: register.counts.leave,
            Unmarked: register.counts.unmarked,
        };
    }, [register, rows.length]);

    const totals: StudentAttendanceTotal[] = summary?.rows ?? [];
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
        closedReason,
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
        counts,
        markedCount,
        dirtyCount: Object.keys(draft).length,
        saving,
        save,
        // the widgets
        range,
        setRange,
        summary,
        totals,
        workingDays: summary?.workingDays ?? 0,
        threshold: summary?.threshold ?? 75,
        trendValues,
        attention,
        loadingWidgets: summaryQuery.isPending || trendQuery.isPending,
    };
}
