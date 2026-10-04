"use client";

import { useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
    FREQUENCIES,
    createFeeHead,
    getFeeStructures,
    setFeeHeadStatus,
    updateFeeHead,
} from "@/services";
import { useApiQuery } from "@/lib/api/use-api-query";
import type { FeeFrequency, FeeStructureRow } from "@/types";

// Operations ▸ Fees Structure — the class-wise `feestructure` master that
// drives invoices and fee collection on the Finance page.
//
// Writes go through the API: the server resolves the class name to a real
// `classroom` row and returns the head with a live student count, so the
// "Applies To" / "Students" columns are never guessed on the client.

export const FEE_STRUCTURE_KEY = ["operations", "fees-structure"];

export type FeeStructureTab = "Fee Structure" | "Class Summary";

/** A blank fee head. The class stays empty until `openCreate` fills in the
 * first class the database offers, so no class name is baked in here. */
export const EMPTY_FEE_HEAD = {
    head: "",
    className: "",
    frequency: "Monthly" as FeeFrequency,
    amount: 0,
    dueDay: "",
};

export type FeeHeadDraft = typeof EMPTY_FEE_HEAD;

export function useFeesStructure(classNames: string[]) {
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

    async function refresh() {
        await queryClient.invalidateQueries({ queryKey: FEE_STRUCTURE_KEY });
    }

    function openCreate() {
        setEditingId(null);
        setDraft({ ...EMPTY_FEE_HEAD, className: classNames[0] ?? "" });
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
    async function saveFeeHead(): Promise<boolean> {
        if (!draft.head.trim() || draft.amount <= 0) return false;
        const values = {
            head: draft.head.trim(),
            className: draft.className,
            frequency: draft.frequency,
            amount: draft.amount,
            // "—" is what the API shows for "no due date"; sending it back would
            // store the placeholder as the due date.
            dueDay: draft.dueDay === "—" ? "" : draft.dueDay.trim(),
        };
        if (editingId !== null) {
            await updateFeeHead(editingId, values);
        } else {
            await createFeeHead(values);
        }
        await refresh();
        setFormOpen(false);
        setEditingId(null);
        return true;
    }

    /** Publishes / unpublishes a fee head and reports the stored state. */
    async function togglePublished(row: FeeStructureRow): Promise<FeeStructureRow["status"]> {
        const next = row.status === "Active" ? "Draft" : "Active";
        const updated = await setFeeHeadStatus(row.id, next);
        await refresh();
        return updated.status;
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
