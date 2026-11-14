"use client";
import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
    applyLeave,
    approveLeave,
    cancelLeave,
    deleteLeavePolicy,
    getLeaveBalances,
    getLeavePolicies,
    rejectLeave,
    saveLeaveBalance,
    saveLeavePolicies,
} from "@/services";
import { useApiQuery } from "@/lib/api/use-api-query";
import type { LeaveApplyInput, LeaveRequestResult } from "@/types";

export type LeavePolicyRows = Awaited<ReturnType<typeof getLeavePolicies>>;
export type LeaveBalanceData = Awaited<ReturnType<typeof getLeaveBalances>>;

/**
 * The leave workflow: the policy table, the balance register and the four verbs.
 *
 * The balance and policy reads are keyed under **`["staff", "leave", …]`** so the
 * same `["staff"]` invalidation the register and the directory use also refreshes
 * them: approving a leave changes a balance, the person's `On Leave` badge, and the
 * list of requests - three screens, one prefix, one refetch.
 *
 * Every write goes through `run`, the same three steps the register and the profile
 * drawer use: mark which control is busy, keep the server's refusal as the screen's
 * message (a `409` here is a real answer - "no longer fits", "already approved"),
 * and invalidate afterwards.
 */
export function useLeaveWorkflow({
    canRead = true,
    canManagePolicy = false,
    year,
}: {
    /** `leave.read` - the policy list and the balance register. */
    canRead?: boolean;
    /** `leave.manage_policy` - the policy table and per-person overrides. */
    canManagePolicy?: boolean;
    /** The balance year the register shows, `YYYY`. */
    year: number;
}) {
    const queryClient = useQueryClient();
    const [busy, setBusy] = useState<string | null>(null);
    const [error, setError] = useState<unknown>(null);
    const [message, setMessage] = useState<string | null>(null);

    const policiesQuery = useApiQuery(["staff", "leave", "policies"], getLeavePolicies, {
        enabled: canRead,
    });
    const balancesQuery = useApiQuery(
        ["staff", "leave", "balances", year],
        () => getLeaveBalances({ year }),
        { enabled: canRead },
    );

    async function run(
        action: string,
        work: () => Promise<LeaveRequestResult>,
    ): Promise<LeaveRequestResult | null> {
        setBusy(action);
        setError(null);
        setMessage(null);
        try {
            const result = await work();
            await queryClient.invalidateQueries({ queryKey: ["staff"] });
            await queryClient.invalidateQueries({ queryKey: ["leave"] });
            return result;
        } catch (problem) {
            setError(problem);
            return null;
        } finally {
            setBusy(null);
        }
    }

    return {
        policies: policiesQuery.data ?? ([] as LeavePolicyRows),
        policiesLoading: policiesQuery.isPending,
        balances: balancesQuery.data ?? null,
        balancesLoading: balancesQuery.isPending,
        balancesError: balancesQuery.error ?? null,
        canManagePolicy,
        busy,
        /** A refusal from a write, kept apart from a failed read. */
        writeError: error,
        setWriteError: setError,
        /** The toast line for the last successful write. */
        message,
        setMessage,

        /** File a leave. `null` on a refusal - the reason is in `writeError`. */
        apply: (input: LeaveApplyInput) => run("apply", () => applyLeave(input)),
        approve: (requestId: string, note?: string | null) =>
            run(`approve-${requestId}`, () => approveLeave(requestId, note)),
        reject: (requestId: string, note?: string | null) =>
            run(`reject-${requestId}`, () => rejectLeave(requestId, note)),
        cancel: (requestId: string, note?: string | null) =>
            run(`cancel-${requestId}`, () => cancelLeave(requestId, note)),

        /** Save the policy table. Types left out of `rows` keep their stored value. */
        savePolicies: async (rows: { leaveType: string; annualDays: number }[]) => {
            setBusy("policies");
            setError(null);
            try {
                await saveLeavePolicies(rows);
                await queryClient.invalidateQueries({ queryKey: ["staff", "leave"] });
                setMessage("Leave policy saved.");
                return true;
            } catch (problem) {
                setError(problem);
                return false;
            } finally {
                setBusy(null);
            }
        },
        removePolicy: async (leaveType: string) => {
            setBusy(`remove-${leaveType}`);
            setError(null);
            try {
                await deleteLeavePolicy(leaveType);
                await queryClient.invalidateQueries({ queryKey: ["staff", "leave"] });
                setMessage(`'${leaveType}' removed.`);
                return true;
            } catch (problem) {
                setError(problem);
                return false;
            } finally {
                setBusy(null);
            }
        },
        /** Grant one person days for one type and year. */
        saveBalance: async (
            employeeId: string,
            input: { leaveType: string; entitledDays: number; note?: string | null },
        ) => {
            setBusy(`balance-${employeeId}`);
            setError(null);
            try {
                await saveLeaveBalance(employeeId, { ...input, year });
                await queryClient.invalidateQueries({ queryKey: ["staff", "leave"] });
                setMessage("Balance updated.");
                return true;
            } catch (problem) {
                setError(problem);
                return false;
            } finally {
                setBusy(null);
            }
        },
    };
}
