"use client";
import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { getLeaveApplications } from "@/services";
import { useApiQuery } from "@/lib/api/use-api-query";
import type { LeaveApplicationItem } from "@/types";

export type LeaveTab = "Apply" | "My Leaves" | "Approvals" | "Staff Leave";

export function useLeave() {
    const queryClient = useQueryClient();
    const leavesQuery = useApiQuery(["leave"], getLeaveApplications);
    const leaves = leavesQuery.data ?? [];
    const loading = leavesQuery.isPending;
    const [tab, setTab] = useState<LeaveTab>("Apply");

    const pendingCount = leaves.filter((l) => l.status === "Pending").length;
    const approvedCount = leaves.filter((l) => l.status === "Approved").length;

    const approve = (id: number) => {
        // Optimistic write-through: cache updates instantly, refetch reconciles.
        queryClient.setQueryData<LeaveApplicationItem[]>(["leave"], (prev) =>
            (prev ?? []).map((l) => (l.id === id ? { ...l, status: "Approved" as const } : l)),
        );
    };

    return { leaves, loading, tab, setTab, pendingCount, approvedCount, approve };
}
