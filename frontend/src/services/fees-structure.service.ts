import type { FeeStructureRow } from "@/types";

// ============================================================
// Operations ▸ Fees Structure service.
//
// Reads the `feestructure` master (class-wise fee heads). Hard-coded for
// this phase — switch the body to
// `api.get<FeeStructureRow[]>("/finance/structures")` when the finance
// router exposes the list endpoint.
// ============================================================

export const FREQUENCIES: FeeStructureRow["frequency"][] = [
    "Monthly",
    "Term",
    "Yearly",
    "One-time",
];

const FEE_HEADS: FeeStructureRow[] = [
    {
        id: 1,
        head: "Tuition Fee",
        className: "Class 6",
        frequency: "Monthly",
        amount: 4500,
        dueDay: "10th of month",
        students: 96,
        status: "Active",
    },
    {
        id: 2,
        head: "Tuition Fee",
        className: "Class 10",
        frequency: "Monthly",
        amount: 6200,
        dueDay: "10th of month",
        students: 88,
        status: "Active",
    },
    {
        id: 3,
        head: "Transport Fee",
        className: "All Classes",
        frequency: "Term",
        amount: 8500,
        dueDay: "5th of term",
        students: 142,
        status: "Active",
    },
    {
        id: 4,
        head: "Lab & Activity",
        className: "Class 11",
        frequency: "Yearly",
        amount: 12000,
        dueDay: "1st June",
        students: 74,
        status: "Active",
    },
    {
        id: 5,
        head: "Admission Fee",
        className: "All Classes",
        frequency: "One-time",
        amount: 25000,
        dueDay: "At admission",
        students: 23,
        status: "Draft",
    },
];

export async function getFeeStructures(): Promise<FeeStructureRow[]> {
    return FEE_HEADS;
}
