"use client";
import { getMyAttendance, getMyStaffRow, getMyWeek } from "@/services";
import { useApiQuery } from "@/lib/api/use-api-query";
import { todayISO } from "@/lib/format";

/**
 * A teacher's own numbers: their row, their week, their month.
 *
 * Three queries under the same `["staff", "me"]` prefix, so one invalidation after a
 * write anywhere in the staff screens refreshes this too. The month is the current
 * one - this panel answers "how is my week and my month going", not "browse history".
 */
export function useMyStaff(month: string = todayISO().slice(0, 7)) {
    const rowQuery = useApiQuery(["staff", "me"], getMyStaffRow);
    const weekQuery = useApiQuery(["staff", "me", "week"], getMyWeek);
    const monthQuery = useApiQuery(["staff", "me", "attendance", month], () =>
        getMyAttendance(month),
    );

    return {
        row: rowQuery.data ?? null,
        week: weekQuery.data ?? null,
        month: monthQuery.data ?? null,
        monthKey: month,
        loading: rowQuery.isPending || weekQuery.isPending || monthQuery.isPending,
        error: rowQuery.error ?? weekQuery.error ?? monthQuery.error ?? null,
    };
}
