"use client";
import { useMemo, useState, type Dispatch, type SetStateAction } from "react";
import {
    getStaff,
    getStaffLeaves,
    getStaffPerformance,
    getStaffSummary,
    getWorkloadMatrix,
} from "@/services";
import { useApiQuery } from "@/lib/api/use-api-query";
import type { StaffMember } from "@/types";

/**
 * The screen's tabs. "Attendance & Leave" carries the leave requests until the
 * attendance register and the substitute register land as their own tabs.
 */
export type StaffTab = "List" | "Workload" | "Attendance & Leave" | "Performance";

export type StaffRows = Awaited<ReturnType<typeof getStaff>>;
export type WorkloadMatrixRows = Awaited<ReturnType<typeof getWorkloadMatrix>>;
export type StaffLeaveRows = Awaited<ReturnType<typeof getStaffLeaves>>;
export type StaffPerfRows = Awaited<ReturnType<typeof getStaffPerformance>>;
export type StaffSummaryRow = Awaited<ReturnType<typeof getStaffSummary>>;

/** What the status dropdown offers: the three badge words, plus "everything". */
export type StaffStatusFilter = "All" | StaffMember["status"];

export interface StaffPermissions {
    /** `teachers.view_workload` - the workload tab and its numbers. */
    canViewWorkload?: boolean;
    /** `leave.read` - the staff leave list. */
    canViewLeave?: boolean;
}

/**
 * The Teachers & Staff screen's data.
 *
 * Two queries read the directory, on purpose:
 *
 * * `["staff", "all"]` is unfiltered and feeds the department dropdown, so
 *   picking "Science" does not remove every other department from the list;
 * * `["staff", "list", filters]` is what the table shows, filtered **by the
 *   server** so paging, the search box and the status badge all describe the same
 *   rows.
 *
 * The tiles read `["staff", "summary"]`, counted over the whole roll - they used
 * to be `staff.length` and a `.filter()` over the page in hand, which is why a
 * filter changed "Total Staff".
 */
export function useStaff(tab: StaffTab, permissions: StaffPermissions = {}) {
    const [query, setQueryValue] = useState("");
    const [dept, setDeptValue] = useState("All");
    const [status, setStatusValue] = useState<StaffStatusFilter>("All");
    const [page, setPage] = useState(1);
    const [pageSize, setPageSize] = useState(5);
    const [prevTab, setPrevTab] = useState(tab);

    if (prevTab !== tab) {
        setPrevTab(tab);
        setPage(1);
    }

    const allQuery = useApiQuery(["staff", "all"], () => getStaff());
    const listQuery = useApiQuery(["staff", "list", { query, dept, status }], () =>
        getStaff({
            q: query,
            department: dept === "All" ? undefined : dept,
            status: status === "All" ? undefined : status,
        }),
    );
    const summaryQuery = useApiQuery(["staff", "summary"], getStaffSummary);
    const matrixQuery = useApiQuery(["staff", "workload"], getWorkloadMatrix, {
        enabled: Boolean(permissions.canViewWorkload),
    });
    const leavesQuery = useApiQuery(["staff", "leaves"], getStaffLeaves, {
        enabled: Boolean(permissions.canViewLeave),
    });
    const perfQuery = useApiQuery(["staff", "performance"], getStaffPerformance);

    const staff = useMemo(() => listQuery.data ?? [], [listQuery.data]);
    const departments = useMemo(
        () => ["All", ...Array.from(new Set((allQuery.data ?? []).map((s) => s.department)))],
        [allQuery.data],
    );

    const paginated = useMemo(() => {
        const start = (page - 1) * pageSize;
        return staff.slice(start, start + pageSize);
    }, [staff, page, pageSize]);

    // Any filter change restarts the paging: page 3 of the previous filter is not
    // the same rows as page 3 of this one.
    const setQuery: Dispatch<SetStateAction<string>> = (action) => {
        setQueryValue(action);
        setPage(1);
    };
    const setDept: Dispatch<SetStateAction<string>> = (action) => {
        setDeptValue(action);
        setPage(1);
    };
    const setStatus: Dispatch<SetStateAction<StaffStatusFilter>> = (action) => {
        setStatusValue(action);
        setPage(1);
    };

    return {
        staff,
        paginated,
        totalItems: staff.length,
        page,
        setPage,
        pageSize,
        setPageSize,
        query,
        setQuery,
        dept,
        setDept,
        status,
        setStatus,
        departments,
        summary: summaryQuery.data ?? null,
        matrix: matrixQuery.data ?? ([] as WorkloadMatrixRows),
        leaves: leavesQuery.data ?? ([] as StaffLeaveRows),
        perf: perfQuery.data ?? ([] as StaffPerfRows),
        loading: listQuery.isPending || summaryQuery.isPending,
        // Only the *list* failing blanks the screen. A tiles hiccup is reported
        // on the tiles (they show "—"), so one broken count does not hide 60 rows.
        error: listQuery.error ?? null,
        summaryError: summaryQuery.error ?? null,
    };
}
