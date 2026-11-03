"use client";

import { useCallback, useMemo, useState, type SetStateAction } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { getAttendance, getStudents, markAttendanceBulk } from "@/services";
import { useApiQuery } from "@/lib/api/use-api-query";
import type { AttendanceRecord } from "@/types";

const STATUSES = ["Present", "Absent", "Late", "Leave"] as const;
export type Status = (typeof STATUSES)[number];
export const ATTENDANCE_STATUSES = STATUSES;

/** The chips read `Present`; the register stores `present` (see AttendanceStatus). */
function storedStatus(status: Status): string {
    return status.toLowerCase();
}

/**
 * The class-section this register belongs to.
 *
 * Inside the Classroom screen the section is fixed by the page the user is on, so
 * the roster can only ever be that section's students. Without a scope the hook
 * keeps the old school-wide behaviour (pickers + local-only save).
 */
export interface AttendanceScope {
    sectionId?: string;
    className?: string;
    section?: string;
}

export function useAttendance(scope: AttendanceScope = {}) {
    const queryClient = useQueryClient();
    const studentsQuery = useApiQuery(["students"], () => getStudents());
    const attendanceQuery = useApiQuery(["attendance"], () => getAttendance());
    const students = studentsQuery.data ?? null;
    const history = attendanceQuery.data ?? [];
    const [className, setClassName] = useState(scope.className ?? "10");
    const [section, setSection] = useState(scope.section ?? "A");
    const [date, setDate] = useState(() => new Date().toISOString().slice(0, 10));
    // per-student marks for the selected roster; unset = not yet marked
    const [marks, setMarks] = useState<Record<string, Status>>({});
    const [saving, setSaving] = useState(false);

    // A section scope wins over the pickers: inside Class 12-J the register is
    // 12-J's, whatever the toolbar happens to hold.
    const activeClass = scope.className ?? className;
    const activeSection = scope.section ?? section;

    const roster = useMemo(
        () =>
            (students ?? []).filter(
                (s) => s.className === activeClass && s.section === activeSection,
            ),
        [students, activeClass, activeSection],
    );

    const markedCount = useMemo(() => roster.filter((s) => marks[s.id]).length, [roster, marks]);

    function setAll(status: Status) {
        setMarks(Object.fromEntries(roster.map((s) => [s.id, status])));
    }

    function reset() {
        setMarks({});
    }

    /**
     * Persist the register.
     *
     * Inside a class-section (`sectionId` present) this is a real write to
     * `attendancerecord` through `POST /attendance/bulk`, and the Classroom card
     * behind the page is refreshed with it. Without a section there is nowhere to
     * write, so the rows stay in the query cache (the school-wide screen).
     */
    const save = useCallback(async (): Promise<AttendanceRecord[] | null> => {
        if (roster.length === 0) return null;

        if (scope.sectionId) {
            setSaving(true);
            try {
                await markAttendanceBulk(
                    scope.sectionId,
                    date,
                    roster.map((s) => ({
                        studentId: s.id,
                        status: storedStatus(marks[s.id] ?? "Present"),
                    })),
                );
            } finally {
                setSaving(false);
            }
            await queryClient.invalidateQueries({ queryKey: ["attendance"] });
            await queryClient.invalidateQueries({ queryKey: ["classroom"] });
        }

        const records: AttendanceRecord[] = roster.map((s) => ({
            id: crypto.randomUUID(),
            studentName: s.name,
            className: `${s.className}-${s.section}`,
            date,
            status: marks[s.id] ?? "Present",
        }));
        setHistory((prev) => [...records, ...prev]);
        setMarks({});
        return records;
    }, [roster, marks, date, scope.sectionId, queryClient]);

    /** Cache-backed history setter, keeps the original Dispatch<SetStateAction> shape. */
    function setHistory(action: SetStateAction<AttendanceRecord[]>) {
        queryClient.setQueryData<AttendanceRecord[]>(["attendance"], (prev) =>
            typeof action === "function" ? action(prev ?? []) : action,
        );
    }

    // ── Stitch widget data (computed, memoized) ────────────────

    /** Live counts for the summary strip. */
    const counts = useMemo(() => {
        const c: Record<Status | "Unmarked", number> = {
            Present: 0,
            Absent: 0,
            Late: 0,
            Leave: 0,
            Unmarked: 0,
        };
        for (const s of roster) {
            const st = marks[s.id];
            if (st) c[st] += 1;
            else c.Unmarked += 1;
        }
        return c;
    }, [roster, marks]);

    /** Weekday averages from history (mock trend for the right column). */
    const weeklyTrend = useMemo(() => {
        const base = { Mon: 92, Tue: 95, Wed: 94, Thu: 98, Fri: 96, Sat: 93 } as Record<
            string,
            number
        >;
        // nudge numbers slightly using today's saved records so it feels live
        const todayName = new Date().toLocaleDateString("en-IN", { weekday: "short" });
        if (todayName in base && history.length > 0) {
            const pct =
                history.filter((r) => r.status === "Present").length / Math.max(1, history.length);
            base[todayName] = Math.round(base[todayName] * 0.4 + pct * 100 * 0.6);
        }
        return base;
    }, [history]);

    /** Students flagged Absent/Late in current marks + known chronic absentees. */
    const alerts = useMemo(() => {
        const list: { name: string; reason: string }[] = [];
        for (const s of roster) {
            const st = marks[s.id];
            if (st === "Absent") list.push({ name: s.name, reason: "Marked absent today" });
            else if (st === "Late") list.push({ name: s.name, reason: "Arrived late today" });
        }
        return list;
    }, [roster, marks]);

    return {
        loading: students === null,
        classes: [...new Set((students ?? []).map((s) => s.className))].sort(),
        className,
        setClassName,
        section,
        setSection,
        /** The class the register is actually for (scope wins over the picker). */
        activeClass,
        activeSection,
        /** True while a real `POST /attendance/bulk` is in flight. */
        saving,
        date,
        setDate,
        roster,
        marks,
        setMark: (id: string, status: Status) => setMarks((prev) => ({ ...prev, [id]: status })),
        setAll,
        reset,
        save,
        markedCount,
        counts,
        weeklyTrend,
        alerts,
        history,
        setHistory,
    };
}
