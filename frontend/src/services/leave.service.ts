import { api } from "@/lib/api/client";
import { toCamel } from "@/lib/api/case";
import type {
    LeaveApplyInput,
    LeaveBalances,
    LeaveBalanceRow,
    LeavePolicy,
    LeaveRequestResult,
} from "@/types";

// ============================================================
// Leave - the workflow both leave screens use
//
// `/leave/staff-requests` and `/leave/applications` (the list reads) live in
// `teachers.service.ts` and `operations.service.ts`, where their screens already
// import them. Everything that *changes* a leave is here, in one file, because the
// apply form, the approve/reject buttons and the policy table are three screens
// driving one workflow.
//
// The body is sent snake_case and the answer read camelCase (`toCamel`), like every
// other service: mixing the two on one object is how `from_date` once arrived as an
// empty column with no error anywhere.
// ============================================================

/** The school's leave types and their annual grants. */
export async function getLeavePolicies(): Promise<LeavePolicy[]> {
    return toCamel<LeavePolicy[]>(await api.get("/leave/policies"));
}

/**
 * Upsert leave types. Types **not** in the payload keep their row: this saves what
 * the table shows, it does not replace the school's list.
 */
export async function saveLeavePolicies(
    policies: { leaveType: string; annualDays: number }[],
): Promise<LeavePolicy[]> {
    return toCamel<LeavePolicy[]>(
        await api.put("/leave/policies", {
            policies: policies.map((policy) => ({
                leave_type: policy.leaveType,
                annual_days: policy.annualDays,
            })),
        }),
    );
}

/** Retire a type. The server refuses (`409`) while any request still uses it. */
export async function deleteLeavePolicy(leaveType: string): Promise<void> {
    await api.delete(`/leave/policies/${encodeURIComponent(leaveType)}`);
}

/**
 * Every person in scope x every leave type for one year.
 *
 * `used` counts approved days, `pending` counts days still waiting, and
 * `remaining` is what is still free to ask for - the three travel together
 * because "3 left" is not readable on its own.
 */
export async function getLeaveBalances(
    params: { year?: number; employeeId?: string } = {},
): Promise<LeaveBalances> {
    const query = new URLSearchParams();
    if (params.year) query.set("year", String(params.year));
    if (params.employeeId) query.set("employee_id", params.employeeId);
    const suffix = query.toString() ? `?${query.toString()}` : "";
    return toCamel<LeaveBalances>(await api.get(`/leave/balances${suffix}`));
}

/** Grant (or correct) one person's days for one type and year. */
export async function saveLeaveBalance(
    employeeId: string,
    input: { leaveType: string; year: number; entitledDays: number; note?: string | null },
): Promise<LeaveBalanceRow> {
    return toCamel<LeaveBalanceRow>(
        await api.put(`/leave/balances/${employeeId}`, {
            leave_type: input.leaveType,
            year: input.year,
            entitled_days: input.entitledDays,
            note: input.note ?? null,
        }),
    );
}

/**
 * File a leave.
 *
 * Send neither id for your **own** leave (the teacher's form - the server finds the
 * employee record from the login); send `employeeId` to file for a staff member, or
 * `studentId` from the student screen. Sending both is refused (`422`).
 */
export async function applyLeave(input: LeaveApplyInput): Promise<LeaveRequestResult> {
    const body: Record<string, unknown> = {
        leave_type: input.leaveType,
        from_date: input.fromDate,
        to_date: input.toDate,
        reason: input.reason ?? null,
    };
    if (input.employeeId) body.employee_id = input.employeeId;
    if (input.studentId) body.student_id = input.studentId;
    return toCamel<LeaveRequestResult>(await api.post("/leave/requests", body));
}

/** Approve a pending request. Approving twice is the same answer, not an error. */
export async function approveLeave(
    requestId: string,
    note?: string | null,
): Promise<LeaveRequestResult> {
    return toCamel<LeaveRequestResult>(
        await api.post(`/leave/requests/${requestId}/approve`, { note: note ?? null }),
    );
}

/** Reject a pending request, with the office's reason (`409` once approved). */
export async function rejectLeave(
    requestId: string,
    note?: string | null,
): Promise<LeaveRequestResult> {
    return toCamel<LeaveRequestResult>(
        await api.post(`/leave/requests/${requestId}/reject`, { note: note ?? null }),
    );
}

/**
 * Withdraw a pending or approved leave - by the person who filed it, or the office.
 *
 * The cancelled day stops reading `On Leave` in the register immediately, because
 * the register derives that word from the approved leave.
 */
export async function cancelLeave(
    requestId: string,
    note?: string | null,
): Promise<LeaveRequestResult> {
    return toCamel<LeaveRequestResult>(
        await api.post(`/leave/requests/${requestId}/cancel`, { note: note ?? null }),
    );
}
