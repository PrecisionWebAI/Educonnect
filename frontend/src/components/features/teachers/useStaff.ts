"use client";
import { useEffect, useMemo, useState, type Dispatch, type SetStateAction } from "react";
import { getStaff, getWorkloadMatrix, getStaffLeaves, getStaffPerformance } from "@/services";
import type { StaffMember } from "@/types";

export type StaffTab = "List" | "Workload" | "Leave & Substitute" | "Performance";

export type WorkloadMatrixRows = Awaited<ReturnType<typeof getWorkloadMatrix>>;
export type StaffLeaveRows = Awaited<ReturnType<typeof getStaffLeaves>>;
export type StaffPerfRows = Awaited<ReturnType<typeof getStaffPerformance>>;

export function useStaff(tab: StaffTab) {
    const [staff, setStaff] = useState<StaffMember[]>([]);
    const [matrix, setMatrix] = useState<Awaited<ReturnType<typeof getWorkloadMatrix>>>([]);
    const [leaves, setLeaves] = useState<Awaited<ReturnType<typeof getStaffLeaves>>>([]);
    const [perf, setPerf] = useState<Awaited<ReturnType<typeof getStaffPerformance>>>([]);
    const [loading, setLoading] = useState(true);
    const [query, setQuery] = useState("");
    const [dept, setDept] = useState("All");

    useEffect(() => {
        let alive = true;
        Promise.all([getStaff(), getWorkloadMatrix(), getStaffLeaves(), getStaffPerformance()])
            .then(([s, m, l, p]) => {
                if (!alive) return;
                setStaff(s);
                setMatrix(m);
                setLeaves(l);
                setPerf(p);
            })
            .finally(() => {
                if (!alive) return;
                setLoading(false);
            });
        return () => {
            alive = false;
        };
    }, []);

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
