import { api } from "@/lib/api/client";
import { toCamel } from "@/lib/api/case";
import type {
    AppraisalCycleInput,
    AppraisalCycleRow,
    AppraisalCycleStatus,
    AppraisalQueue,
    AppraisalRow,
    ReviewInput,
    SelfAssessmentInput,
    TrainingInput,
    TrainingRow,
} from "@/types";

/**
 * The appraisal season's calls.
 *
 * Three groups, mirroring the rights on the server: the season (`cycles`, the
 * office's), the person's own form (`self` + `submit`), and the reviewer's
 * (`review`, `goals`, `finalize`). A `403` here is the server refusing the *right*;
 * a `409` is it refusing the *row* (not submitted, already finalized).
 */

export async function getAppraisalCycles(): Promise<AppraisalCycleRow[]> {
    return toCamel<AppraisalCycleRow[]>(await api.get("/teachers/appraisals/cycles"));
}

export async function createAppraisalCycle(input: AppraisalCycleInput): Promise<AppraisalCycleRow> {
    return toCamel<AppraisalCycleRow>(
        await api.post("/teachers/appraisals/cycles", {
            name: input.name,
            start_date: input.startDate,
            end_date: input.endDate,
            note: input.note ?? null,
        }),
    );
}

/** `Draft -> Open` creates one appraisal per person on the roll. */
export async function setAppraisalCycleStatus(
    cycleId: string,
    status: AppraisalCycleStatus,
): Promise<AppraisalCycleRow> {
    return toCamel<AppraisalCycleRow>(
        await api.post(`/teachers/appraisals/cycles/${cycleId}/status`, { status }),
    );
}

/** The season at the caller's scope, plus their own appraisal (`mine`). */
export async function getAppraisalQueue(cycleId: string): Promise<AppraisalQueue> {
    return toCamel<AppraisalQueue>(await api.get(`/teachers/appraisals/cycles/${cycleId}`));
}

export async function saveSelfAssessment(
    appraisalId: string,
    input: SelfAssessmentInput,
): Promise<AppraisalRow> {
    return toCamel<AppraisalRow>(
        await api.post(`/teachers/appraisals/${appraisalId}/self`, {
            self_rating: input.selfRating,
            self_note: input.selfNote ?? null,
            goals: input.goals.map((goal) => ({
                title: goal.title,
                target: goal.target ?? null,
                weight: goal.weight ?? 1,
            })),
        }),
    );
}

export async function submitAppraisal(appraisalId: string): Promise<AppraisalRow> {
    return toCamel<AppraisalRow>(await api.post(`/teachers/appraisals/${appraisalId}/submit`));
}

export async function reviewAppraisal(
    appraisalId: string,
    input: ReviewInput,
): Promise<AppraisalRow> {
    return toCamel<AppraisalRow>(
        await api.post(`/teachers/appraisals/${appraisalId}/review`, {
            reviewer_rating: input.reviewerRating,
            reviewer_note: input.reviewerNote ?? null,
        }),
    );
}

export async function finalizeAppraisal(appraisalId: string): Promise<AppraisalRow> {
    return toCamel<AppraisalRow>(await api.post(`/teachers/appraisals/${appraisalId}/finalize`));
}

export async function judgeAppraisalGoal(goalId: string, achieved: boolean): Promise<AppraisalRow> {
    return toCamel<AppraisalRow>(
        await api.patch(`/teachers/appraisals/goals/${goalId}`, { achieved }),
    );
}

export async function getEmployeeTraining(employeeId: string): Promise<TrainingRow[]> {
    return toCamel<TrainingRow[]>(
        await api.get(`/teachers/appraisals/employees/${employeeId}/training`),
    );
}

export async function recordEmployeeTraining(
    employeeId: string,
    input: TrainingInput,
): Promise<TrainingRow> {
    return toCamel<TrainingRow>(
        await api.post(`/teachers/appraisals/employees/${employeeId}/training`, {
            title: input.title,
            provider: input.provider ?? null,
            on_date: input.onDate,
            hours: input.hours ?? 0,
            note: input.note ?? null,
        }),
    );
}
