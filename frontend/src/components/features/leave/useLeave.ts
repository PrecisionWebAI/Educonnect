"use client";
import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { approveLeave, getLeaveApplications, rejectLeave } from "@/services";
import { useApiQuery } from "@/lib/api/use-api-query";

export type LeaveTab = "Apply" | "My Leaves" | "Approvals" | "Staff Leave";

/**
 * The student leave screen's data and its two decisions.
 *
 * `approve` used to rewrite the cached row and print "Approved" - a screen that
 * looked like a workflow and recorded nothing, so the decision vanished on the next
 * reload and the applicant never found out. It now calls
 * `POST /leave/requests/{id}/approve` and refetches; the server's refusal (`409`
 * for a request somebody already decided) is kept as the message.
 */
export function useLeave() {
    const queryClient = useQueryClient();
    const leavesQuery = useApiQuery(["leave"], getLeaveApplications);
    const leaves = leavesQuery.data ?? [];
    const loading = leavesQuery.isPending;
    const [tab, setTab] = useState<LeaveTab>("Apply");
    const [busy, setBusy] = useState<string | null>(null);
    const [error, setError] = useState<unknown>(null);

    const pendingCount = leaves.filter((l) => l.status === "Pending").length;
    const approvedCount = leaves.filter((l) => l.status === "Approved").length;

    async function decide(
        action: "approve" | "reject",
        id: string,
        note?: string | null,
    ): Promise<boolean> {
        setBusy(`${action}-${id}`);
        setError(null);
        try {
            await (action === "approve" ? approveLeave(id, note) : rejectLeave(id, note));
            await queryClient.invalidateQueries({ queryKey: ["leave"] });
            return true;
        } catch (problem) {
            setError(problem);
            return false;
        } finally {
            setBusy(null);
        }
    }

    return {
        leaves,
        loading,
        tab,
        setTab,
        pendingCount,
        approvedCount,
        busy,
        /** A refusal from a decision, kept apart from a failed read. */
        error,
        setError,
        approve: (id: string) => decide("approve", id),
        reject: (id: string, note?: string | null) => decide("reject", id, note),
    };
}
