import { api } from "@/lib/api/client";
import type { AttendanceRecord, IrregularStudent, LeaveSyncRow } from "@/types";

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

export async function getIrregularStudents(): Promise<IrregularStudent[]> {
    return api.get<IrregularStudent[]>("/attendance/irregular");
}

export async function getLeaveSync(): Promise<LeaveSyncRow[]> {
    return api.get<LeaveSyncRow[]>("/attendance/leave-sync");
}
