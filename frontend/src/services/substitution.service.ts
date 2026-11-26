import { api } from "@/lib/api/client";
import { toCamel } from "@/lib/api/case";
import type {
    ClassAttendanceAccess,
    ClassAttendanceAccessInput,
    SubstitutionAssignInput,
    SubstitutionAssignment,
    SubstitutionBoard,
    SubstitutionCandidates,
} from "@/types";

/**
 * The cover board's four calls.
 *
 * The board reads a **derived** thing: opening it writes nothing, so a screen that
 * is re-opened all morning leaves no rows behind. Rows appear only when somebody
 * arranges a cover, signs it off, or withdraws it.
 */

/** The day's absences, their periods, and what is still open (`date` defaults to today). */
export async function getSubstitutionBoard(date?: string): Promise<SubstitutionBoard> {
    const suffix = date ? `?date=${encodeURIComponent(date)}` : "";
    return toCamel<SubstitutionBoard>(await api.get(`/teachers/substitutions${suffix}`));
}

/** Who can cover one period - with the reason for every yes and every no. */
export async function getSubstitutionCandidates(
    periodId: string,
    date: string,
): Promise<SubstitutionCandidates> {
    return toCamel<SubstitutionCandidates>(
        await api.get(
            `/teachers/substitutions/candidates?period_id=${encodeURIComponent(
                periodId,
            )}&date=${encodeURIComponent(date)}`,
        ),
    );
}

/** Arrange cover. `409` names why not (already covered, on leave, teaching). */
export async function assignSubstitution(
    input: SubstitutionAssignInput,
): Promise<SubstitutionAssignment> {
    return toCamel<SubstitutionAssignment>(
        await api.post("/teachers/substitutions/assignments", {
            period_id: input.periodId,
            on_date: input.onDate,
            absent_employee_id: input.absentEmployeeId,
            substitute_employee_id: input.substituteEmployeeId,
            note: input.note ?? null,
        }),
    );
}

/** Sign a cover off (`403` for a head of department). */
export async function approveSubstitution(
    assignmentId: string,
    note?: string | null,
): Promise<SubstitutionAssignment> {
    return toCamel<SubstitutionAssignment>(
        await api.post(`/teachers/substitutions/assignments/${assignmentId}/approve`, {
            note: note ?? null,
        }),
    );
}

/** Withdraw a cover, freeing the slot for somebody else. */
export async function withdrawSubstitution(assignmentId: string): Promise<void> {
    await api.delete(`/teachers/substitutions/assignments/${assignmentId}`);
}

/**
 * Hand a class-section's attendance on one day to a teacher (or change who has it).
 *
 * For a class whose class teacher is away. The teacher has no access until the office
 * approves it; choosing somebody else resets that. `409` names why (the class teacher is
 * not away, the chosen teacher is on leave or absent).
 */
export async function setClassAttendanceAccess(
    input: ClassAttendanceAccessInput,
): Promise<ClassAttendanceAccess> {
    return toCamel<ClassAttendanceAccess>(
        await api.put("/teachers/substitutions/attendance-access", {
            classroom_id: input.classroomId,
            on_date: input.onDate,
            delegate_employee_id: input.delegateEmployeeId,
            note: input.note ?? null,
        }),
    );
}

/** Sign a hand-over off - the teacher may then open that class and save its register. */
export async function approveClassAttendanceAccess(
    accessId: string,
): Promise<ClassAttendanceAccess> {
    return toCamel<ClassAttendanceAccess>(
        await api.post(`/teachers/substitutions/attendance-access/${accessId}/approve`, {}),
    );
}

/** Take a hand-over back; the teacher loses that class's register at once. */
export async function withdrawClassAttendanceAccess(accessId: string): Promise<void> {
    await api.delete(`/teachers/substitutions/attendance-access/${accessId}`);
}
