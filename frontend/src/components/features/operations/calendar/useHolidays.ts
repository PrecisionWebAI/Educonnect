"use client";

import { useMemo, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useApiQuery } from "@/lib/api/use-api-query";
import { isoDate } from "@/lib/attendance/view";
import {
    clearOpenDay,
    createHoliday,
    deleteHoliday,
    getHolidayCalendar,
    getWeeklyOff,
    markOpenDay,
    setWeeklyOff,
    updateHoliday,
} from "@/services";
import type { HolidayInput } from "@/services";

// The calendar's data: one window (the year being looked at) for the grid, the weekly off
// setting, and the three writes. Every write refreshes the window **and** the register
// screens' own queries, because a holiday changes the open days every percentage divides
// by - a screen left showing yesterday's numbers would be wrong, not merely stale.

/**
 * The window the calendar is read over.
 *
 * A weekly off is a **rule for every matching day of the year**, not for the days near the
 * month on screen: declaring "Sunday off" closes every unmarked Sunday of 2026, January to
 * December, and the register refuses each one. The window used to be a fixed `6 months
 * back / 12 months forward`, which made the grid stop shading at an arbitrary horizon - a
 * Sunday 14 months out looked open while the API would refuse its register. So the window
 * follows the year being looked at, plus today's year, so "Upcoming" still crosses New Year.
 */
const windowOf = (month: Date) => {
    const year = month.getFullYear();
    const thisYear = new Date().getFullYear();
    return {
        from: isoDate(new Date(Math.min(year, thisYear), 0, 1)),
        to: isoDate(new Date(Math.max(year, thisYear), 11, 31)),
    };
};

export function useHolidays() {
    const queryClient = useQueryClient();
    const [month, setMonth] = useState(
        () => new Date(new Date().getFullYear(), new Date().getMonth(), 1),
    );

    const window = useMemo(() => windowOf(month), [month]);

    const calendarQuery = useApiQuery(["attendance", "holidays", window.from, window.to], () =>
        getHolidayCalendar(window.from, window.to),
    );
    const weeklyOffQuery = useApiQuery(["attendance", "weekly-off"], getWeeklyOff);

    function refresh() {
        // `attendance` covers the register, the summary, the trend and this calendar;
        // `classroom` covers the section header's own percentages.
        void queryClient.invalidateQueries({ queryKey: ["attendance"] });
        void queryClient.invalidateQueries({ queryKey: ["classroom"] });
    }

    const create = useMutation({
        mutationFn: (input: HolidayInput) => createHoliday(input),
        onSuccess: refresh,
    });
    const update = useMutation({
        mutationFn: (values: { id: string; input: HolidayInput }) =>
            updateHoliday(values.id, values.input),
        onSuccess: refresh,
    });
    const remove = useMutation({
        mutationFn: (id: string) => deleteHoliday(id),
        onSuccess: refresh,
    });
    const saveWeeklyOff = useMutation({
        mutationFn: (input: { days: number[]; nth: string[] }) =>
            setWeeklyOff(input.days, input.nth),
        onSuccess: refresh,
    });
    /** Reopen one date ("just this day") - the weekly-off setting is left alone. */
    const openDay = useMutation({
        mutationFn: (date: string) => markOpenDay(date),
        onSuccess: refresh,
    });
    /** Close that date again. */
    const closeOpenDay = useMutation({
        mutationFn: (date: string) => clearOpenDay(date),
        onSuccess: refresh,
    });

    return {
        month,
        setMonth,
        window,
        calendar: calendarQuery.data,
        loading: calendarQuery.isPending,
        error: calendarQuery.error,
        // The three cards ride on the calendar read itself (server-computed), so a save that
        // refreshes the list refreshes the figures with it - one request, no stale second one.
        summary: calendarQuery.data?.summary,
        summaryLoading: calendarQuery.isPending,
        weeklyOffDays: weeklyOffQuery.data?.days ?? [],
        // `"5#1"` = the 1st Saturday of every month.
        weeklyOffNth: weeklyOffQuery.data?.nth ?? [],
        weeklyOffLoading: weeklyOffQuery.isPending,
        create,
        update,
        remove,
        saveWeeklyOff,
        openDay,
        closeOpenDay,
        refresh,
    };
}
