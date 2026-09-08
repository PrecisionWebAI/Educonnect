"use client";
import { useMemo, useState } from "react";
import { getSalaryStructure, getPayrollEntry } from "@/services";
import { useApiQuery } from "@/lib/api/use-api-query";

export type PayrollTab = "Salary Structure" | "Month Processing" | "Payslips";

export function usePayroll(tab?: PayrollTab) {
    const structuresQuery = useApiQuery(["payroll", "structures"], getSalaryStructure);
    const entriesQuery = useApiQuery(["payroll", "entries"], getPayrollEntry);
    const structures = structuresQuery.data ?? [];
    const entries = entriesQuery.data ?? [];
    const loading = structuresQuery.isPending || entriesQuery.isPending;
    const [query, setQuery] = useState("");
    const [status, setStatus] = useState("All");

    const statuses = useMemo(
        () => ["All", ...Array.from(new Set(entries.map((e) => e.status)))],
        [entries],
    );

    const filtered = useMemo(
        () =>
            entries.filter((e) => {
                const q = query.trim().toLowerCase();
                const matchQ =
                    !q || e.name.toLowerCase().includes(q) || e.staffCode.toLowerCase().includes(q);
                const matchS = status === "All" || e.status === status;
                return matchQ && matchS;
            }),
        [entries, query, status],
    );

    const totalPayroll = useMemo(() => entries.reduce((a, e) => a + e.net, 0), [entries]);
    const draftCount = entries.filter((e) => e.status === "Draft").length;
    const postedCount = entries.filter((e) => e.status === "Posted").length;
    const paidCount = entries.filter((e) => e.status === "Paid").length;

    return {
        tab,
        structures,
        entries,
        filtered,
        loading,
        query,
        setQuery,
        status,
        setStatus,
        statuses,
        totalPayroll,
        draftCount,
        postedCount,
        paidCount,
    };
}
