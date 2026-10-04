"use client";

import { useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { FREQUENCIES, getFeeStructures } from "@/services";
import { useApiQuery } from "@/lib/api/use-api-query";
import { CLASS_NAMES } from "@/lib/constants/classes";
import type { FeeFrequency, FeeStructureRow } from "@/types";

// Operations ▸ Fees Structure — the class-wise `feestructure` master that
// drives invoices and fee collection on the Finance page.

export const FEE_STRUCTURE_KEY = ["operations", "fees-structure"];

export type FeeStructureTab = "Fee Structure" | "Class Summary";

export const EMPTY_FEE_HEAD = {
    head: "",
    className: CLASS_NAMES[0],
    frequency: "Monthly" as FeeFrequency,
    amount: 0,
    dueDay: "",
};

export type FeeHeadDraft = typeof EMPTY_FEE_HEAD;

export function useFeesStructure() {
    const queryClient = useQueryClient();
    const structuresQuery = useApiQuery(FEE_STRUCTURE_KEY, getFeeStructures);
    const structures = useMemo(() => structuresQuery.data ?? [], [structuresQuery.data]);

    const [tab, setTab] = useState<FeeStructureTab>("Fee Structure");
    const [query, setQuery] = useState("");
    const [classFilter, setClassFilter] = useState("All Classes");
    const [formOpen, setFormOpen] = useState(false);
    const [editingId, setEditingId] = useState<number | null>(null);
    const [draft, setDraft] = useState<FeeHeadDraft>(EMPTY_FEE_HEAD);

    const filtered = useMemo(() => {
        const q = query.trim().toLowerCase();
        return structures.filter((s) => {
            const matchQ =
                !q || s.head.toLowerCase().includes(q) || s.className.toLowerCase().includes(q);
            const matchC = classFilter === "All Classes" || s.className === classFilter;
            return matchQ && matchC;
        });
    }, [structures, query, classFilter]);

    // Class-wise rollup — same aggregate the Finance fee card shows.
    const classSummary = useMemo(() => {
        const map = new Map<
            string,
            { className: string; heads: number; students: number; value: number }
        >();
        structures.forEach((s) => {
            const bucket = map.get(s.className) ?? {
                className: s.className,
                heads: 0,
                students: 0,
                value: 0,
            };
            bucket.heads += 1;
            bucket.students += s.students;
            bucket.value += s.amount * s.students;
            map.set(s.className, bucket);
        });
        return Array.from(map.values()).sort((a, b) => a.className.localeCompare(b.className));
    }, [structures]);

    const counts = useMemo(
        () => ({
            heads: structures.length,
            published: structures.filter((s) => s.status === "Active").length,
            drafts: structures.filter((s) => s.status === "Draft").length,
            recurringValue: structures
                .filter((s) => s.frequency !== "One-time")
                .reduce((sum, s) => sum + s.amount * s.students, 0),
        }),
        [structures],
    );

    function writeStructures(
        updater: (rows: FeeStructureRow[]) => FeeStructureRow[],
    ) {
        queryClient.setQueryData<FeeStructureRow[]>(FEE_STRUCTURE_KEY, (prev) =>
            updater(prev ?? []),
        );
    }

    function openCreate() {
        setEditingId(null);
        setDraft(EMPTY_FEE_HEAD);
        setFormOpen(true);
    }

    function openEdit(row: FeeStructureRow) {
        setEditingId(row.id);
        setDraft({
            head: row.head,
            className: row.className,
            frequency: row.frequency,
            amount: row.amount,
            dueDay: row.dueDay,
        });
        setFormOpen(true);
    }

    /** Creates or updates a fee head. Returns false when the form is invalid. */
    function saveFeeHead(): boolean {
        if (!draft.head.trim() || draft.amount <= 0) return false;
        const values = {
            head: draft.head.trim(),
            className: draft.className,
            frequency: draft.frequency,
            amount: draft.amount,
            dueDay: draft.dueDay.trim() || "—",
        };
        if (editingId !== null) {
            writeStructures((rows) =>
                rows.map((s) => (s.id === editingId ? { ...s, ...values } : s)),
            );
        } else {
            writeStructures((rows) => {
                const nextId = rows.reduce((max, s) => Math.max(max, s.id), 0) + 1;
                return [...rows, { id: nextId, ...values, students: 0, status: "Draft" }];
            });
        }
        setFormOpen(false);
        setEditingId(null);
        return true;
    }

    function togglePublished(row: FeeStructureRow) {
        const next = row.status === "Active" ? "Draft" : "Active";
        writeStructures((rows) => rows.map((s) => (s.id === row.id ? { ...s, status: next } : s)));
        return next;
    }

    return {
        structures,
        loading: structuresQuery.isPending,
        tab,
        setTab,
        query,
        setQuery,
        classFilter,
        setClassFilter,
        filtered,
        classSummary,
        counts,
        frequencies: FREQUENCIES,
        formOpen,
        setFormOpen,
        editingId,
        draft,
        setDraft,
        openCreate,
        openEdit,
        saveFeeHead,
        togglePublished,
    };
}
