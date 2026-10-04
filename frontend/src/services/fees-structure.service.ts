import type { FeeStructureRow } from "@/types";
import { api } from "@/lib/api/client";
import { toCamel, toSnake } from "@/lib/api/case";

// ============================================================
// Operations ▸ Fees Structure service — talks to `feestructure`.
//
//   GET  /finance/fee-structures                the fee card (class + counts)
//   POST /finance/fee-structures                add a head (starts as Draft)
//   PUT  /finance/fee-structures/{id}           edit a head
//   PUT  /finance/fee-structures/{id}/status    publish / unpublish
//
// The server resolves `className` against `gradeclass` (name first, level as a
// fallback) and returns the canonical class name plus a live student count, so
// the "Applies To" and "Students" columns are never invented on the client.
// ============================================================

export const FREQUENCIES: FeeStructureRow["frequency"][] = [
    "Monthly",
    "Term",
    "Yearly",
    "One-time",
];

export interface FeeHeadInput {
    head: string;
    className: string;
    frequency: FeeStructureRow["frequency"];
    amount: number;
    dueDay: string;
}

export async function getFeeStructures(): Promise<FeeStructureRow[]> {
    return toCamel<FeeStructureRow[]>(await api.get("/finance/fee-structures"));
}

export async function createFeeHead(input: FeeHeadInput): Promise<FeeStructureRow> {
    return toCamel<FeeStructureRow>(
        await api.post("/finance/fee-structures", toSnake(input)),
    );
}

export async function updateFeeHead(
    id: number,
    input: FeeHeadInput,
): Promise<FeeStructureRow> {
    return toCamel<FeeStructureRow>(
        await api.put(`/finance/fee-structures/${id}`, toSnake(input)),
    );
}

export async function setFeeHeadStatus(
    id: number,
    status: FeeStructureRow["status"],
): Promise<FeeStructureRow> {
    return toCamel<FeeStructureRow>(
        await api.put(`/finance/fee-structures/${id}/status`, toSnake({ status })),
    );
}
