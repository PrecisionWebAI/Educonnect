"use client";
import { useState } from "react";
import { keepPreviousData, useQueryClient } from "@tanstack/react-query";
import {
    approveSubstitution,
    assignSubstitution,
    getSubstitutionBoard,
    getSubstitutionCandidates,
    withdrawSubstitution,
} from "@/services";
import { useApiQuery } from "@/lib/api/use-api-query";
import type { SubstitutionPeriod } from "@/types";

/**
 * The cover board for one day, and the three writes that change it.
 *
 * `["staff", "substitutions", date]` sits under the same `["staff"]` prefix the
 * register, the leave list and the directory use, so one invalidation after a write
 * refreshes every screen that could disagree with it.
 *
 * The candidates are a **separate, lazy query**: one keyed by the period being
 * looked at, `enabled` only while a period is open. A board with twelve periods
 * does not need twelve candidate lists it is not showing.
 */
export function useSubstitution({ date }: { date: string }) {
    const queryClient = useQueryClient();
    const [busy, setBusy] = useState<string | null>(null);
    const [error, setError] = useState<unknown>(null);
    /** The period whose cover dialog is open. */
    const [picked, setPicked] = useState<SubstitutionPeriod | null>(null);

    const boardQuery = useApiQuery(
        ["staff", "substitutions", date],
        () => getSubstitutionBoard(date),
        { placeholderData: keepPreviousData },
    );

    const candidatesQuery = useApiQuery(
        ["staff", "substitutions", date, "candidates", picked?.periodId ?? "none"],
        () => getSubstitutionCandidates(picked?.periodId as string, date),
        { enabled: picked !== null },
    );

    async function run(action: string, work: () => Promise<unknown>): Promise<boolean> {
        setBusy(action);
        setError(null);
        try {
            await work();
            await queryClient.invalidateQueries({ queryKey: ["staff", "substitutions"] });
            return true;
        } catch (problem) {
            // The server's `409` is the screen's message: it names the colleague,
            // the reason or the cover already in the slot.
            setError(problem);
            return false;
        } finally {
            setBusy(null);
        }
    }

    return {
        board: boardQuery.data ?? null,
        loading: boardQuery.isPending,
        refreshing: boardQuery.isFetching && !boardQuery.isPending,
        error: boardQuery.error ?? null,
        writeError: error,
        setWriteError: setError,
        busy,
        /** The period the cover dialog was opened for, and its candidate list. */
        picked,
        setPicked,
        candidates: candidatesQuery.data ?? null,
        candidatesLoading: candidatesQuery.isPending && picked !== null,
        /** Assign a colleague to the picked period; the dialog closes on success. */
        assign: async (period: SubstitutionPeriod, substituteId: string) => {
            const ok = await run("assign", () =>
                assignSubstitution({
                    periodId: period.periodId,
                    onDate: date,
                    absentEmployeeId: period.absentEmployeeId,
                    substituteEmployeeId: substituteId,
                }),
            );
            if (ok) setPicked(null);
            return ok;
        },
        approve: (assignmentId: string) => run("approve", () => approveSubstitution(assignmentId)),
        withdraw: (assignmentId: string) =>
            run("withdraw", () => withdrawSubstitution(assignmentId)),
    };
}
