"use client";
import { useEffect, useMemo, useState } from "react";
import { getFeeInvoices, getExpenses } from "@/services";
import type { FeeInvoice, ExpenseItem } from "@/types";

export type FinanceTab = "Fee Collection" | "Dues & Recovery" | "Expenses & Budget" | "Reports";

export function useFinance(tab?: FinanceTab) {
    const [invoices, setInvoices] = useState<FeeInvoice[]>([]);
    const [expenses, setExpenses] = useState<ExpenseItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [query, setQuery] = useState("");
    const [status, setStatus] = useState("All");

    useEffect(() => {
        let alive = true;
        Promise.all([getFeeInvoices(), getExpenses()]).then(([inv, exp]) => {
            if (!alive) return;
            setInvoices(inv);
            setExpenses(exp);
            setLoading(false);
        });
        return () => {
            alive = false;
        };
    }, []);

    const statuses = useMemo(
        () => ["All", ...Array.from(new Set(invoices.map((i) => i.status)))],
        [invoices],
    );

    const filtered = useMemo(
        () =>
            invoices.filter((i) => {
                const q = query.trim().toLowerCase();
                const matchQ =
                    !q ||
                    i.student.toLowerCase().includes(q) ||
                    i.className.toLowerCase().includes(q) ||
                    i.head.toLowerCase().includes(q);
                const matchS = status === "All" || i.status === status;
                return matchQ && matchS;
            }),
        [invoices, query, status],
    );

    const collected = useMemo(() => invoices.reduce((a, i) => a + i.paid, 0), [invoices]);
    const pendingDues = useMemo(() => invoices.filter((i) => i.due > 0).length, [invoices]);
    const invoicesCount = invoices.length;
    const paidCount = invoices.filter((i) => i.status === "Paid").length;

    return {
        tab,
        invoices,
        expenses,
        filtered,
        loading,
        query,
        setQuery,
        status,
        setStatus,
        statuses,
        collected,
        pendingDues,
        invoicesCount,
        paidCount,
    };
}
