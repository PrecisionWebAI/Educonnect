// ==========================================================
// EduConnect Frontend — shared domain & app types
// ==========================================================

/**
 * Role codenames exactly as the API returns them (upper-cased `role.codename`).
 *
 * A person may hold several at once - a principal who also teaches, a teacher who
 * is also a parent - so `User.roles` is a list and the permissions a session has
 * are the union of all of them.
 */
export type Role =
    | "SYSTEM_ADMIN"
    | "SCHOOL_ADMIN"
    | "PRINCIPAL"
    | "VICE_PRINCIPAL"
    | "HOD"
    | "TEACHER"
    | "ACCOUNTANT"
    | "LIBRARIAN"
    | "TRANSPORT"
    | "STAFF"
    | "STUDENT"
    | "GUARDIAN";

export const ROLE_LABELS: Record<Role, string> = {
    SYSTEM_ADMIN: "System Admin",
    SCHOOL_ADMIN: "School Admin",
    PRINCIPAL: "Principal",
    VICE_PRINCIPAL: "Vice Principal",
    HOD: "Head of Dept.",
    TEACHER: "Teacher",
    ACCOUNTANT: "Accountant",
    LIBRARIAN: "Librarian",
    TRANSPORT: "Transport",
    STAFF: "Staff",
    STUDENT: "Student",
    GUARDIAN: "Parent",
};

export interface User {
    id: string;
    username: string;
    email: string;
    fullName: string;
    roles: Role[];
    role?: string; // primary role, for the places that want a single answer
    permissions?: string[];
    department?: string;
    /** The school this session is confined to; absent for a platform admin. */
    schoolId?: string | null;
    /** That school's name — what the header shows in place of the old search box. */
    schoolName?: string | null;
    /**
     * A platform admin who picked one school in "Switch account": the identity and
     * permissions are still the admin's own, only the data is that school's.
     */
    schoolScope?: boolean;
    /** Set when a platform admin switched into this account ("view as"). */
    impersonatedBy?: { id: string; fullName: string; email: string } | null;
}

export interface Session {
    user: User;
    accessToken: string;
    refreshToken: string;
}

// ---- Academic domain -------------------------------------

export interface ClassInfo {
    id: string;
    name: string;
    section: string;
    classTeacher: string;
    strength: number;
}

export interface Student {
    id: string;
    admissionNo: string;
    name: string;
    className: string;
    section: string;
    gender: "Male" | "Female";
    guardian: string;
    phone: string;
    email: string;
    status: "Active" | "Inactive";
    /** The guardian's login, when the student came through an admission. */
    guardianEmail?: string | null;
    guardianUserId?: string | null;
}

/**
 * What `DELETE /students/{id}` removed.
 *
 * A class-section exists because students sit in it, so the **last** student takes
 * it with them: `classroomRemoved` names the class-section that went ("Class 10-A"),
 * or is `null` when other students still sit there.
 */
export interface StudentDeleteResult {
    deleted: boolean;
    id: string;
    classroomRemoved: string | null;
    /**
     * True when the child's login went with them. `false` means it is still there,
     * because the same person signs in as something else (a parent, a member of staff) —
     * a login only ever goes when it opened nothing else.
     */
    loginRemoved: boolean;
}

// ---------------------------------------------------------------------------
// Guardians (the card on a student's screen)
//
// A guardian is a **person**: one row, one login, one number, shared by every child of
// that family. The link carries what is about *this* child - the relation and whether
// they are the primary contact.
// ---------------------------------------------------------------------------

export interface GuardianLink {
    linkId: string;
    guardianId: string;
    name: string;
    relation: string;
    isPrimary: boolean;
    phone: string;
    email?: string | null;
    alternatePhone?: string | null;
    occupation?: string | null;
    address?: string | null;
    /** The login they sign in with, when they have one. */
    loginEmail?: string | null;
    /** The first-time password: present only on the response that created the login. */
    password?: string | null;
}

export interface GuardianInput {
    name: string;
    phone: string;
    relation?: string;
    email?: string;
    alternate_phone?: string;
    occupation?: string;
    address?: string;
    is_primary?: boolean;
}

export interface GuardianRemoveResult {
    removed: boolean;
    guardianId: string;
    /** True when the person has no other child here (they are kept, not deleted). */
    personKept: boolean;
    /** The guardian that took over as primary, if the removed one held it. */
    primaryMovedTo?: string | null;
}

export interface AttendanceRecord {
    id: string;
    studentName: string;
    className: string;
    date: string;
    status: "Present" | "Absent" | "Late" | "Leave";
}

export interface MarksRow {
    subject: string;
    /** The subject's id, when the row came from a class-section's marks. */
    subjectId?: string;
    max: number;
    obtained: number;
}

export interface MarksEntry {
    studentId: string;
    studentName: string;
    className: string;
    exam: string;
    /** The exam's id, when the entry came from a class-section's marks. */
    examId?: string;
    admissionNumber?: string;
    rows: MarksRow[];
}

export interface TimetableSlot {
    day: string;
    period: string;
    className: string;
    subject: string;
    teacher: string;
}

// ---- Dashboard / analytics -------------------------------

export interface Kpi {
    label: string;
    value: string;
    delta: number; // +% vs last term (positive good)
    icon: string;
    hint?: string;
}

export interface DashboardData {
    greeting: string;
    kpis: Kpi[];
    attendanceTrend: { label: string; value: number }[];
    classReport: { name: string; attending: number; marks: number }[];
    upcoming: { title: string; when: string; type: string }[];
    notices: { title: string; body: string; time: string }[];
}

// ---- Role-mastered dashboard data (PAGE 02) ----

export interface ApprovalItem {
    id: string;
    kind: "Leave" | "Fee waiver" | "Mark dispute" | "Paper approval";
    summary: string;
    requester: string;
    time: string;
}

export interface OperationsBoard {
    runningClasses: number;
    presentTeachers: number;
    teachersTotal: number;
    substitutes: number;
    upcomingEvents: { title: string; when: string }[];
}

export interface ClassAttendanceStat {
    id: string;
    name: string;
    present: number;
    total: number;
}

export interface SubjectPerf {
    subject: string;
    className: string;
    average: number;
    weakTopic: string;
}

export interface TodayClassItem {
    id: string;
    subject: string;
    className: string;
    period: string;
    room: string;
}

export interface HomeworkStatusItem {
    className: string;
    subject: string;
    assigned: number;
    submitted: number;
}

export interface SubjectLeaveItem {
    id: string;
    student: string;
    type: string;
    range: string;
}

export interface MeetingReminderItem {
    id: string;
    parent: string;
    time: string;
}

export interface StudentHomeworkItem {
    id: string;
    title: string;
    subject: string;
    due: string;
    done: boolean;
}

export interface RecentGradeItem {
    subject: string;
    score: number;
    max: number;
}

export interface StudentPortalData {
    name: string;
    className: string;
    section: string;
    attendancePct: number;
    avgMarks: number;
    rank: number;
    todaySchedule: TodayClassItem[];
    homework: StudentHomeworkItem[];
    recentGrades: RecentGradeItem[];
    leaves: {
        id: string;
        type: string;
        range: string;
        status: "Pending" | "Approved" | "Rejected";
    }[];
    tickets: { id: string; title: string; status: "Open" | "In Progress" | "Resolved" }[];
}

export interface ChildSummary {
    id: string;
    name: string;
    className: string;
    section: string;
    attendancePct: number;
    avgMarks: number;
    feeStatus: "On track" | "Due";
    pendingHw: number;
}

export interface AccountantSummary {
    collectedToday: string;
    collectedMonth: string;
    pendingDues: number;
    payrollRun: string;
}

// ---- Wave 3: Teachers / Payroll / Finance / Library / Transport ----

/**
 * One row of the staff directory (`GET /teachers`).
 *
 * The API speaks snake_case and `toCamel` in the service renames it, so the field
 * names here are the ones the screen reads. `staffCode` and the other camelCase
 * names on the wire are the backend's own historical spelling and arrive as they
 * are.
 */
export interface StaffMember {
    id: string;
    userId: string;
    staffCode: string;
    name: string;
    /** Subjects the teacher can take; "" when none is listed yet. */
    subject: string;
    department: string;
    qualification: string | null;
    joiningDate: string;
    phone: string;
    email: string;
    /**
     * Employment state, not login state: `Inactive` means off the staff roll and
     * `On Leave` means an approved leave covers today.
     */
    status: "Active" | "On Leave" | "Inactive";
    classes: string[];
    /** Timetable periods a week. */
    workload: number;
}

/** The tiles above the directory - counted by the server, not by the page. */
export interface StaffSummary {
    total: number;
    active: number;
    onLeaveToday: number;
    inactive: number;
    /** Which tab these tiles count: the Teachers half or the Staff half (0.9). */
    kind: "teacher" | "staff";
    /** False for staff: the periods tile is not drawn at all (0 would read as "no load"). */
    showsPeriods: boolean;
    periodsPerWeek: number;
    withoutTimetable: number;
}

/** One row of the Staff / Student leave tab (`GET /leave/requests?kind=`). */
export interface LeaveTabRow {
    id: string;
    kind: "staff" | "student";
    person: string;
    code: string | null;
    leaveType: string;
    fromDate: string;
    toDate: string;
    days: number;
    status: string;
    requesterUserId: string;
}

/** Which leave tabs the caller may open (`GET /leave/visible-kinds`). */
export interface VisibleLeaveKinds {
    kinds: ("staff" | "student")[];
}

// ---- The staff profile drawer (`GET /teachers/{id}/profile`) ----

/**
 * One degree on a profile. `yearCompleted` is nullable on purpose: the office
 * often records the degree first, and a blank year is not the year 0.
 */
export interface StaffQualification {
    id: string;
    degree: string;
    institution: string | null;
    yearCompleted: number | null;
    grade: string | null;
}

/** One earlier job. `toDate: null` means "still there". */
export interface StaffExperience {
    id: string;
    employer: string;
    designation: string | null;
    fromDate: string;
    toDate: string | null;
    note: string | null;
}

/** A certificate. `validTill` is what makes an expired one visible as a date. */
export interface StaffCertification {
    id: string;
    name: string;
    issuer: string | null;
    issuedOn: string | null;
    validTill: string | null;
    referenceNo: string | null;
}

/** The events the employment history records (the API's closed vocabulary). */
export type StaffEmploymentEvent =
    "Joined" | "Promoted" | "Transferred" | "Designation changed" | "Left";

/**
 * One file the school holds for a person.
 *
 * There is **no storage key and no path** on this row, on purpose: a download is
 * addressed by the row's id (`/teachers/profile/{id}/documents/{docId}/download`)
 * and the server resolves the file itself, so a client can never compose a path
 * of its own.
 */
export interface StaffDocumentRow {
    id: string;
    /** One of the closed `doc_type` vocabulary (`aadhaar`, `degree`, …). */
    docType: string;
    /** The screen's word for it ("Aadhaar Card"), so the drawer owns no copy. */
    docTypeLabel: string;
    title: string | null;
    fileName: string;
    contentType: string | null;
    sizeBytes: number;
    /** The day the office saw the original; `null` means pending. */
    verifiedOn: string | null;
    verifiedBy: string | null;
    uploadedBy: string | null;
    createdAt: string | null;
}

/**
 * Aadhaar / PAN / bank detail.
 *
 * `masked` is what the drawer keys on, so it never has to guess whether
 * "XXXX XXXX 9012" is a mask or a value somebody typed; `canReveal` says whether
 * asking for the full number would be allowed.
 */
export interface StaffKyc {
    aadhaarNo: string | null;
    panNo: string | null;
    bankName: string | null;
    bankAccountNo: string | null;
    ifsc: string | null;
    masked: boolean;
    canReveal: boolean;
}

/** One line of the staff audit trail (`GET /teachers/audit`). Append-only. */
export interface StaffAuditEntry {
    id: string;
    employeeId: string;
    employeeName: string;
    section: string;
    action: string;
    rowId: string | null;
    summary: string;
    changedBy: string | null;
    createdAt: string | null;
}

/** One employment event. Append-only: nothing in the UI edits or deletes these. */
export interface StaffHistoryEvent {
    id: string;
    event: StaffEmploymentEvent;
    effectiveOn: string;
    fromValue: string | null;
    toValue: string | null;
    note: string | null;
    recordedBy: string | null;
    createdAt: string | null;
}

/**
 * One person, as the profile drawer shows them: the roll facts **and** the four
 * lists, in one read - so the tabs can never disagree with the row that opened
 * the drawer.
 */
export interface StaffProfileDetail {
    id: string;
    userId: string;
    staffCode: string;
    name: string;
    department: string;
    designation: string | null;
    employmentType: string | null;
    qualification: string | null;
    experienceYears: number;
    joiningDate: string;
    probationEnd: string | null;
    reportsTo: string | null;
    reportsToEmployeeId: string | null;
    phone: string;
    email: string;
    address: string | null;
    emergencyContact: string | null;
    status: StaffMember["status"];
    subjects: string[];
    classes: string[];
    workload: number;
    capacity: number;
    utilisation: number;
    qualifications: StaffQualification[];
    experiences: StaffExperience[];
    certifications: StaffCertification[];
    history: StaffHistoryEvent[];
    /** The dossier - rows only, never a path (see `StaffDocumentRow`). */
    documents: StaffDocumentRow[];
    /** Masked unless the caller asked with `reveal` and holds `teachers.view_kyc`. */
    kyc: StaffKyc;
}

/** One row of the workload matrix: a teacher's load against the school's week. */
export interface WorkloadMatrixRow {
    id: string;
    staff: string;
    subject: string;
    classes: string[];
    periods: number;
    /** The week this load is a share of: the school's rule, or the timetable. */
    capacity: number;
    /** Which of the two the number above came from - the screen prints both. */
    capacitySource: "rule" | "timetable";
    /** What the timetable itself runs, whatever the rule says. */
    weekSlots: number;
    /** Duties still standing today - counted, never converted into periods. */
    duties: number;
    /** Periods the week's log records as taught (`classlog`) - Phase 5. */
    completedThisWeek: number;
    /** `periods - completedThisWeek`, floored at 0: what is left of the plan. */
    remainingThisWeek: number;
    /** Periods covered for an absent colleague this week (approved covers only). */
    substitutePeriods: number;
    freePeriods: number;
    utilisation: number;
    /** Over the line. Not `utilisation > 100`: the bar caps at 100. */
    overloaded: boolean;
    band: "Overloaded" | "Steady" | "Light" | "Unassigned";
}

/** The school's definition of a full week (`GET /teachers/workload/rules`). */
export interface WorkloadRule {
    weeklyPeriods: number | null;
    overloadPercent: number;
    underloadPercent: number;
    /** False when nobody has stated a capacity yet - the dialog's first edit. */
    isSet: boolean;
    updatedAt: string | null;
    updatedBy: string | null;
}

/** One duty on a person's file: exam invigilation, a gate, the library desk. */
export interface StaffDuty {
    id: string;
    dutyType: string;
    /** The screen's word for `dutyType` (`Exam Duty`). */
    dutyTypeLabel: string;
    title: string | null;
    dayOfWeek: string | null;
    dayLabel: string | null;
    onDate: string | null;
    startTime: string | null;
    endTime: string | null;
    /** `09:00-11:00`, or `null` for a duty with no hours. */
    slot: string | null;
    hours: number;
    effectiveFrom: string;
    effectiveTo: string | null;
    note: string | null;
    createdAt: string | null;
}

/** One cell of a staff week grid: a taught period or a duty. */
export interface StaffWeekSlot {
    kind: "period" | "duty";
    day: string;
    dayLabel: string;
    start: string | null;
    end: string | null;
    slot: string;
    subject: string;
    classLabel: string | null;
    room: string | null;
    title: string | null;
    periodId: string | null;
    dutyId: string | null;
}

/** One column of the week grid. An empty day is still a day. */
export interface StaffWeekDay {
    day: string;
    dayLabel: string;
    slots: StaffWeekSlot[];
    periods: number;
    duties: number;
}

/** One person's week (`GET /teachers/workload/{id}/week`). */
export interface StaffWeek {
    id: string;
    name: string;
    department: string;
    days: StaffWeekDay[];
    periods: number;
    duties: number;
    /** Hours of duty only - duties are never converted into periods. */
    dutyHours: number;
    emptyDays: number;
}

/** One row of the analytics split, ascending by department. */
export interface DepartmentLoad {
    department: string;
    staff: number;
    periods: number;
    utilisation: number;
    overloaded: number;
}

/** The tiles above the matrix (`GET /teachers/workload/analytics`). */
export interface WorkloadAnalytics {
    capacity: number;
    capacitySource: "rule" | "timetable";
    weekSlots: number;
    weeklyPeriodsRule: number | null;
    staff: number;
    totalPeriods: number;
    averagePeriods: number;
    averageUtilisation: number;
    overloaded: number;
    /** On the roll with no period in the timetable yet. */
    unassigned: number;
    duties: number;
    byDepartment: DepartmentLoad[];
}

/** What a register row may say. `on_leave` and `not_marked` are derived, not stored. */
export type StaffAttendanceStatus = "present" | "absent" | "half_day" | "on_leave" | "not_marked";

/** One line of the daily register (`GET /teachers/attendance/register`). */
export interface StaffAttendanceRow {
    employeeId: string;
    employeeCode: string;
    name: string;
    department: string;
    designation: string | null;
    status: StaffAttendanceStatus;
    /** The server's word for `status` (`Half Day`, `On Leave`, `Not Marked`). */
    statusLabel: string;
    /** False for `on_leave` / `not_marked` - neither is a recorded row. */
    isMarked: boolean;
    /** The row to amend, or `null` when nobody has marked this day. */
    recordId: string | null;
    remarks: string | null;
    /** The leave that made this person `On Leave` (`Medical`, `Casual`). */
    leaveType: string | null;
    markedBy: string | null;
    markedAt: string | null;
}

/**
 * One day's register: every person on the roll, plus the counts above them.
 *
 * The counts describe the **day** (the department filter applies, the status
 * filter does not), so narrowing the list never rewrites the numbers.
 */
export interface StaffRegister {
    date: string;
    weekday: string;
    rows: StaffAttendanceRow[];
    total: number;
    present: number;
    absent: number;
    halfDay: number;
    onLeave: number;
    /** On the roll, no row, no leave - the office's to-do list. */
    notMarked: number;
    marked: number;
    /** Present + half days over the **marked** days. */
    percent: number;
}

/** One day in a person's month grid. */
export interface StaffAttendanceDay {
    date: string;
    day: number;
    weekday: string;
    status: StaffAttendanceStatus;
    statusLabel: string;
    remarks: string | null;
    leaveType: string | null;
    recordId: string | null;
    markedBy: string | null;
    markedAt: string | null;
}

/** One person's month (`GET /teachers/attendance/employees/{id}?month=YYYY-MM`). */
export interface StaffMonth {
    employeeId: string;
    employeeCode: string;
    name: string;
    department: string;
    /** `2026-11`, the key that was asked for. */
    month: string;
    /** `November 2026`, so the sheet does not re-implement month names. */
    monthLabel: string;
    days: StaffAttendanceDay[];
    present: number;
    absent: number;
    halfDay: number;
    onLeave: number;
    notMarked: number;
    marked: number;
    /** Days attended as a share of the days somebody marked. */
    percent: number;
}

/** One row of the staff leave screen (`GET /leave/staff-requests`). */
export interface StaffLeaveItem {
    id: string;
    /** The employee the leave belongs to; `null` for a requester with no record. */
    employeeId: string | null;
    staffName: string;
    staffCode: string;
    role: string;
    department: string;
    leaveType: string;
    fromDate: string;
    toDate: string;
    days: number;
    reason: string;
    /** Who covers the class - `null` until substitutions are assigned. */
    substitute: string | null;
    /**
     * Days left in this type for the leave's own year, counted from the requests.
     * `0` is "none left"; `null` is "this school tracks no balance for this type".
     */
    balance: number | null;
    status: "Pending" | "Approved" | "Rejected" | "Cancelled";
    appliedAt: string;
    /** Who decided it, and when. `null` while pending. */
    decidedBy: string | null;
    decidedAt: string | null;
    decisionNote: string | null;
}

/** What the api answers a write with - apply, approve, reject and cancel alike. */
export interface LeaveRequestResult {
    id: string;
    scope: "staff" | "student";
    person: string;
    personCode: string;
    leaveType: string;
    fromDate: string;
    toDate: string;
    days: number;
    reason: string;
    status: StaffLeaveItem["status"];
    /** Days left for this type after the write; `null` for a student or untracked type. */
    balanceRemaining: number | null;
    decidedBy: string | null;
    decidedAt: string | null;
    decisionNote: string | null;
    appliedAt: string;
}

/** One leave type and what the school grants for it (`GET /leave/policies`). */
export interface LeavePolicy {
    leaveType: string;
    annualDays: number;
    /** `null` for the built-in defaults - nobody has saved this row yet. */
    updatedBy: string | null;
    updatedAt: string | null;
}

/** One person, one leave type, one year (`GET /leave/balances`). */
export interface LeaveBalanceRow {
    employeeId: string;
    employeeCode: string;
    staffName: string;
    department: string;
    leaveType: string;
    year: number;
    /** `null` when the school tracks no entitlement for this type. */
    entitled: number | null;
    used: number;
    pending: number;
    remaining: number | null;
    source: "policy" | "override" | "untracked";
}

export interface LeaveBalances {
    year: number;
    /** The types in the order the screen lists its columns. */
    types: string[];
    rows: LeaveBalanceRow[];
}

/** What the apply form sends. Exactly one of the two ids, or neither (own leave). */
export interface LeaveApplyInput {
    employeeId?: string | null;
    studentId?: string | null;
    leaveType: string;
    fromDate: string;
    toDate: string;
    reason?: string;
}

/** A teacher's average rating (`GET /teachers/performance`). */
/** One ingredient of the overall score; `value` is null when there is no data. */
export interface StaffPerformanceComponent {
    key: "attendance" | "reviews" | "syllabus" | "leave";
    label: string;
    value: number | null;
    weight: number;
    display: string;
}

export interface StaffPerformanceRow {
    id: string;
    staff: string;
    /** Which tab the row belongs to: staff have no syllabus component (0.9). */
    kind: "teacher" | "staff";
    rating: number;
    reviews: number;
    trend: "up" | "flat" | "down";
    /** Null when nothing is recorded yet - never a fabricated 0. */
    score: number | null;
    components: StaffPerformanceComponent[];
}

export interface PayrollEntry {
    id: string;
    staffCode: string;
    name: string;
    basic: number;
    allowances: number;
    deductions: number;
    net: number;
    status: "Draft" | "Posted" | "Paid";
}

export interface SalaryStructureRow {
    id: string;
    staffCode: string;
    name: string;
    basic: number;
    hra: number;
    da: number;
    special: number;
    total: number;
}

export interface FeeInvoice {
    id: string;
    student: string;
    className: string;
    head: string;
    amount: number;
    paid: number;
    due: number;
    status: "Paid" | "Partial" | "Due";
}

// ---- Wave 4: Homework / Classroom --------------------------

export interface HomeworkItem {
    id: string;
    title: string;
    subject: string;
    className: string;
    due: string;
    assignedBy: string;
    description: string;
}

export interface SubmissionItem {
    id: string;
    homeworkTitle: string;
    student: string;
    status: "Submitted" | "Pending" | "Late";
    submittedAt: string;
}

export interface DiaryEntry {
    id: string;
    className: string;
    day: string;
    subject: string;
    topic: string;
    homework: string;
    activity: string;
}

export interface ClassroomItem {
    id: string;
    title: string;
    subject: string;
    className: string;
    /** The class-section's id — what "Open Class" links to. */
    sectionId: string;
    teacher: string;
    nextLesson: string;
    students: number;
}

/** One class-section card on the Classroom grid (principal and above).
 *  A `null` figure means "no data behind it yet" - the card shows a dash. */
export interface ClassSectionCard {
    sectionId: string;
    sectionName: string;
    classTeacher: string | null;
    strength: number;
    boys: number;
    girls: number;
    presentToday: number;
    attendanceDate: string | null;
    attendancePercent: number | null;
    feesExpected: number | null;
    feesCollected: number | null;
    feesPercent: number | null;
    syllabusPercent: number | null;
    subjectsTracked: number;
    homeworkOpen: number;
    timetablePeriods: number;
    avgMarksPercent: number | null;
    examsCount: number;
    lastDiaryDate: string | null;
}

/** A class heading ("Class 6") with its section cards beneath it. */
export interface ClassGroup {
    classroomId: string;
    className: string;
    level: number;
    stage: string;
    strength: number;
    sectionCount: number;
    sections: ClassSectionCard[];
}

// --- Phase 2: the drill-down behind one class-section card ------------------

export interface SectionClassTeacher {
    employeeId: string | null;
    name: string | null;
    email: string | null;
    phone: string | null;
}

export interface SectionStudentRow {
    studentId: string;
    name: string;
    admissionNumber: string;
    guardian: string | null;
    gender: string | null;
    attendancePercent: number | null;
    feesPaid: number;
    feesDue: number;
}

export interface AttendanceDayRow {
    date: string;
    present: number;
    absent: number;
    leave: number;
    late: number;
    total: number;
    percent: number;
}

export interface TimetableSlotRow {
    day: string;
    startTime: string;
    endTime: string;
    subject: string;
    teacher: string | null;
    room: string | null;
}

export interface HomeworkRowItem {
    id: string;
    title: string;
    subject: string;
    teacher: string | null;
    dueDate: string;
    submitted: number;
    total: number;
}

export interface DiaryRowItem {
    id: string;
    date: string;
    teacher: string | null;
    note: string;
}

export interface ExamRowItem {
    id: string;
    name: string;
    term: string | null;
    status: string;
    averagePercent: number | null;
    marksEntered: number;
}

export interface SubjectMarkRowItem {
    subject: string;
    averagePercent: number | null;
    highest: number | null;
    lowest: number | null;
    entries: number;
}

/** Everything the class-section drill-down shows. */
/** One subject taught in a section, and who takes it (null until assigned). */
export interface SectionSubjectRow {
    subjectId: string;
    name: string;
    code: string;
    teacherId: string | null;
    teacherName: string | null;
}

/** A teacher the Classroom screen can assign to a class-section. */
export interface TeacherOption {
    employeeId: string;
    name: string;
    email: string;
}

export interface SectionDetail {
    sectionId: string;
    classLabel: string;
    className: string;
    /** The class's own id — the Timetable tab reads this section's week by it. */
    classroomId: string;
    /** The section letter on its own ("J") - what the Students / Attendance tabs scope by. */
    sectionName: string;
    stage: string;
    classTeacher: SectionClassTeacher | null;
    strength: number;
    boys: number;
    girls: number;
    attendancePercent: number | null;
    syllabusPercent: number | null;
    feesExpected: number | null;
    feesCollected: number | null;
    feesPercent: number | null;
    students: SectionStudentRow[];
    attendance: AttendanceDayRow[];
    timetable: TimetableSlotRow[];
    homework: HomeworkRowItem[];
    diary: DiaryRowItem[];
    exams: ExamRowItem[];
    marks: SubjectMarkRowItem[];
    /** Every subject with its teacher for this section (null where unassigned). */
    subjects: SectionSubjectRow[];
}

export interface LessonResource {
    id: string;
    type: "Video" | "PDF" | "Quiz" | "Link";
    title: string;
}

export interface LessonDetail {
    id: string;
    title: string;
    subject: string;
    className: string;
    duration: string;
    topics: string[];
    resources: LessonResource[];
    homework: string;
}

export interface NotificationItem {
    id: string;
    title: string;
    body: string;
    kind: "Attendance" | "Homework" | "Event" | "Booking" | "Alert" | "System";
    time: string;
    read: boolean;
    to?: "Student" | "Teacher" | "Guardian" | "Staff";
}

export interface LeaveApplicationItem {
    id: string;
    student: string;
    className: string;
    type: "Medical" | "Personal" | "OD" | "Event" | "Travel";
    fromDate: string;
    toDate: string;
    reason: string;
    days: number;
    status: "Pending" | "Approved" | "Rejected";
    submittedAt: string;
}

export interface ChatConversation {
    id: string;
    name: string;
    group: boolean;
    lastMessage: string;
    time: string;
    unread: number;
    online?: boolean;
    avatar?: string;
    pinned?: boolean;
    muted?: boolean;
    relationship?: string;
    whoCanPost?: "all" | "teachers_only";
    entityType?: "student" | "class" | "ticket" | "paper" | "general";
    entityId?: string | number;
    entityContext?: string;
    isAnnouncementChannel?: boolean;
}

export interface ChatContact {
    id: string;
    name: string;
    email: string;
    role: string;
    roleTag: string;
    group: boolean;
    relationship: string;
    threadId?: string;
    online?: boolean;
}

export interface ChatAttachment {
    name: string;
    type: "image" | "pdf" | "audio" | "link";
    url: string;
    size: string;
    safeStatus: "verified" | "warning" | "external";
}

export interface ChatMessageItem {
    id: string;
    threadId: string;
    senderId: string;
    senderName: string;
    senderRole?: string;
    isMe: boolean;
    text: string;
    time: string;
    createdAt: string;
    status: "sent" | "delivered" | "read";
    isOfficial?: boolean;
    isSensitive?: boolean;
    pinProtected?: boolean;
    unlocked?: boolean;
    attachment?: ChatAttachment;
    hasIssueDetected?: boolean;
    convertedTicketId?: string;
    reported?: boolean;
}

export interface GroupSpace {
    id: string;
    name: string;
    category: "class" | "department" | "subject_team" | "club";
    description: string;
    membersCount: number;
    whoCanPost: "all" | "teachers_only";
    isAnnouncementChannel: boolean;
    moderator: string;
    lastActive: string;
    activeNotice?: string;
    threadId: string;
}

export interface InContextEntity {
    id: string;
    type: "student" | "class" | "ticket" | "paper";
    title: string;
    subtitle: string;
    stakeholders: string[];
    threadId: string;
    badge: string;
    hasActiveIssue?: boolean;
}

export interface ClassNotice {
    id: string;
    title: string;
    content: string;
    pinnedBy: string;
    targetClass: string;
    createdAt: string;
    priority: "Normal" | "Urgent";
}

export interface MeetingItem {
    id: string;
    title: string;
    with: string;
    date: string;
    time: string;
    room: string;
    type: "Scheduled" | "Pending" | "Done";
}

export interface TicketItem {
    id: string;
    subject: string;
    category: "IT" | "Accounts" | "Facility" | "Academic" | "Other";
    priority: "Low" | "Medium" | "High";
    status: "Open" | "In Progress" | "Resolved" | "Closed";
    reporter: string;
    assignee: string;
    updated: string;
}

export interface ReportCard {
    id: string;
    title: string;
    metric: string;
    value: string;
    trend: string;
    tone: "green" | "amber" | "red" | "teal";
}

export interface DataQualityRow {
    id: string;
    area: string;
    score: number;
    issue: string;
    status: "Healthy" | "Attention" | "Critical";
}

export interface SettingUser {
    id: string;
    name: string;
    email: string;
    role: "SYSTEM_ADMIN" | "Teacher" | "Accountant" | "Staff";
    status: "Active" | "Invited" | "Disabled";
}

export interface SchoolInfo {
    id: string;
    label: string;
    value: string;
}

export interface SecurityLog {
    id: string;
    event: string;
    /** Renamed from `user` (reserved word) — Phase 1. */
    actor_email: string;
    /** Renamed from `when` (reserved word) — Phase 1. */
    occurred_at: string;
}

export interface CopilotAutomation {
    id: string;
    title: string;
    schedule: string;
    lastRun: string;
    active: boolean;
}

export interface CopilotSuggestion {
    id: string;
    prompt: string;
    tag: string;
}

export interface IrregularStudent {
    id: string;
    name: string;
    className: string;
    absences: number;
    pattern: string;
    risk: "High" | "Medium" | "Low";
}

export interface LeaveSyncRow {
    id: string;
    student: string;
    className: string;
    from: string;
    days: number;
    autoMarked: string;
    status: "Synced" | "Pending" | "Overridden";
}

// ---- Class catalogue (the `classname` + `section` platform tables) ----------
// The vocabulary every class / section control reads. No screen keeps a class
// list of its own, so a class added in the database shows up everywhere at once.

export interface CatalogSection {
    id: string;
    name: string;
    classroomId: string;
}

export interface CatalogClass {
    id: string;
    name: string;
    level: number;
    stage: string;
    sections: CatalogSection[];
}

export interface ClassCatalog {
    classes: CatalogClass[];
    sectionNames: string[];
    stages: string[];
}

export interface CollectionReportRow {
    id: string;
    period: string;
    billed: string;
    collected: string;
    variance: string;
    mode: string;
}

export interface ChatFile {
    id: string;
    name: string;
    sharedBy: string;
    size: string;
    /** Renamed from `when` (reserved word) — Phase 1. */
    sharedAt: string;
    type?: "pdf" | "image" | "audio" | "link";
    safeStatus?: "verified" | "warning" | "external";
    url?: string;
}

export interface EducationReportRow {
    id: string;
    metric: string;
    className: string;
    value: string;
    trend: string;
}

export interface PaletteCommand {
    id: string;
    label: string;
    shortcut: string;
    category: string;
}

export interface GatewayStatus {
    id: string;
    name: string;
    type: string;
    status: "Connected" | "Degraded" | "Down";
    quota: string;
}

export interface LibraryBook {
    id: string;
    isbn: string;
    title: string;
    author: string;
    category: string;
    copies: number;
    available: number;
    overdue?: boolean;
}

export interface BookIssue {
    id: string;
    book: string;
    student: string;
    issued: string;
    due: string;
    status: "Borrowed" | "Returned" | "Overdue";
}

export interface TransportRoute {
    id: string;
    name: string;
    busId: string;
    driver: string;
    stops: number;
    students: number;
    status: "Active" | "Idle";
}

export interface Bus {
    id: string;
    name: string;
    plate: string;
    route: string;
    capacity: number;
    occupied: number;
    status: "En route" | "Parked" | "Service";
}

/* ============================================================
   Operations module (Student Admission / Staff Hiring /
   Fees Structure / Salary)
   NOTE: the list data still comes from the per-feature service
   seeds (services/{admission,hiring,fees-structure,salary}.service.ts)
   while the matching backend endpoints are being built.
   ============================================================ */

/** Everything the admission form collects — mirrors the
 *  ADMISSION FORM -> DATABASE block in db_mapping.txt
 *  (`student`, the one row a learner has).
 *
 *  There is no draft: the form is saved once, and what it saves is a student. So
 *  every field a student cannot be without is marked `required` on the form and
 *  checked before the save (`missingRequiredFields`), not filled in later. */
export interface AdmissionFormValues {
    // STUDENT
    studentFirstName: string;
    studentMiddleName: string;
    studentLastName: string;
    studentEmail: string;
    dateOfBirth: string;
    gender: string;
    bloodGroup: string;
    religion: string;
    category: string;
    motherTongue: string;
    nationality: string;
    aadhaarId: string;
    address: string;
    permanentAddress: string;
    // PREVIOUS SCHOOL
    previousSchoolName: string;
    previousClassPassed: string;
    previousBoard: string;
    transferCertificateNo: string;
    oldUniqueId: string;
    // FATHER — family detail. The **contact** belongs to the guardian: a phone or an
    // email typed here would be dropped by the server, which stores one contact per
    // person (see the GUARDIAN block below).
    fatherName: string;
    fatherOccupation: string;
    fatherAnnualIncome: string;
    // MOTHER — family detail, exactly like the father's.
    motherName: string;
    motherOccupation: string;
    motherAnnualIncome: string;
    // GUARDIAN — the family's contact, and the only block that carries one.
    guardianName: string;
    guardianRelation: string;
    guardianPhone: string;
    guardianEmail: string;
    guardianOccupation: string;
    guardianAddress: string;
    // PLACEMENT + LOGISTICS
    appliedForClassLevel: string;
    /** The catalog id behind `appliedForClassLevel`; "" for a hand-typed class. */
    appliedClassId: string;
    /** defaults to the admission class; editable when the student moved up */
    currentClassOrLastClass: string;
    appliedSectionPreference: string;
    /** The catalog id behind `appliedSectionPreference`; "" when none is picked. */
    appliedSectionId: string;
    needsTransport: string;
    transportRoute: string;
    needsHostel: string;
    // WORKFLOW
    notes: string;
}

/** Whether the student is still on the rolls. */
export type AdmissionStudentStatus = "Active" | "Inactive";

export type SeparationSession = "Completed Session" | "Incomplete Session";

/** Recorded by the Separation action when a student leaves the school. */
export interface SeparationRecord {
    /** class the student was in when they left (fixed in the form) */
    droppedClass: string;
    reason: string;
    session: SeparationSession;
    date: string;
}

/**
 * A saved row: the form values plus what the server stamped on it.
 *
 * There is no draft, so a row is always a student - it has an admission number, a
 * guardian (the contact block is read back from that **person**) and the logins the
 * form's own emails made.
 */
export interface AdmissionApplicationRow extends AdmissionFormValues {
    id: string;
    admissionNumber: string;
    createdOn: string;
    /** Present once the student has been separated (→ Inactive). */
    separation?: SeparationRecord | null;

    // ---- what admitting this student created --------------------------------
    /** The student this row is - its own id (View / Logins / Delete use it). */
    studentId?: string | null;
    studentUserId?: string | null;
    guardianUserId?: string | null;
    /** The logins it created (emails only; the password is never stored). */
    studentLoginEmail?: string | null;
    guardianLoginEmail?: string | null;
    /**
     * The first-time passwords, present **only** on the response that registered
     * the form (or reset one) - that is the one moment they exist.
     */
    credentials?: LoginCredential[] | null;
    /** Set when the student could not be placed in a class. */
    placementNote?: string | null;
}

/** A student or guardian login created while registering an admission. */
export interface LoginCredential {
    role: string;
    fullName: string;
    email: string;
    password: string | null;
    /** false when an existing login was reused (a parent's second child). */
    created: boolean;
}

/** A freshly minted first-time password, returned exactly once. */
export interface PasswordReset {
    role: string;
    fullName: string;
    email: string;
    password: string;
}

/**
 * The four tiles on the Admission screen — counted by the server, for this school.
 *
 * They used to be derived from the row list in the browser, so a school whose roll
 * was larger than the list's cap saw the cap (e.g. 500) on every tile. `GET
 * /admissions/stats` counts them in SQL, inside the same school filter the list uses.
 */
export interface AdmissionStats {
    students: number;
    active: number;
    inactive: number;
    midDropped: number;
}

/** Hiring pipeline stages for a staff candidate (stored in `hiringcandidate`) */
// --- Staff registration (hiring that starts at "this person is hired") ---------
// The short registration form on the Staff Hiring screen. Submitting it hires
// the person: the server creates their login (`tea.*` for teaching posts,
// `stf.*` for the rest) and their staff record, and returns the login once,
// with its first-time password.

export interface StaffRegistrationInput {
    fullName: string;
    /** Roles this hire holds; the first is the primary (its dashboard opens at login). */
    roleCodenames: string[];
    department: string;
    qualification: string;
    experienceYears: number;
    contactEmail: string;
    joiningDate: string;
    //: set when this registration came from the pipeline (the "Hired" button)
    candidateId: string | null;
    // --- expanded employee detail (KYC / bank / salary) -----------------
    phone: string;
    /** Subjects this teacher can teach (many per teacher). */
    subjectIds: string[];
    address: string;
    emergencyContact: string;
    aadhaarNo: string;
    panNo: string;
    bankName: string;
    bankAccountNo: string;
    ifsc: string;
    salaryMonthly: number | null;
    previousEmployerMonthlySalary: number | null;
}

/** The hire response: the created employee plus the one-time login. */
export interface StaffProfileCreateResult extends StaffProfileRow {
    credentials: LoginCredential[] | null;
}

/** A hired staff member — the login + employee record the server created. */
export interface StaffProfileRow {
    id: string;
    userId: string;
    employeeCode: string;
    fullName: string;
    email: string;
    /** The primary role (shown in the Role column). */
    roleCodename: string;
    /** Every role held, primary first. */
    roleCodenames: string[];
    department: string;
    qualification: string | null;
    experienceYears: number;
    joiningDate: string;
    isTeacher: boolean;
    // --- expanded employee detail ---------------------------------------
    contactEmail: string | null;
    phone: string | null;
    /** Every subject this teacher can teach. */
    subjectIds: string[];
    address: string | null;
    emergencyContact: string | null;
    aadhaarNo: string | null;
    panNo: string | null;
    bankName: string | null;
    bankAccountNo: string | null;
    ifsc: string | null;
    salaryMonthly: number | null;
    previousEmployerMonthlySalary: number | null;
    // --- lifecycle (a person who left is deactivated, not deleted) --------
    // `app/domains/staff/lifecycle.py`: withdrawing the roles stamps the day and
    // leaves every row in place, so the salary register still explains itself.
    /** False once their staff side was switched off. */
    isActive: boolean;
    /** The day the office says they left (it can be back-dated). */
    leftOn: string | null;
    /** When the Deactivate button was pressed. */
    deactivatedAt: string | null;
    /** The roles that were withdrawn — reactivating restores exactly these. */
    deactivatedRoles: string[];
    /** True while the login signs in. A teacher who is also a parent keeps theirs. */
    loginActive: boolean;
}

/** Body of a deactivate call: the last day, and why (both optional). */
export interface StaffLifecycleInput {
    leftOn?: string | null;
    reason?: string | null;
}

/**
 * What a deactivate / reactivate call did (`app/core/lifecycle.py::LifecycleRead`).
 *
 * `action` is what just happened; `rolesWithdrawn`/`rolesRestored` name the roles,
 * `rolesKept` the ones the action deliberately left (a teacher-parent is still a
 * parent), and the login flags say whether the account was left, switched off or
 * brought back. `message` is the sentence the screen shows.
 */
export interface StaffLifecycleResult {
    id: string;
    kind: "staff" | "student";
    name: string;
    action: "deactivated" | "reactivated";
    leftOn: string | null;
    deactivatedAt: string | null;
    reason: string | null;
    rolesWithdrawn: string[];
    rolesRestored: string[];
    rolesKept: string[];
    loginKept: boolean;
    loginActive: boolean;
    loginEmail: string | null;
    message: string;
}

export type HiringStatus = "Resume" | "Shortlisted" | "Interview" | "Hired" | "Rejected";

export interface HiringCandidateRow {
    id: string;
    candidateNo: string | null;
    /** assigned on hire — shown in place of the candidate id */
    empId: string | null;
    candidateName: string;
    role: string;
    department: string;
    qualification: string | null;
    experience: number;
    appliedOn: string;
    /** null while no interview has been scheduled */
    interviewOn: string | null;
    status: HiringStatus;
    // --- interview intake (the "schedule interview" form) ---------------
    phone: string | null;
    email: string | null;
    /** role codename applied for (teacher, accountant, ...) */
    appliedFor: string | null;
    subjectId: string | null;
    subjectName: string | null;
    resumePath: string | null;
    /** scheduled interview date + time */
    interviewAt: string | null;
    interviewNote: string | null;
}

/** A school subject, for the interview "Subject" dropdown. */
export interface SubjectRow {
    id: string;
    name: string;
    code: string;
}

/** `feestructure.frequency` — monthly | term | yearly | one_time */
export type FeeFrequency = "Monthly" | "Term" | "Yearly" | "One-time";

export interface FeeStructureRow {
    id: string;
    head: string;
    className: string;
    frequency: FeeFrequency;
    amount: number;
    dueDay: string;
    students: number;
    status: "Active" | "Draft";
}

/** Staff salary register row (`salarypayment`) */
export type SalaryPaymentStatus = "Paid" | "Processing" | "Pending";

export interface SalaryPaymentRow {
    id: string;
    staffCode: string;
    staffName: string;
    designation: string;
    department: string;
    month: string;
    gross: number;
    deductions: number;
    net: number;
    status: SalaryPaymentStatus;
    /** stamped by the server when the row is marked Paid */
    paidOn: string | null;
}

// ============================================================
// Substitution (Phase 7) — the cover board
//
// `absences` comes from the approved leave (and any written absence),
// `periods` from the timetable, and `candidates` from the engine. The
// server derives all three, so a period moved or a leave cancelled this
// morning is reflected without anybody re-entering anything.
// ============================================================

export interface SubstitutionAssignment {
    id: string;
    periodId: string;
    onDate: string;
    absentEmployeeId: string;
    absentName: string;
    substituteEmployeeId: string;
    substituteName: string;
    /** `Assigned` / `Approved`. */
    status: string;
    statusLabel: string;
    note: string | null;
    assignedAt: string | null;
    decidedAt: string | null;
}

export interface SubstitutionAbsence {
    employeeId: string;
    name: string;
    employeeCode: string | null;
    department: string | null;
    /** The leave type, or "Training" / "Official duty". */
    reason: string;
    /** Set when the absence came from an approved leave. */
    leaveType: string | null;
    note: string | null;
    openPeriods: number;
    totalPeriods: number;
}

export interface SubstitutionPeriod {
    periodId: string;
    /** `09:00-09:45`, spelled by the server. */
    slot: string;
    startTime: string;
    endTime: string;
    subjectId: string;
    subject: string;
    /** `Class 9-A`. */
    classLabel: string;
    room: string | null;
    absentEmployeeId: string;
    absentName: string;
    /** `null` while the slot has nobody in front of the class. */
    assignment: SubstitutionAssignment | null;
}

export interface SubstitutionBoard {
    onDate: string;
    weekday: string;
    absences: SubstitutionAbsence[];
    periods: SubstitutionPeriod[];
    total: number;
    covered: number;
    open: number;
    /** True when that weekday has no timetable at all - not "0 open". */
    timetableEmpty: boolean;
}

export interface SubstitutionCandidate {
    employeeId: string;
    name: string;
    employeeCode: string | null;
    department: string | null;
    teachesSubject: boolean;
    sameDepartment: boolean;
    weeklyPeriods: number;
    knowsTheClass: boolean;
    score: number;
    /** Why they are offered, in words ("Teaches Physics; Science department"). */
    reason: string;
}

export interface SubstitutionBlocked {
    employeeId: string;
    name: string;
    /** Why they cannot ("On approved Sick leave"). */
    reason: string;
}

export interface SubstitutionCandidates {
    periodId: string;
    onDate: string;
    slot: string;
    subject: string;
    classLabel: string;
    candidates: SubstitutionCandidate[];
    blocked: SubstitutionBlocked[];
    /** Set when the slot already has a cover. */
    assignment: SubstitutionAssignment | null;
}

export interface SubstitutionAssignInput {
    periodId: string;
    onDate: string;
    absentEmployeeId: string;
    substituteEmployeeId: string;
    note?: string | null;
}

// ============================================================
// Appraisal (Phase 8) — the season, one person's appraisal, goals, training
//
// The rating is 1..5 twice (the person's, then the reviewer's) and
// `finalizedAt` is the lock: after it, every write on that row is refused by
// the server. `achieved: null` on a goal means *nobody judged it* - not
// "failed".
// ============================================================

export type AppraisalCycleStatus = "Draft" | "Open" | "Closed";
export type AppraisalStatus = "Draft" | "Submitted" | "Reviewed" | "Finalized";

export interface AppraisalCycleRow {
    id: string;
    name: string;
    startDate: string;
    endDate: string;
    status: AppraisalCycleStatus;
    note: string | null;
    appraisals: number;
    submitted: number;
    finalized: number;
}

export interface AppraisalGoalRow {
    id: string;
    title: string;
    target: string | null;
    /** `null` until a reviewer judges it. */
    achieved: boolean | null;
    weight: number;
}

export interface AppraisalRow {
    id: string;
    cycleId: string;
    cycleName: string;
    employeeId: string;
    employeeCode: string;
    name: string;
    department: string | null;
    status: AppraisalStatus;
    statusLabel: string;
    selfRating: number | null;
    selfNote: string | null;
    reviewerRating: number | null;
    reviewerNote: string | null;
    reviewerName: string | null;
    submittedAt: string | null;
    reviewedAt: string | null;
    finalizedAt: string | null;
    goals: AppraisalGoalRow[];
    goalsTotal: number;
    goalsJudged: number;
    goalsAchieved: number;
}

export interface AppraisalQueue {
    cycle: AppraisalCycleRow;
    rows: AppraisalRow[];
    total: number;
    /** The caller's own appraisal in this season, when they have one. */
    mine: AppraisalRow | null;
}

export interface AppraisalGoalInput {
    title: string;
    target?: string | null;
    weight?: number;
}

export interface SelfAssessmentInput {
    selfRating: number;
    selfNote?: string | null;
    /** Replaces the goal list: a goal removed from the form is no longer claimed. */
    goals: AppraisalGoalInput[];
}

export interface ReviewInput {
    reviewerRating: number;
    reviewerNote?: string | null;
}

export interface AppraisalCycleInput {
    name: string;
    startDate: string;
    endDate: string;
    note?: string | null;
}

export interface TrainingRow {
    id: string;
    employeeId: string;
    title: string;
    provider: string | null;
    onDate: string;
    hours: number;
    note: string | null;
}

export interface TrainingInput {
    title: string;
    provider?: string | null;
    onDate: string;
    hours?: number;
    note?: string | null;
}

// ============================================================
// Phase 9 — the three staff aggregates (`GET /reports/staff-summary`)
//
// Derived, never stored: the register's window, the timetable's load and the
// current season, read on every request. The payload carries the window, the
// denominator's source and the scope, so no number is quietly about fewer
// people or a different month than the reader assumes.
// ============================================================

export interface StaffAttendanceSummary {
    windowStart: string;
    windowEnd: string;
    days: number;
    present: number;
    halfDay: number;
    absent: number;
    marked: number;
    /** A share of the days somebody marked - not of the calendar. */
    percent: number;
}

export interface StaffWorkloadSummary {
    teachers: number;
    periods: number;
    average: number;
    maximum: number;
    under: number;
    normal: number;
    over: number;
    /** `rule` when the school set a capacity, `timetable` when the heaviest load is it. */
    capacitySource: string;
    capacity: number;
}

export interface StaffAppraisalSummary {
    cycle: string | null;
    cycleStatus: string | null;
    total: number;
    submitted: number;
    reviewed: number;
    finalized: number;
    averageReviewerRating: number | null;
    goalsJudged: number;
    goalsAchieved: number;
}

export interface StaffSummaryReport {
    attendance: StaffAttendanceSummary;
    workload: StaffWorkloadSummary;
    appraisals: StaffAppraisalSummary;
    /** `school` for the office, `scoped` when the caller only sees some people. */
    scope: string;
    people: number;
}
