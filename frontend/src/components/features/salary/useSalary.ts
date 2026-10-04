"use client";

import { useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { getSalaryRegister, markSalaryPaid, runSalaryPayroll } from "@/services";
import { useApiQuery } from "@/lib/api/use-api-query";
import type { SalaryPaymentRow, SalaryPaymentStatus } from "@/types";

// Operations ▸ Staff Salary — monthly salary register.
//
// The register, the months it covers and the departments it spans all come from
// `salarypayment`. The month and department dropdowns are derived from the rows
// themselves, so a newly seeded month shows up in the filter with no constant
// to keep in step, and the stat tiles describe the month being viewed.

export const SALARY_KEY = ["operations", "salary"];

export const ALL_DEPARTMENTS = "All Departments";

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

/** The distinct months in the register, in the order the register lists them. */
function monthsOf(rows: SalaryPaymentRow[]): string[] {
    return Array.from(new Set(rows.map((row) => row.month)));
}

function departmentsOf(rows: SalaryPaymentRow[]): string[] {
    return [
        ALL_DEPARTMENTS,
        ...Array.from(new Set(rows.map((row) => row.department))).sort(),
    ];
}

export function useSalary() {
    const queryClient = useQueryClient();
    const registerQuery = useApiQuery(SALARY_KEY, getSalaryRegister);
    const register = useMemo(() => registerQuery.data ?? [], [registerQuery.data]);

    const months = useMemo(() => monthsOf(register), [register]);
    const departments = useMemo(() => departmentsOf(register), [register]);

    const [tab, setTab] = useState<SalaryTab>("Salary Register");
    const [query, setQuery] = useState("");
    const [status, setStatus] = useState<SalaryPaymentStatus | "All">("All");
    const [monthChoice, setMonthChoice] = useState("");
    const [department, setDepartment] = useState(ALL_DEPARTMENTS);

    // Newest month by default; a month picked by hand sticks as long as the
    // register still contains it.
    const month = months.includes(monthChoice) ? monthChoice : (months[0] ?? "");

    const monthRows = useMemo(
        () => register.filter((row) => row.month === month),
        [register, month],
    );

    const filtered = useMemo(() => {
        const q = query.trim().toLowerCase();
        return monthRows.filter((r) => {
            const matchQ =
                !q ||
                r.staffName.toLowerCase().includes(q) ||
                r.staffCode.toLowerCase().includes(q) ||
                r.designation.toLowerCase().includes(q);
            const matchS = status === "All" || r.status === status;
            const matchD = department === ALL_DEPARTMENTS || r.department === department;
            return matchQ && matchS && matchD;
        });
    }, [monthRows, query, status, department]);

    const departmentSummary = useMemo(() => {
        const map = new Map<
            string,
            { department: string; staff: number; gross: number; net: number }
        >();
        monthRows.forEach((r) => {
            const bucket =
                map.get(r.department) ?? { department: r.department, staff: 0, gross: 0, net: 0 };
            bucket.staff += 1;
            bucket.gross += r.gross;
            bucket.net += r.net;
            map.set(r.department, bucket);
        });
        return Array.from(map.values()).sort((a, b) => b.net - a.net);
    }, [monthRows]);

    const counts = useMemo(() => {
        const unpaid = monthRows.filter((r) => r.status !== "Paid");
        return {
            netPayable: monthRows.reduce((sum, r) => sum + r.net, 0),
            paid: monthRows.filter((r) => r.status === "Paid").length,
            processing: monthRows.filter((r) => r.status === "Processing").length,
            pending: monthRows.filter((r) => r.status === "Pending").length,
            outstanding: unpaid.reduce((sum, r) => sum + r.net, 0),
        };
    }, [monthRows]);

    async function refresh() {
        await queryClient.invalidateQueries({ queryKey: SALARY_KEY });
    }

    /** Queues the month's still-pending rows; returns how many moved. */
    async function runPayroll(): Promise<number> {
        const result = await runSalaryPayroll(month);
        await refresh();
        return result.queued;
    }

    /** Marks one salary row paid (the server stamps the date). */
    async function markPaid(row: SalaryPaymentRow) {
        await markSalaryPaid(row.id);
        await refresh();
    }

    return {
        register,
        monthRows,
        loading: registerQuery.isPending,
        tab,
        setTab,
        query,
        setQuery,
        status,
        setStatus,
        month,
        setMonth: setMonthChoice,
        months,
        department,
        setDepartment,
        departments,
        filtered,
        departmentSummary,
        counts,
        runPayroll,
        markPaid,
    };
}
