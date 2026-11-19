import { api } from "@/lib/api/client";
import { toCamel } from "@/lib/api/case";
import type {
    AttendanceAttentionRow,
    AttendanceRecord,
    ClosedDay,
    LateStudents,
    SectionCalendar,
    StudentAttendanceEntry,
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

/**
 * Per-student present/absent/late days and %, with the school's threshold.
 *
 * No dates: the server measures over the register's own window - the first day this
 * section was ever marked up to the last day it holds - which is the window the table
 * prints. `until` stops the window on the day on screen (so the annual percentage never
 * counts a day the reader has not reached) and `month` picks the month the row's
 * `Monthly attendance 12/30` describes.
 */
export async function getSectionSummary(
    sectionId: string,
    options: { until?: string | null; month?: string | null } = {},
): Promise<SectionSummary> {
    const query = new URLSearchParams();
    if (options.until) query.set("until", options.until);
    if (options.month) query.set("month", options.month);
    const suffix = query.size ? `?${query}` : "";
    const payload = await api.get<unknown>(`/attendance/section/${sectionId}/summary${suffix}`);
    return toCamel<SectionSummary>(payload);
}

/**
 * The month the register's date control draws: which days are closed and why, plus which
 * days already have a register saved for this class-section.
 *
 * One read for the whole window, so the calendar's colours and its saved-day dots come
 * from the same calendar the register itself obeys.
 */
export async function getSectionCalendar(
    sectionId: string,
    from: string,
    to: string,
): Promise<SectionCalendar> {
    const payload = await api.get<unknown>(
        `/attendance/section/${sectionId}/calendar?from=${from}&to=${to}`,
    );
    return toCamel<SectionCalendar>(payload);
}

/**
 * Present percentage per open day, counting back from `end` (today when it is empty).
 *
 * The anchor is what lets the card draw "the week of the date I am looking at" instead
 * of "the last seven days"; weekly offs and holidays are skipped either way.
 */
export async function getSectionTrend(
    sectionId: string,
    days = 7,
    end?: string | null,
): Promise<SectionTrend> {
    const query = new URLSearchParams({ days: String(days) });
    if (end) query.set("end", end);
    const payload = await api.get<unknown>(`/attendance/section/${sectionId}/trend?${query}`);
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

/** One child's whole register history (newest first) - the drill-down under a name. */
export async function getStudentAttendance(studentId: string): Promise<StudentAttendanceEntry[]> {
    const payload = await api.get<unknown>(`/attendance/student/${studentId}`);
    return toCamel<StudentAttendanceEntry[]>(payload);
}

/** Children late more than the school's share of last month's open days. */
export async function getSectionLateLastMonth(sectionId: string): Promise<LateStudents> {
    const payload = await api.get<unknown>(`/attendance/section/${sectionId}/late-last-month`);
    return toCamel<LateStudents>(payload);
}
