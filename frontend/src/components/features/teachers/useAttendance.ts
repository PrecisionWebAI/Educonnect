"use client";
import { useState } from "react";
import { keepPreviousData, useQueryClient } from "@tanstack/react-query";
import {
    amendStaffAttendance,
    getAttendanceRegister,
    getStaffMonth,
    markMyAttendance,
    markStaffAttendance,
    type StaffAttendanceEntry,
    type StaffAttendanceMark,
} from "@/services";
import { useApiQuery } from "@/lib/api/use-api-query";

export type StaffRegisterData = Awaited<ReturnType<typeof getAttendanceRegister>>;
export type StaffMonthData = Awaited<ReturnType<typeof getStaffMonth>>;

/**
 * The register for one day, and the two writes that change it.
 *
 * The **department** and **status** filters are query keys, so the list the table
 * shows is the list the server counted: narrowing to "Absent" cannot make the
 * tiles above disagree with the rows below, because both come from one response.
 *
 * Every write goes through `run`, the same three steps the profile drawer and the
 * workload tab use: mark which button is busy, keep the server's refusal (`409`
 * for somebody on approved leave, `403` for a department head) as the screen's
 * message, and invalidate **`["staff", …]`** afterwards - the register, the
 * month sheet and the directory's `On Leave` tile all read that prefix.
 */
export function useAttendance({
    canView = true,
    canMark = false,
    date,
}: {
    canView?: boolean;
    canMark?: boolean;
    /** The day being shown, `YYYY-MM-DD`. */
    date: string;
}) {
    const queryClient = useQueryClient();
    const [department, setDepartment] = useState("All");
    const [status, setStatus] = useState("All");
    const [busy, setBusy] = useState<string | null>(null);
    const [error, setError] = useState<unknown>(null);

    const registerQuery = useApiQuery(
        ["staff", "attendance", date, department, status],
        () =>
            getAttendanceRegister({
                date,
                department: department === "All" ? undefined : department,
                status: status === "All" ? undefined : status,
            }),
        { enabled: canView },
    );

    async function run(action: string, work: () => Promise<unknown>): Promise<boolean> {
        setBusy(action);
        setError(null);
        try {
            await work();
            await queryClient.invalidateQueries({ queryKey: ["staff"] });
            return true;
        } catch (problem) {
            setError(problem);
            return false;
        } finally {
            setBusy(null);
        }
    }

    const register = registerQuery.data ?? null;

    return {
        register,
        loading: registerQuery.isPending,
        error: registerQuery.error ?? null,
        /** A refusal from a write, kept apart from a failed read. */
        writeError: error,
        setWriteError: setError,
        busy,
        canMark,
        department,
        setDepartment,
        status,
        setStatus,
        /** The departments the day's own rows offer, ascending, with "All" first. */
        departments: [
            "All",
            ...Array.from(new Set((register?.rows ?? []).map((row) => row.department)))
                .filter((name) => Boolean(name))
                .sort((first, second) => first.localeCompare(second)),
        ],
        /**
         * `POST /teachers/attendance/bulk` - a whole day in one call.
         *
         * The server answers with the day as it now reads, and the invalidation
         * refetches it anyway: the two are the same numbers, and the refetch is
         * what keeps the `Not Marked` count honest after a partial send.
         */
        mark: (records: StaffAttendanceEntry[]) =>
            run("mark", () => markStaffAttendance({ date, records })),
        /** `PATCH /teachers/attendance/records/{id}` - one corrected day. */
        amend: (recordId: string, input: { status?: StaffAttendanceMark; remarks?: string }) =>
            run("amend", () => amendStaffAttendance(recordId, input)),
        /**
         * `POST /teachers/me/attendance` - the caller marks **their own** day.
         *
         * The employee is the token's, so there is no id here; a second mark on the
         * same date is a `409` and the office's correction is the way to change one.
         */
        markSelf: (day: string) =>
            run("self", () => markMyAttendance({ date: day, status: "present" })),
    };
}

/**
 * One person's month, read while their sheet is open.
 *
 * The sheet is **mounted only while a person is picked** (`AttendanceLeaveTab`), so
 * this hook is always enabled. That matters: a query with `enabled: false` stays
 * `pending` for ever in TanStack Query, which reads as a permanent spinner - the
 * month sheet used to render itself (and its `Modal`) even with nobody picked, and
 * the spinner never went away.
 *
 * `placeholderData: keepPreviousData` is why changing the month does not empty the
 * screen: the grid keeps the month it is showing (with `refreshing` true) until the
 * new one arrives, instead of dropping to a spinner and making the calendar feel
 * slower than the request it is waiting for.
 */
export function useStaffMonth(employeeId: string, month: string) {
    const monthQuery = useApiQuery(
        ["staff", "attendance-month", employeeId, month],
        () => getStaffMonth(employeeId, month),
        { placeholderData: keepPreviousData },
    );

    return {
        month: monthQuery.data ?? null,
        loading: monthQuery.isPending,
        /** A second month is on its way while the previous one is still on screen. */
        refreshing: monthQuery.isFetching && !monthQuery.isPending,
        error: monthQuery.error ?? null,
    };
}
