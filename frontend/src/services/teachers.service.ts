import { api } from "@/lib/api/client";
import { toCamel } from "@/lib/api/case";
import type {
    LeaveTabRow,
    StaffAttendanceDay,
    StaffAuditEntry,
    StaffCertification,
    StaffDocumentRow,
    StaffExperience,
    StaffLeaveItem,
    StaffMember,
    StaffMonth,
    StaffProfileDetail,
    StaffQualification,
    StaffRegister,
    StaffSummary,
    StaffWeek,
    VisibleLeaveKinds,
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

/** Which half of the split a directory read wants (0.9). */
export type StaffKind = "teacher" | "staff";

/**
 * The directory: the teaching roll or the rest of the staff (0.9).
 *
 * Same filters and the same server-side scope; only the path changes, so one
 * employee appears in exactly one of the two lists. A teacher-only account still
 * gets its own record back - the backend decides that (`people/teachers/scope.py`).
 */
export async function getStaff(
    query: StaffQuery = {},
    kind: StaffKind = "teacher",
): Promise<StaffMember[]> {
    const path = kind === "staff" ? "/staff" : "/teachers";
    return toCamel<StaffMember[]>(await api.get(`${path}${queryString(query)}`));
}

/** The tiles above the directory - counted over one side of the split, by the server. */
export async function getStaffSummary(kind: StaffKind = "teacher"): Promise<StaffSummary> {
    const path = kind === "staff" ? "/staff/summary" : "/teachers/summary";
    return toCamel<StaffSummary>(await api.get(path));
}

/**
 * Mark **your own** attendance (`staff_attendance.self`).
 *
 * No employee id: the server takes the person from the token, so this call cannot
 * name somebody else even if the body were tampered with. A second mark on the same
 * day is a `409` - the office corrects a marked day.
 */
export async function markMyAttendance(input: {
    date: string;
    status: "present" | "absent" | "half_day";
    remarks?: string;
    checkInTime?: string;
    checkOutTime?: string;
}): Promise<void> {
    await api.post("/teachers/me/attendance", {
        date: input.date,
        status: input.status,
        remarks: input.remarks ?? null,
        check_in_time: input.checkInTime ?? null,
        check_out_time: input.checkOutTime ?? null,
    });
}

/** The Staff / Student leave tabs (0.10) - one table, filtered by `kind`. */
export async function getLeaveTabRows(
    kind: "staff" | "student" | "all" = "all",
): Promise<LeaveTabRow[]> {
    return toCamel<LeaveTabRow[]>(await api.get(`/leave/requests?kind=${kind}`));
}

/** Which leave tabs the caller may open (office: both; staff: staff; child: student). */
export async function getVisibleLeaveKinds(): Promise<VisibleLeaveKinds> {
    return toCamel<VisibleLeaveKinds>(await api.get("/leave/visible-kinds"));
}

/** Staff leave requests (the staff rows of `leaverequest`). */
export async function getStaffLeaves(): Promise<StaffLeaveItem[]> {
    return toCamel<StaffLeaveItem[]>(await api.get("/leave/staff-requests"));
}

// ============================================================
// The daily staff register
//
// One day at a time (`register`), one person at a time (`month`), and the two
// writes: a whole day in one call, and a correction to a day already recorded.
// `on_leave` is never sent - the server derives it from the approved leave, and a
// write that tried to store it is refused (`422`).
// ============================================================

/** The three words a caller may record. `on_leave` and `not_marked` are derived. */
export type StaffAttendanceMark = "present" | "absent" | "half_day";

/**
 * The day's register - every person on the roll, marked or not.
 *
 * `date` defaults to today on the server; the screen always sends the day it is
 * showing so a refetch cannot drift across midnight.
 */
export async function getAttendanceRegister(
    params: { date?: string; department?: string; status?: string } = {},
): Promise<StaffRegister> {
    const query = new URLSearchParams();
    if (params.date) query.set("date", params.date);
    if (params.department) query.set("department", params.department);
    if (params.status) query.set("status", params.status);
    const suffix = query.toString() ? `?${query.toString()}` : "";
    return toCamel<StaffRegister>(await api.get(`/teachers/attendance/register${suffix}`));
}

export interface StaffAttendanceEntry {
    employeeId: string;
    status: StaffAttendanceMark;
    remarks?: string | null;
}

/**
 * Mark a whole day. Answers with the day as it now reads, so the table updates
 * from the server's own numbers rather than from what was sent.
 */
export async function markStaffAttendance(input: {
    date: string;
    records: StaffAttendanceEntry[];
}): Promise<StaffRegister> {
    return toCamel<StaffRegister>(
        await api.post("/teachers/attendance/bulk", {
            date: input.date,
            records: input.records.map((entry) => ({
                employee_id: entry.employeeId,
                status: entry.status,
                remarks: entry.remarks ?? null,
            })),
        }),
    );
}

/** Correct one recorded day. `409` for a leaver or somebody on approved leave. */
export async function amendStaffAttendance(
    recordId: string,
    input: { status?: StaffAttendanceMark; remarks?: string | null },
): Promise<StaffAttendanceDay> {
    const body: Record<string, unknown> = {};
    if (input.status !== undefined) body.status = input.status;
    if (input.remarks !== undefined) body.remarks = input.remarks;
    return toCamel<StaffAttendanceDay>(
        await api.patch(`/teachers/attendance/records/${recordId}`, body),
    );
}

/** One person's month, with the counts and the percentage beside the grid. */
export async function getStaffMonth(employeeId: string, month?: string): Promise<StaffMonth> {
    const suffix = month ? `?month=${encodeURIComponent(month)}` : "";
    return toCamel<StaffMonth>(
        await api.get(`/teachers/attendance/employees/${employeeId}${suffix}`),
    );
}

/**
 * The caller's own reads (`/teachers/me…`).
 *
 * The employee id comes from the token, not the URL: a teacher reading their own
 * week or month needs no office permission, and cannot reach a colleague by guessing
 * an id. The office routes keep their own, narrower rights.
 */
export async function getMyStaffRow(): Promise<StaffMember> {
    return toCamel<StaffMember>(await api.get("/teachers/me"));
}

export async function getMyWeek(): Promise<StaffWeek> {
    return toCamel<StaffWeek>(await api.get("/teachers/me/week"));
}

export async function getMyAttendance(month?: string): Promise<StaffMonth> {
    const suffix = month ? `?month=${encodeURIComponent(month)}` : "";
    return toCamel<StaffMonth>(await api.get(`/teachers/me/attendance${suffix}`));
}

/** A single directory row (`/teachers/{id}`, 404 when the caller may not see them). */
export async function getStaffMember(teacherId: string): Promise<StaffMember> {
    return toCamel<StaffMember>(await api.get(`/teachers/${teacherId}`));
}

// ============================================================
// The profile drawer
//
// One read (`GET /teachers/{id}/profile`) returns the person **and** the four
// lists, so the drawer's tabs cannot disagree with each other. Writes answer with
// the row they changed, and the drawer refetches the whole profile afterwards:
// a designation change also appends a history row, and that row is part of the
// answer the office wants to see.
// ============================================================

/**
 * The person, their post, and every list the drawer's tabs show.
 *
 * `reveal` asks for the **unmasked** Aadhaar / PAN / bank numbers. The server
 * masks them for everybody; a full answer needs `teachers.view_kyc` *and* this
 * flag, and the reveal itself is written to the staff audit trail - which is why
 * the drawer asks for it only when somebody presses "Show full", never on load.
 */
export async function getStaffProfile(
    teacherId: string,
    reveal = false,
): Promise<StaffProfileDetail> {
    const suffix = reveal ? "?reveal=true" : "";
    return toCamel<StaffProfileDetail>(await api.get(`/teachers/${teacherId}/profile${suffix}`));
}

/** What the post itself may be edited to. */
export interface EmploymentInput {
    designation?: string | null;
    employmentType?: string | null;
    probationEnd?: string | null;
    reportsToEmployeeId?: string | null;
}

/** Save the post. Answers with the whole profile (a change may add history). */
export async function saveEmployment(
    teacherId: string,
    input: EmploymentInput,
): Promise<StaffProfileDetail> {
    const body: Record<string, unknown> = {};
    if ("designation" in input) body.designation = input.designation;
    if ("employmentType" in input) body.employment_type = input.employmentType;
    if ("probationEnd" in input) body.probation_end = input.probationEnd;
    if ("reportsToEmployeeId" in input) body.reports_to_employee_id = input.reportsToEmployeeId;
    return toCamel<StaffProfileDetail>(
        await api.put(`/teachers/profile/${teacherId}/employment`, body),
    );
}

/** Replace what the teacher is listed as able to teach. Answers with the stored line. */
export async function replaceSubjectTags(
    teacherId: string,
    subjectTags: string,
): Promise<string | null> {
    const stored = await api.put<{ subject_tags: string | null }>(
        `/teachers/profile/${teacherId}/subject-tags`,
        { subject_tags: subjectTags },
    );
    return stored.subject_tags ?? null;
}

export interface QualificationInput {
    degree: string;
    institution?: string | null;
    yearCompleted?: number | null;
    grade?: string | null;
}

export async function addQualification(
    teacherId: string,
    input: QualificationInput,
): Promise<StaffQualification> {
    return toCamel<StaffQualification>(
        await api.post(`/teachers/profile/${teacherId}/qualifications`, {
            degree: input.degree,
            institution: input.institution ?? null,
            year_completed: input.yearCompleted ?? null,
            grade: input.grade ?? null,
        }),
    );
}

export async function deleteQualification(teacherId: string, rowId: string): Promise<void> {
    await api.delete(`/teachers/profile/${teacherId}/qualifications/${rowId}`);
}

export interface ExperienceInput {
    employer: string;
    designation?: string | null;
    fromDate: string;
    toDate?: string | null;
    note?: string | null;
}

export async function addExperience(
    teacherId: string,
    input: ExperienceInput,
): Promise<StaffExperience> {
    return toCamel<StaffExperience>(
        await api.post(`/teachers/profile/${teacherId}/experiences`, {
            employer: input.employer,
            designation: input.designation ?? null,
            from_date: input.fromDate,
            to_date: input.toDate ?? null,
            note: input.note ?? null,
        }),
    );
}

export async function deleteExperience(teacherId: string, rowId: string): Promise<void> {
    await api.delete(`/teachers/profile/${teacherId}/experiences/${rowId}`);
}

export interface CertificationInput {
    name: string;
    issuer?: string | null;
    issuedOn?: string | null;
    validTill?: string | null;
    referenceNo?: string | null;
}

export async function addCertification(
    teacherId: string,
    input: CertificationInput,
): Promise<StaffCertification> {
    return toCamel<StaffCertification>(
        await api.post(`/teachers/profile/${teacherId}/certifications`, {
            name: input.name,
            issuer: input.issuer ?? null,
            issued_on: input.issuedOn ?? null,
            valid_till: input.validTill ?? null,
            reference_no: input.referenceNo ?? null,
        }),
    );
}

export async function deleteCertification(teacherId: string, rowId: string): Promise<void> {
    await api.delete(`/teachers/profile/${teacherId}/certifications/${rowId}`);
}

// ============================================================
// Documents and the audit trail
//
// A document is addressed by its **row id**; the file itself is streamed by the
// download route, so nothing here ever builds a path. `api.blob` exists for that
// one case - the JSON methods would corrupt the bytes.
// ============================================================

/** Upload one document (PDF / Word / image) with its type and an optional title. */
export async function uploadStaffDocument(
    teacherId: string,
    input: { file: File; docType: string; title?: string | null },
): Promise<StaffDocumentRow> {
    const form = new FormData();
    form.append("file", input.file);
    form.append("doc_type", input.docType);
    if (input.title?.trim()) form.append("title", input.title.trim());
    return toCamel<StaffDocumentRow>(
        await api.postForm(`/teachers/profile/${teacherId}/documents`, form),
    );
}

/**
 * The stored file, as a `Blob`.
 *
 * Handed back rather than saved here: the drawer knows the original file name
 * (the row carries it) and a service should not touch the DOM.
 */
export async function fetchStaffDocument(teacherId: string, documentId: string): Promise<Blob> {
    return api.blob(`/teachers/profile/${teacherId}/documents/${documentId}/download`);
}

/** Mark a document as seen against the original, or take that back. */
export async function verifyStaffDocument(
    teacherId: string,
    documentId: string,
    verified = true,
): Promise<StaffDocumentRow> {
    return toCamel<StaffDocumentRow>(
        await api.patch(`/teachers/profile/${teacherId}/documents/${documentId}`, {
            verified,
        }),
    );
}

/** Delete the row and the file. The audit trail keeps the line. */
export async function deleteStaffDocument(teacherId: string, documentId: string): Promise<void> {
    await api.delete(`/teachers/profile/${teacherId}/documents/${documentId}`);
}

/**
 * Who changed what, newest first - the whole school or one person.
 *
 * Chronology, not alphabetical order: the question an audit feed answers is
 * "what happened last", so it is the one list on this screen that reads
 * newest-first.
 */
export async function getStaffAudit(
    options: {
        employeeId?: string;
        section?: string;
        limit?: number;
        offset?: number;
    } = {},
): Promise<StaffAuditEntry[]> {
    const params = new URLSearchParams();
    if (options.employeeId) params.set("employee_id", options.employeeId);
    if (options.section) params.set("section", options.section);
    if (options.limit) params.set("limit", String(options.limit));
    if (options.offset) params.set("offset", String(options.offset));
    const query = params.toString();
    return toCamel<StaffAuditEntry[]>(await api.get(`/teachers/audit${query ? `?${query}` : ""}`));
}
