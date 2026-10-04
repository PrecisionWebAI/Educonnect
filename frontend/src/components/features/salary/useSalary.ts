"use client";

import { useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
    SALARY_DEPARTMENTS,
    SALARY_MONTHS,
    getSalaryRegister,
} from "@/services";
import { useApiQuery } from "@/lib/api/use-api-query";
import { todayISO } from "@/lib/format";
import type { SalaryPaymentRow, SalaryPaymentStatus } from "@/types";

// Operations ▸ Salary (Staff) — monthly salary register.
// NOTE: the schema has no salary-payment table yet (only the static
// `staffprofile.salary` column), so this runs on the service seed data.

export const SALARY_KEY = ["operations", "salary"];

export type SalaryTab = "Salary Register" | "Department Summary";

export const SALARY_STATUS_TONE: Record<SalaryPaymentStatus, "green" | "accent" | "amber"> = {
    Paid: "green",
    Processing: "accent",
    Pending: "amber",
};

export const SALARY_STATUS_OPTIONS: (SalaryPaymentStatus | "All")[] = [
    "All",
    "Paid",
    "Processing",
    "Pending",
];

export function useSalary() {
    const queryClient = useQueryClient();
    const registerQuery = useApiQuery(SALARY_KEY, getSalaryRegister);
    const register = useMemo(() => registerQuery.data ?? [], [registerQuery.data]);

    const [tab, setTab] = useState<SalaryTab>("Salary Register");
    const [query, setQuery] = useState("");
    const [status, setStatus] = useState<SalaryPaymentStatus | "All">("All");
    const [month, setMonth] = useState(SALARY_MONTHS[0]);
    const [department, setDepartment] = useState(SALARY_DEPARTMENTS[0]);

    const filtered = useMemo(() => {
        const q = query.trim().toLowerCase();
        return register.filter((r) => {
            const matchQ =
                !q ||
                r.staffName.toLowerCase().includes(q) ||
                r.staffCode.toLowerCase().includes(q) ||
                r.designation.toLowerCase().includes(q);
            const matchS = status === "All" || r.status === status;
            const matchM = r.month === month;
            const matchD = department === "All Departments" || r.department === department;
            return matchQ && matchS && matchM && matchD;
        });
    }, [register, query, status, month, department]);

    const departmentSummary = useMemo(() => {
        const map = new Map<
            string,
            { department: string; staff: number; gross: number; net: number }
        >();
        register.forEach((r) => {
            const bucket =
                map.get(r.department) ?? { department: r.department, staff: 0, gross: 0, net: 0 };
            bucket.staff += 1;
            bucket.gross += r.gross;
            bucket.net += r.net;
            map.set(r.department, bucket);
        });
        return Array.from(map.values()).sort((a, b) => b.net - a.net);
    }, [register]);

    const counts = useMemo(() => {
        const unpaid = register.filter((r) => r.status !== "Paid");
        return {
            netPayable: register.reduce((sum, r) => sum + r.net, 0),
            paid: register.filter((r) => r.status === "Paid").length,
            processing: register.filter((r) => r.status === "Processing").length,
            pending: register.filter((r) => r.status === "Pending").length,
            outstanding: unpaid.reduce((sum, r) => sum + r.net, 0),
        };
    }, [register]);

    function writeRegister(updater: (rows: SalaryPaymentRow[]) => SalaryPaymentRow[]) {
        queryClient.setQueryData<SalaryPaymentRow[]>(SALARY_KEY, (prev) => updater(prev ?? []));
    }

    /** Queues the month's still-pending rows for processing. */
    function runPayroll(): number {
        const queued = register.filter((r) => r.status === "Pending").length;
        writeRegister((rows) =>
            rows.map((r) => (r.status === "Pending" ? { ...r, status: "Processing" } : r)),
        );
        return queued;
    }

    function markPaid(row: SalaryPaymentRow) {
        writeRegister((rows) =>
            rows.map((r) =>
                r.id === row.id ? { ...r, status: "Paid", paidOn: todayISO() } : r,
            ),
        );
    }

    return {
        register,
        loading: registerQuery.isPending,
        tab,
        setTab,
        query,
        setQuery,
        status,
        setStatus,
        month,
        setMonth,
        months: SALARY_MONTHS,
        department,
        setDepartment,
        departments: SALARY_DEPARTMENTS,
        filtered,
        departmentSummary,
        counts,
        runPayroll,
        markPaid,
    };
}
