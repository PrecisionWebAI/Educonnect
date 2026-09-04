import { api } from "@/lib/api/client";
import type { AttendanceRecord, IrregularStudent, LeaveSyncRow } from "@/types";

export async function getAttendance(skip = 0, limit = 100): Promise<AttendanceRecord[]> {
    return api.get<AttendanceRecord[]>(`/attendance?skip=${skip}&limit=${limit}`);
}

export async function getIrregularStudents(): Promise<IrregularStudent[]> {
    return api.get<IrregularStudent[]>("/attendance/irregular");
}

export async function getLeaveSync(): Promise<LeaveSyncRow[]> {
    return api.get<LeaveSyncRow[]>("/attendance/leave-sync");
}
