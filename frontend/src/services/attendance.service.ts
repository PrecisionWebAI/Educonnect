import { api } from "@/lib/api/client";
import { toCamel } from "@/lib/api/case";
import type {
    AttendanceAttentionRow,
    AttendanceRecord,
    ClosedDay,
    IrregularStudent,
    LeaveSyncRow,
    SectionRegister,
    SectionSummary,
    SectionTrend,
} from "@/types";

export async function getAttendance(skip = 0, limit = 100): Promise<AttendanceRecord[]> {
    return api.get<AttendanceRecord[]>(`/attendance?skip=${skip}&limit=${limit}`);
}

/**
 * Save a whole class-section's register in one call (`POST /attendance/bulk`).
 *
 * The body names the **section** (the class is `section.classroom_id`), the date
 * and one row per student. `status` is the stored wording - lowercase
 * (`present` / `absent` / `late` / `leave`) - not the label the chips show.
 */
export async function markAttendanceBulk(
    sectionId: string,
    date: string,
    marks: { studentId: string; status: string }[],
    subjectId?: string | null,
): Promise<AttendanceRecord[]> {
    return api.post<AttendanceRecord[]>("/attendance/bulk", {
        section_id: sectionId,
        subject_id: subjectId ?? null,
        date,
        records: marks.map((mark) => ({
            student_id: mark.studentId,
            status: mark.status,
        })),
    });
}

/** The register already saved for one class-section on one date. */
export async function getSectionAttendance(
    classId: string,
    sectionId: string,
    date: string,
): Promise<AttendanceRecord[]> {
    return api.get<AttendanceRecord[]>(
        `/attendance/class/${classId}/section/${sectionId}?target_date=${date}`,
    );
}

// ---------------------------------------------------------------------------
// The register screen (Phase 4) - the four reads it draws and the calendar.
//
// Every one of these answers from real rows; nothing here is computed in the
// browser from a fixture or a hardcoded percentage.
// ---------------------------------------------------------------------------

/**
 * The whole roll for one day: everyone, marked or not (`unmarked` is a state).
 *
 * This is the read that pre-fills the grid, tells the toolbar when the day is
 * closed (`closedReason` = "Sunday" / "Diwali break") and carries the approved
 * leave a child is on (`leaveRequestId`).
 */
export async function getSectionRegister(
    sectionId: string,
    date: string,
    subjectId?: string | null,
): Promise<SectionRegister> {
    const params = new URLSearchParams({ date });
    if (subjectId) params.set("subject_id", subjectId);
    const payload = await api.get<unknown>(`/attendance/section/${sectionId}?${params}`);
    return toCamel<SectionRegister>(payload);
}

/** Per-student present/absent/leave days and % over a range, with the threshold. */
export async function getSectionSummary(
    sectionId: string,
    from: string,
    to: string,
): Promise<SectionSummary> {
    const payload = await api.get<unknown>(
        `/attendance/section/${sectionId}/summary?from=${from}&to=${to}`,
    );
    return toCamel<SectionSummary>(payload);
}

/** Present percentage per open day (Sundays and holidays are absent, not zero). */
export async function getSectionTrend(sectionId: string, days = 7): Promise<SectionTrend> {
    const payload = await api.get<unknown>(`/attendance/section/${sectionId}/trend?days=${days}`);
    return toCamel<SectionTrend>(payload);
}

/** Who the office should ring: below the school's threshold, or a run of absences. */
export async function getSectionAttention(sectionId: string): Promise<AttendanceAttentionRow[]> {
    const payload = await api.get<unknown>(`/attendance/section/${sectionId}/attention`);
    return toCamel<AttendanceAttentionRow[]>(payload);
}

/** Sundays and the school's holidays in a range - what the date picker greys out. */
export async function getClosedDays(from: string, to: string): Promise<ClosedDay[]> {
    const payload = await api.get<unknown>(`/attendance/closed-days?from=${from}&to=${to}`);
    return toCamel<ClosedDay[]>(payload);
}

export async function getIrregularStudents(): Promise<IrregularStudent[]> {
    return api.get<IrregularStudent[]>("/attendance/irregular");
}

export async function getLeaveSync(): Promise<LeaveSyncRow[]> {
    return api.get<LeaveSyncRow[]>("/attendance/leave-sync");
}
