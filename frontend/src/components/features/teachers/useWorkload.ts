"use client";
import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
    addStaffDuty,
    deleteStaffDuty,
    getStaffDuties,
    getStaffWeek,
    getWorkloadAnalytics,
    getWorkloadRule,
    saveWorkloadRule,
    type StaffDutyInput,
    type WorkloadRuleInput,
} from "@/services";
import { useApiQuery } from "@/lib/api/use-api-query";

export type WorkloadAnalyticsRow = Awaited<ReturnType<typeof getWorkloadAnalytics>>;
export type WorkloadRuleRow = Awaited<ReturnType<typeof getWorkloadRule>>;
export type StaffWeekRow = Awaited<ReturnType<typeof getStaffWeek>>;
export type StaffDutyRows = Awaited<ReturnType<typeof getStaffDuties>>;

/**
 * The workload tab's numbers and its two writes.
 *
 * The **matrix itself is not read here**: `useStaff` already fetches
 * `["staff", "workload"]` for the tab, and a second read of the same URL would
 * let the table and the tiles beside it disagree while one of them refetches.
 * This hook owns what the matrix cannot answer - the school's capacity rule and
 * the analytics counted over the same rows.
 *
 * Every write goes through `run`, the same three-step the profile drawer uses: it
 * marks which button is busy, keeps the server's refusal (`409` duplicate duty,
 * `403` for an HOD) as the screen's message, and invalidates **`["staff", …]`**
 * afterwards - the matrix, the tiles and the rule all read that prefix, so a
 * changed capacity updates every number at once.
 */
export function useWorkload({ canView = true }: { canView?: boolean } = {}) {
    const queryClient = useQueryClient();
    const [busy, setBusy] = useState<string | null>(null);
    const [error, setError] = useState<unknown>(null);

    const analyticsQuery = useApiQuery(["staff", "workload-analytics"], getWorkloadAnalytics, {
        enabled: canView,
    });
    const ruleQuery = useApiQuery(["staff", "workload-rule"], getWorkloadRule, {
        enabled: canView,
    });

    async function run(action: string, work: () => Promise<unknown>): Promise<boolean> {
        setBusy(action);
        setError(null);
        try {
            await work();
            await queryClient.invalidateQueries({ queryKey: ["staff"] });
            return true;
        } catch (problem) {
            setError(problem);
            return false;
        } finally {
            setBusy(null);
        }
    }

    return {
        analytics: analyticsQuery.data ?? null,
        rule: ruleQuery.data ?? null,
        loading: analyticsQuery.isPending || ruleQuery.isPending,
        loadError: analyticsQuery.error ?? ruleQuery.error ?? null,
        error,
        setError,
        busy,
        /** `PUT /teachers/workload/rules` - the school's full week. */
        saveRule: (input: WorkloadRuleInput) => run("rule", () => saveWorkloadRule(input)),
        addDuty: (teacherId: string, input: StaffDutyInput) =>
            run("duty", () => addStaffDuty(teacherId, input)),
        removeDuty: (teacherId: string, dutyId: string) =>
            run("duty", () => deleteStaffDuty(teacherId, dutyId)),
    };
}

/**
 * One person's week and their duties, read only while their sheet is open.
 *
 * `enabled: Boolean(teacherId)` rather than a conditional hook: the sheet is
 * mounted with `teacherId === null` and has to stay mounted, so the request is
 * what waits, not the component. Both reads answer `404` for somebody this caller
 * may not see - the server decides, not the screen.
 */
export function useStaffWeek(teacherId: string | null) {
    const weekQuery = useApiQuery(
        ["staff", "workload-week", teacherId],
        () => getStaffWeek(teacherId as string),
        { enabled: Boolean(teacherId) },
    );
    const dutiesQuery = useApiQuery(
        ["staff", "workload-duties", teacherId],
        () => getStaffDuties(teacherId as string),
        { enabled: Boolean(teacherId) },
    );

    return {
        week: weekQuery.data ?? null,
        duties: dutiesQuery.data ?? ([] as StaffDutyRows),
        loading: weekQuery.isPending,
        error: weekQuery.error ?? dutiesQuery.error ?? null,
    };
}
