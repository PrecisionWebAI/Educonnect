import { api } from "@/lib/api/client";
import { toCamel } from "@/lib/api/case";
import type {
    StaffLeaveItem,
    StaffMember,
    StaffPerformanceRow,
    StaffSummary,
    WorkloadMatrixRow,
} from "@/types";

// ============================================================
// Teachers & Staff - the People screen's reads (`/teachers`, `/leave/staff-requests`)
//
// The API answers in snake_case (`joining_date`, `from_date`) and the screen reads
// camelCase, so every response goes through `toCamel` here instead of each table
// mapping fields by hand. It was that hand mapping that let `from_date` reach the
// staff-leave table as `from` - an empty column, with no error anywhere.
// ============================================================

/** The directory's filters. `status` is one of the three badge words. */
export interface StaffQuery {
    q?: string;
    department?: string;
    status?: StaffMember["status"];
    skip?: number;
    /** `null` (the default) means "everyone": the screen pages in the browser. */
    limit?: number | null;
}

function queryString({ q, department, status, skip, limit }: StaffQuery): string {
    const params = new URLSearchParams();
    if (q?.trim()) params.set("q", q.trim());
    if (department && department !== "All") params.set("department", department);
    if (status) params.set("status", status);
    if (skip) params.set("skip", String(skip));
    if (limit != null) params.set("limit", String(limit));
    const query = params.toString();
    return query ? `?${query}` : "";
}

/**
 * The staff directory.
 *
 * A teacher-only account gets its own record back: the backend decides that (see
 * `people/teachers/scope.py`), not this screen.
 */
export async function getStaff(query: StaffQuery = {}): Promise<StaffMember[]> {
    return toCamel<StaffMember[]>(await api.get(`/teachers${queryString(query)}`));
}

/** The tiles above the directory - counted over the whole roll by the server. */
export async function getStaffSummary(): Promise<StaffSummary> {
    return toCamel<StaffSummary>(await api.get("/teachers/summary"));
}

/** Every teacher's periods against the timetable's own week. */
export async function getWorkloadMatrix(): Promise<WorkloadMatrixRow[]> {
    return toCamel<WorkloadMatrixRow[]>(await api.get("/teachers/workload"));
}

/** Staff leave requests (the staff rows of `leaverequest`). */
export async function getStaffLeaves(): Promise<StaffLeaveItem[]> {
    return toCamel<StaffLeaveItem[]>(await api.get("/leave/staff-requests"));
}

/** Per-teacher rating summary from the anonymous reviews. */
export async function getStaffPerformance(): Promise<StaffPerformanceRow[]> {
    return toCamel<StaffPerformanceRow[]>(await api.get("/teachers/performance"));
}

/** A single directory row (`/teachers/{id}`, 404 when the caller may not see them). */
export async function getStaffMember(teacherId: string): Promise<StaffMember> {
    return toCamel<StaffMember>(await api.get(`/teachers/${teacherId}`));
}
