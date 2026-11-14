"use client";
import { useState } from "react";
import { keepPreviousData, useQueryClient } from "@tanstack/react-query";
import {
    createAppraisalCycle,
    finalizeAppraisal,
    getAppraisalCycles,
    getAppraisalQueue,
    judgeAppraisalGoal,
    reviewAppraisal,
    saveSelfAssessment,
    setAppraisalCycleStatus,
    submitAppraisal,
} from "@/services";
import { useApiQuery } from "@/lib/api/use-api-query";
import type {
    AppraisalCycleInput,
    AppraisalCycleStatus,
    ReviewInput,
    SelfAssessmentInput,
} from "@/types";

/**
 * The appraisal season's data, and the writes that move it.
 *
 * Two queries: the seasons (`["staff", "appraisals", "cycles"]`) and the one that is
 * selected (`["staff", "appraisals", cycleId]`), both under the `["staff"]` prefix the
 * register, leave and cover board share - so one invalidation refreshes every screen
 * that could disagree.
 *
 * The selected season is **derived, not stored twice**: it defaults to the first
 * `Open` season (that is the one a school is working in), else the newest, and it is
 * only overridden when the user picks another.
 */
export function useAppraisal({ canRead, canManage }: { canRead: boolean; canManage: boolean }) {
    const queryClient = useQueryClient();
    const [busy, setBusy] = useState<string | null>(null);
    const [error, setError] = useState<unknown>(null);
    const [chosen, setChosen] = useState<string | null>(null);

    const cyclesQuery = useApiQuery(["staff", "appraisals", "cycles"], getAppraisalCycles, {
        enabled: canRead,
    });
    const cycles = cyclesQuery.data ?? [];

    const fallback = cycles.find((cycle) => cycle.status === "Open")?.id ?? cycles[0]?.id ?? null;
    // A season that disappeared (deleted elsewhere) must not pin the screen. Derived
    // rather than stored back into state in an effect: `chosen` is honoured only while
    // it is still in the list, so adding and removing seasons needs no synchronisation.
    const chosenStillExists = chosen !== null && cycles.some((cycle) => cycle.id === chosen);
    const cycleId = (chosenStillExists ? chosen : null) ?? fallback;

    const queueQuery = useApiQuery(
        ["staff", "appraisals", cycleId],
        () => getAppraisalQueue(cycleId as string),
        { enabled: canRead && Boolean(cycleId), placeholderData: keepPreviousData },
    );

    async function run(action: string, work: () => Promise<unknown>): Promise<boolean> {
        setBusy(action);
        setError(null);
        try {
            await work();
            await queryClient.invalidateQueries({ queryKey: ["staff", "appraisals"] });
            return true;
        } catch (problem) {
            // The server's `409` is the screen's message: a draft cannot be reviewed,
            // a finalized appraisal cannot change, a season is not open.
            setError(problem);
            return false;
        } finally {
            setBusy(null);
        }
    }

    return {
        cycles,
        cycleId,
        setCycleId: (id: string) => setChosen(id),
        queue: queueQuery.data ?? null,
        loading: cyclesQuery.isPending || queueQuery.isPending,
        refreshing: queueQuery.isFetching && !queueQuery.isPending,
        error: cyclesQuery.error ?? queueQuery.error ?? null,
        writeError: error,
        setWriteError: setError,
        busy,
        canManage,
        createCycle: (input: AppraisalCycleInput) =>
            run("cycle", async () => {
                const created = await createAppraisalCycle(input);
                setChosen(created.id);
            }),
        moveCycle: (status: AppraisalCycleStatus) =>
            run("move", () => setAppraisalCycleStatus(cycleId as string, status)),
        saveSelf: (appraisalId: string, input: SelfAssessmentInput) =>
            run("self", () => saveSelfAssessment(appraisalId, input)),
        submit: (appraisalId: string) => run("submit", () => submitAppraisal(appraisalId)),
        review: (appraisalId: string, input: ReviewInput) =>
            run("review", () => reviewAppraisal(appraisalId, input)),
        finalize: (appraisalId: string) => run("finalize", () => finalizeAppraisal(appraisalId)),
        judgeGoal: (goalId: string, achieved: boolean) =>
            run("goal", () => judgeAppraisalGoal(goalId, achieved)),
    };
}
