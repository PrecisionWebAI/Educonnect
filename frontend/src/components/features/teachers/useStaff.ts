"use client";
import { useMemo, useState, type Dispatch, type SetStateAction } from "react";
import { getStaff, getWorkloadMatrix, getStaffLeaves, getStaffPerformance } from "@/services";
import { useApiQuery } from "@/lib/api/use-api-query";

export type StaffTab = "List" | "Workload" | "Leave & Substitute" | "Performance";

export type WorkloadMatrixRows = Awaited<ReturnType<typeof getWorkloadMatrix>>;
export type StaffLeaveRows = Awaited<ReturnType<typeof getStaffLeaves>>;
export type StaffPerfRows = Awaited<ReturnType<typeof getStaffPerformance>>;

export function useStaff(tab: StaffTab) {
    const staffQuery = useApiQuery(["staff"], getStaff);
    const matrixQuery = useApiQuery(["staff", "workload"], getWorkloadMatrix);
    const leavesQuery = useApiQuery(["staff", "leaves"], getStaffLeaves);
    const perfQuery = useApiQuery(["staff", "performance"], getStaffPerformance);
    const staff = staffQuery.data ?? [];
    const matrix = matrixQuery.data ?? ([] as Awaited<ReturnType<typeof getWorkloadMatrix>>);
    const leaves = leavesQuery.data ?? ([] as Awaited<ReturnType<typeof getStaffLeaves>>);
    const perf = perfQuery.data ?? ([] as Awaited<ReturnType<typeof getStaffPerformance>>);
    const loading =
        staffQuery.isPending || matrixQuery.isPending || leavesQuery.isPending || perfQuery.isPending;
    const [query, setQuery] = useState("");
    const [dept, setDept] = useState("All");

    const departments = useMemo(
        () => ["All", ...Array.from(new Set(staff.map((s) => s.department)))],
        [staff],
    );

    const filtered = useMemo(
        () =>
            staff.filter((s) => {
                const q = query.trim().toLowerCase();
                const matchQ =
                    !q ||
                    s.name.toLowerCase().includes(q) ||
                    s.subject.toLowerCase().includes(q) ||
                    s.staffCode.toLowerCase().includes(q);
                const matchD = dept === "All" || s.department === dept;
                return matchQ && matchD;
            }),
        [staff, query, dept],
    );

    const activeCount = staff.filter((s) => s.status === "Active").length;
    const leaveCount = staff.filter((s) => s.status === "On Leave").length;

    const [page, setPage] = useState(1);
    const [pageSize, setPageSize] = useState(5);
    const [prevTab, setPrevTab] = useState(tab);

    if (prevTab !== tab) {
        setPrevTab(tab);
        setPage(1);
    }

    const handleQueryChange: Dispatch<SetStateAction<string>> = (action) => {
        setQuery(action);
        setPage(1);
    };

    const handleDeptChange: Dispatch<SetStateAction<string>> = (action) => {
        setDept(action);
        setPage(1);
    };

    const paginated = useMemo(() => {
        const start = (page - 1) * pageSize;
        return filtered.slice(start, start + pageSize);
    }, [filtered, page, pageSize]);

    return {
        staff,
        filtered,
        paginated,
        page,
        setPage,
        pageSize,
        setPageSize,
        totalItems: filtered.length,
        matrix,
        leaves,
        perf,
        loading,
        query,
        setQuery: handleQueryChange,
        dept,
        setDept: handleDeptChange,
        departments,
        activeCount,
        leaveCount,
    };
}
