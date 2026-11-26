// ==========================================================
// EduConnect Frontend â€” shared domain & app types
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
    /** That school's name â€” what the header shows in place of the old search box. */
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
    /** The session they were admitted in (earliest enrollment). */
    admissionYear?: string | null;
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
    /** The student's own login (`app_user.id`) - how "me" is recognised, never by name. */
    user_id?: string | null;
    /** The class-section (`classroom.id`) this year's enrollment sits in. */
    section_id?: string | null;
    /** The class the child first enrolled in. */
    admissionClass?: string | null;
    /** How this year's enrollment came to be. */
    promotionStatus?: "NEW_ADMISSION" | "PROMOTED" | "RETAINED" | "COMPLETED" | null;
    /** What happened to the child after this year; empty while Pending. */
    nextYearOutcome?: string | null;
    /** "Class 6-A" when the child was moved one class down this year. */
    movedFrom?: string | null;
    /** Attendance over the current academic year; `null` when nothing was marked. */
    attendancePercent?: number | null;
}

/** A student the promotion request could not move, and why. */
export interface PromotionSkipped {
    studentId: string;
    name: string;
    reason: string;
}

export interface PromotionResult {
    done: number;
    skipped: PromotionSkipped[];
}

/** What de-promoting would permanently delete. */
export interface DepromotePreview {
    students: {
        studentId: string;
        name: string;
        attendance: number;
        fees: number;
        marks: number;
    }[];
    attendance: number;
    fees: number;
    marks: number;
    skipped: PromotionSkipped[];
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
     * because the same person signs in as something else (a parent, a member of staff) â€”
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

// ---- The register the Attendance tab draws (Phase 2 API, Phase 4 screen) ----
//
// The wire is snake_case; `services/attendance.service.ts` converts it with
// `toCamel`, so these types are camelCase like every other screen's.

/** What a child's day says. `unmarked` is a state, not a missing row. */
export type RegisterStatus = "present" | "absent" | "late" | "half_day" | "leave" | "unmarked";

export interface RegisterRow {
    studentId: string;
    /** The saved row, when there is one (`null` for an unmarked or leave-only day). */
    recordId: string | null;
    name: string;
    admissionNo: string | null;
    status: RegisterStatus;
    /** False only for `unmarked`: "absent" and "nobody said" are different things. */
    marked: boolean;
    remarks: string | null;
    /** The approved leave this day is derived from, when there is one. */
    leaveRequestId: string | null;
    /**
     * False for a child who has left the school. They stay on the sheet - their history is
     * real - but the chips are greyed out, because nobody marks a child who is not there.
     */
    active?: boolean;
}

export interface RegisterCounts {
    present: number;
    absent: number;
    late: number;
    halfDay: number;
    leave: number;
    unmarked: number;
}

export interface SectionRegister {
    sectionId: string;
    date: string;
    classroomSubjectId: string | null;
    /** "Sunday" or the holiday's name; the day is readable but cannot be saved. */
    closedReason: string | null;
    /** `weeklyOff` / `weekOff` / `holiday` - the colour the calendar paints the day. */
    closedKind: string | null;
    counts: RegisterCounts;
    /** `null` when nothing is marked - "no data", never 0%. */
    percent: number | null;
    rows: RegisterRow[];
}

export interface StudentAttendanceTotal {
    studentId: string;
    name: string;
    admissionNo: string | null;
    present: number;
    absent: number;
    late: number;
    halfDay: number;
    leave: number;
    /** Days with a register row (leave days are not marks). */
    marked: number;
    /** Present + late - the figure the table prints as "Present". */
    presentTotal: number;
    /** Present + late **in the month the calendar shows** - the row's `Monthly attendance`. */
    monthPresentTotal: number;
    /** Absent days in that month. */
    monthAbsent: number;
    /** Open days of that month up to its cutoff - the `/12` in `Monthly attendance 5/12`. */
    monthOpenDays: number;
    /** Registers actually taken that month - the tooltip's "9 of 12 registers taken". */
    monthSaved: number;
    /** Open days this child's percentage divides by. */
    openDays: number;
    percent: number | null;
    /** The school's own `attendance.absence_threshold`. */
    threshold: number;
    belowThreshold: boolean;
}

export interface SectionSummary {
    sectionId: string;
    fromDate: string;
    toDate: string;
    /** Open days in the range (Sundays and holidays removed). */
    workingDays: number;
    threshold: number;
    /** The month the rows' figures describe, and where its cutoff fell. */
    monthFromDate?: string | null;
    monthToDate?: string | null;
    rows: StudentAttendanceTotal[];
}

export interface AttendanceTrendPoint {
    date: string;
    /** The x-axis word the server chose: "Mon", "3rd wk Nov", "Nov". */
    label?: string;
    present: number;
    marked: number;
    percent: number | null;
    /** The last day of the span (a day has none - it is `date`). */
    endDate?: string | null;
}

export interface SectionTrend {
    sectionId: string;
    /** `day`, `week` or `month` - the scale of the bars. */
    range: string;
    days: number;
    /** Oldest first; Sundays and holidays are absent, not zero. */
    points: AttendanceTrendPoint[];
}

export interface AttendanceAttentionRow {
    studentId: string;
    name: string;
    admissionNo: string | null;
    percent: number | null;
    consecutiveAbsences: number;
    reason: string;
}

/** A day the register cannot be taken - what the date picker greys out. */
export interface ClosedDay {
    date: string;
    reason: string;
    /** `weeklyOff` / `weekOff` / `holiday` - the colour, decided by the server. */
    kind?: string | null;
}

/** One day of the register's month calendar: closed (and why), and saved or not. */
export interface SectionCalendarDay {
    date: string;
    /** `weeklyOff` / `weekOff` / `holiday`; `null` on a day a register may be taken. */
    closedKind: string | null;
    closedReason: string | null;
    /** A register was saved on this day for this class-section - the calendar's dot. */
    saved: boolean;
}

/** The month the daily register's date control draws. */
export interface SectionCalendar {
    sectionId: string;
    fromDate: string;
    toDate: string;
    days: SectionCalendarDay[];
}

// ---- The Course tab (Phase 5 API, Phase 6 screen) ---------------------------

/** One person who has taught a subject in this class-section. */
export interface CourseTeacher {
    employeeId: string;
    name: string;
    effectiveFrom: string | null;
    /** `null` while they still hold the subject. */
    effectiveTo: string | null;
    current: boolean;
    /** Chapters of this subject **they** completed in this section. */
    completed: number;
}

/** The words the Course tab shows for a chapter. */
export type ChapterStatus = "Pending" | "In progress" | "Completed" | "Skipped";

/** The chapter list's own lifecycle: the teacher drafts, the principal approves. */
export type ChapterPlanStatus = "Draft" | "Submitted" | "Approved";

/** Another section that already teaches this subject and has a plan to copy. */
export interface CourseChapter {
    chapterId: string;
    sequence: number;
    name: string;
    plannedDate: string | null;
    status: ChapterStatus;
    completedOn: string | null;
    completedBy: string | null;
    completedByEmployeeId: string | null;
    /** Finished on or before the planned date (null when there is no plan). */
    ahead: boolean | null;
    /** The planned date has passed and it is not finished. */
    behind: boolean;
    /** May the caller tick it (subject teacher, or the office)? */
    canTick: boolean;
    /** May the caller rename, move or delete it (the office only)? */
    canEdit: boolean;
    /** Saved by the teacher, waiting for the principal. */
    proposedStatus: "Completed" | "Skipped" | "Pending" | null;
}

/** The six official fields of a week's lesson plan. */
export interface LessonPlanContent {
    topics: string;
    learningObjectives: string;
    activities: string;
    homework: string;
    resources: string;
    assessment: string;
}

/** One week tab: calendar slot, latest plan, and the last approved snapshot. */
export interface LessonPlanWeek extends LessonPlanContent {
    /** The submitted row; `null` until the week is submitted. */
    planId: string | null;
    weekNo: number;
    startDate: string;
    endDate: string;
    /** The real open days in the range (Sunday/holiday removed). */
    teachingDays: string[];
    /** `null` means "not submitted" - the week has no row yet. */
    status: "Submitted" | "Approved" | "Rejected" | null;
    version: number;
    approvedVersion: number | null;
    /** Send this back on submit; `0` before the first submit. */
    expectedVersion: number;
    approved: LessonPlanContent | null;
    rejectionReason: string | null;
    submittedAt: string | null;
    submittedBy: string | null;
    canEdit: boolean;
    /** Approved week: a change needs the explicit "Request change" intent. */
    canRequestChange: boolean;
}

/** One submitted week in the approver's queue, with the full six fields. */
export interface ReviewRow extends LessonPlanContent {
    planId: string;
    classroomSubjectId: string;
    sectionId: string;
    label: string;
    subject: string;
    weekNo: number;
    year: number;
    month: number;
    startDate: string;
    endDate: string;
    status: "Submitted" | "Approved" | "Rejected";
    version: number;
    expectedVersion: number;
    submittedAt: string | null;
    submittedBy: string | null;
    rejectionReason: string | null;
}

export interface ReviewDecision {
    planId: string;
    status: string;
    version: number;
    approvedVersion: number | null;
    rejectionReason: string | null;
    reviewedAt: string | null;
}

export interface BulkReviewItem {
    planId: string;
    status: "approved" | "skipped";
    detail: string | null;
}

export interface BulkReviewResult {
    approved: string[];
    skipped: BulkReviewItem[];
}

/** The Course badge's three numbers. */
export interface CourseSummary {
    subjectCount: number;
    pendingApprovals: number;
    completionPercent: number | null;
}

/** One row in Teachers > Course. */
export interface CourseTeacherRow {
    employeeId: string;
    name: string;
    employeeCode: string | null;
    department: string | null;
    subjectsCount: number;
    sectionsCount: number;
    pendingApprovals: number;
    behindSubjects: number;
    completionPercent: number | null;
}

export interface TeacherWeekRow {
    weekNo: number;
    startDate: string;
    endDate: string;
    planId: string | null;
    status: "Submitted" | "Approved" | "Rejected" | null;
    version: number;
    approvedVersion: number | null;
    rejectionReason: string | null;
}

export interface TeacherChapterRow {
    chapterId: string;
    sequence: number;
    name: string;
    plannedDate: string | null;
    status: "Pending" | "In progress" | "Completed";
    completedOn: string | null;
    completedBy: string | null;
}

export interface TeacherAssignment {
    classroomSubjectId: string;
    sectionId: string;
    label: string;
    subject: string;
    current: boolean;
    effectiveFrom: string | null;
    effectiveTo: string | null;
    done: number;
    total: number;
    percent: number | null;
    weeks: TeacherWeekRow[];
    chapters: TeacherChapterRow[];
}

export interface TeacherCourseDetail {
    employeeId: string;
    name: string;
    employeeCode: string | null;
    department: string | null;
    assignments: TeacherAssignment[];
}

/** This calendar month's weekly plans for one section subject. */
export interface LessonPlanSummary {
    year: number;
    month: number;
    /** Every week that has a row (its latest version). */
    submitted: number;
    approved: number;
    pending: number;
    /** Rejected weeks waiting for a corrected resubmission. */
    rejected: number;
}

export interface CourseSubject {
    /** The section's row; `null` only for a legacy teacher row before the Phase 1 backfill. */
    classroomSubjectId: string | null;
    /** This section's own subject name. */
    name: string;
    code: string | null;
    /** Active / Archived - the section's row, not a school-wide master list. */
    status: "Active" | "Archived";
    currentTeacher: string | null;
    currentTeacherId: string | null;
    teachers: CourseTeacher[];
    done: number;
    total: number;
    /** `null` when there is no plan - "no plan" is not 0%. */
    percent: number | null;
    nextChapter: string | null;
    behind: number;
    planned: boolean;
    chapters: CourseChapter[];
    /** This month's plan counts; `null` when no week has been submitted. */
    lessonPlan: LessonPlanSummary | null;
    /** What the server says this caller may do to the row. */
    canManage: boolean;
    canAssignTeacher: boolean;
    canArchive: boolean;
    canRestore: boolean;
    canDelete: boolean;
    chapterPlanStatus: ChapterPlanStatus;
    chapterPlanRejectReason: string | null;
    /** An approved list was changed; the changes wait for the principal. */
    chapterPlanReapproval: boolean;
    /** The count last approved; shown while edits to it wait for approval. */
    approvedTotal?: number | null;
    /** Chapters skipped (approved); they do not count as done. */
    skipped: number;
    /** Chapters whose saved change waits for the principal. */
    pendingApproval: number;
    canEditPlan: boolean;
    canSubmitPlan: boolean;
    canSaveProgress: boolean;
    canApprove: boolean;
}

export interface SectionCourse {
    sectionId: string;
    label: string;
    academicYear: string | null;
    /** Completed chapters out of all planned chapters; `null` when no subject has a plan. */
    completionPercent: number | null;
    /** How many subjects that average is made of (subjects with at least one chapter). */
    completionSubjects: number;
    /** Active subjects in this section - "No Subjects Yet" is this being zero. */
    subjectsCount: number;
    subjects: CourseSubject[];
}

/** What assigning a teacher answers with - including the workload warning, if any. */
export interface CourseTeacherAssignment {
    classroomSubjectId: string;
    teacherId: string;
    teacher: string;
    effectiveFrom: string;
    /** The assignment saved; this sentence asks the office to review the timetable. */
    warning: string | null;
}

/** What Add Subject / rename / archive / restore answers with. */
export interface CourseSubjectRow {
    classroomSubjectId: string;
    name: string;
    code: string | null;
    status: "Active" | "Archived";
}

// ---- Exams plan (Phase 7's backend: `exam`, `exam_paper`, `marks`) ----------
//
// A **paper** is one sitting of one **section subject** (Class 9-A's Mathematics),
// and it is the only place a maximum lives (`exam_paper.max_marks`). Sections that
// sit the same question paper share a **group**: it links papers, never subjects.
// A mark is a score out of that maximum, or an absence - not a zero.

/**
 * A `numeric(6,2)` as the API writes it.
 *
 * Pydantic serialises `Decimal` to JSON as a **string** (`"72.50"`), so every
 * figure here may be text; `amount()` in `lib/exams/view` turns it into a number.
 */
export type DecimalText = string | number;

export interface ExamPaperPlan {
    id: string;
    examId: string;
    /** The section's own subject; the paper hangs from it. */
    classroomSubjectId: string;
    /** The section that sits the paper. */
    classroomId: string;
    classId: string;
    /** `Class 9-A`. */
    section: string;
    /** The section subject's own name. */
    subject: string;
    /** The shared paper's title when it has one; else the subject's name. */
    title: string;
    paperGroupId: string | null;
    /** True once marks exist or a paper is published: the shared paper is frozen. */
    groupLocked: boolean;
    examDate: string | null;
    /** `"09:00:00"` - what the backend stores. */
    startTime: string | null;
    endTime: string | null;
    maxMarks: DecimalText;
    passingMarks: DecimalText | null;
    room: string | null;
    note: string | null;
    /** Set the moment this sitting's marks are published. */
    publishedAt: string | null;
    chapterIds: string[];
    /** The chapter names, for the syllabus line. */
    chapters: string[];
    marksEntered: number;
    /** The teacher who takes it (the assigned one unless somebody else was picked). */
    takenByEmployeeId: string | null;
    takenByName: string | null;
    assignedTeacherId: string | null;
    assignedTeacherName: string | null;
    /** True when someone other than the assigned teacher takes it (the Temporary card). */
    isTemporary: boolean;
    /** This paper's own pass line: `marks` or `grade`. */
    passMode: "marks" | "grade" | null;
    /** The pass line as a percentage of the total, whichever way it was stated. */
    passPercent: DecimalText | null;
    passingGrade: string | null;
    /** This paper's own copy of the grading ladder, highest first (empty on older papers). */
    gradingScale: { minPercent: DecimalText; grade: string }[];
    /** True once the subject teacher has written a syllabus. */
    hasSyllabus: boolean;
    /** How this paper's Grade column works: `auto` (ladder), `na` or `manual`. */
    gradeMode: "auto" | "na" | "manual";
    /** Who writes this subject's syllabus (the assigned teacher unless another is picked). */
    syllabusByEmployeeId: string | null;
    syllabusByName: string | null;
    syllabusIsTemporary: boolean;
    /** True when this caller may write this subject's syllabus (School Exam papers). */
    canSyllabus: boolean;
    /** True when this caller may change the paper (the office, or its subject teacher). */
    canEdit: boolean;
    /** True when the paper is in a shared group and this caller may give it its own. */
    canDetach: boolean;
}

/** A shared question paper: the title and chapters its sections have in common. */
export interface ExamPaperGroup {
    id: string;
    examId: string;
    displayTitle: string | null;
    chapters: string[];
    paperIds: string[];
    locked: boolean;
}

/** A section left out of a named subject because it has no such subject yet. */
export interface SkippedSection {
    classroomId: string;
    section: string;
    subject: string;
}

export interface ExamPlan {
    id: string;
    name: string;
    term: string | null;
    examType: string | null;
    /** `class` (one class sits it) or `school` (every class does). */
    scope: "class" | "school";
    /** `draft` | `scheduled` | `done` | `marks_entry` | `published`. */
    status: string;
    classId: string | null;
    classroomId: string | null;
    academicYearId: string | null;
    startDate: string | null;
    endDate: string | null;
    note: string | null;
    /** What guardians and students read with the schedule. */
    familyNote: string | null;
    datesheetPublishedAt: string | null;
    /** Set when the date sheet was archived (hidden from the list, never deleted). */
    archivedAt: string | null;
    /** True when this caller may set and publish the date sheet (School Exams). */
    canManage: boolean;
    publishedAt: string | null;
    papers: ExamPaperPlan[];
    groups: ExamPaperGroup[];
    /** Sections skipped when the exam was saved (empty on a plain read). */
    skipped: SkippedSection[];
}

/** One child's line on a paper's marks sheet. */
export interface PaperMarkRow {
    studentId: string;
    name: string;
    admissionNumber: string | null;
    section: string | null;
    /** `null` when unmarked **or** absent - `absent` says which. */
    marksObtained: DecimalText | null;
    absent: boolean;
    grade: string | null;
    /** `obtained / total * 100`; `null` for an absent or unmarked child. */
    percentage: DecimalText | null;
    /** Pass/fail by this paper's own pass line; `null` for an absent or unmarked child. */
    passed: boolean | null;
    /** True when this score was corrected after the paper was published. */
    changedAfterPublish: boolean;
}

/** One correction made to a published mark: who, when, from what to what, why. */
export interface MarkAudit {
    studentId: string;
    studentName: string;
    oldValue: DecimalText | null;
    newValue: DecimalText | null;
    oldAbsent: boolean;
    newAbsent: boolean;
    changedBy: string | null;
    changedAt: string;
    reason: string | null;
}

export interface MarksSaved {
    paperId: string;
    examId: string;
    examStatus: string;
    written: number;
    absent: number;
    rows: PaperMarkRow[];
}

export interface ExamResultMark {
    paperId: string;
    classroomSubjectId: string;
    subject: string;
    maxMarks: DecimalText;
    obtained: DecimalText | null;
    absent: boolean;
    grade: string | null;
    passed: boolean | null;
}

export interface ExamResultRow {
    studentId: string;
    name: string;
    admissionNumber: string | null;
    className: string | null;
    section: string | null;
    marks: ExamResultMark[];
    total: DecimalText;
    outOf: DecimalText;
    percent: DecimalText | null;
    grade: string | null;
    /** Competition rank (`1, 1, 3`); `null` when ranks are off or nothing was sat. */
    rank: number | null;
    absentCount: number;
    passedAll: boolean | null;
}

export interface ExamResultPaper {
    paperId: string;
    classroomSubjectId: string;
    classroomId: string;
    /** `Class 9-A` - a class exam has one column per section paper. */
    section: string;
    subject: string;
    examDate: string | null;
    maxMarks: DecimalText;
    passingMarks: DecimalText | null;
    published: boolean;
    average: DecimalText | null;
    highest: DecimalText | null;
    lowest: DecimalText | null;
    entered: number;
    absent: number;
}

/** What a new paper's pass line starts from (`GET /exams/marking-defaults`). */
export interface MarkingDefaults {
    totalMarks: string;
    /** 33% of the total, as the API writes a decimal (a string). */
    passMarks: string;
    /** The school's pass percentage (33 unless it set another). */
    passPercent: string;
    /** The grade that percentage earns on the ladder ("D"). */
    passingGrade: string | null;
    /** The school's ladder, highest first. */
    ladder: { minPercent: string; grade: string }[];
    /** `marks` / `grades` / `both`. */
    displayMode: "marks" | "grades" | "both";
}

/* ---------- the result overview (`GET /exams/results/overview`) ---------- */

/** What a section did on one test - the teacher's class view; never sent to a family. */
export interface OverviewStats {
    marked: number;
    absent: number;
    averageMarks: DecimalText | null;
    averagePercentage: DecimalText | null;
    highest: DecimalText | null;
    lowest: DecimalText | null;
    passed: number;
    failed: number;
}

/** One test (one paper) as a column of the result table. */
export interface OverviewTest {
    paperId: string;
    examId: string;
    examName: string;
    examType: string | null;
    subject: string;
    section: string;
    examDate: string | null;
    totalMarks: DecimalText;
    passMode: "marks" | "grade" | null;
    passPercent: DecimalText | null;
    passingMarks: DecimalText | null;
    passingGrade: string | null;
    /** False for a test still waiting to be published (staff only). */
    published: boolean;
    stats: OverviewStats | null;
}

/** One child's result on one test. */
export interface OverviewEntry {
    paperId: string;
    obtained: DecimalText | null;
    absent: boolean;
    percentage: DecimalText | null;
    grade: string | null;
    /** By that test's own pass line; `null` for an absent or unmarked child. */
    passed: boolean | null;
}

/** One subject across all the tests so far: `sum obtained / sum total`. */
export interface OverviewSubject {
    subject: string;
    obtained: DecimalText;
    total: DecimalText;
    percentage: DecimalText | null;
    grade: string | null;
    testsCounted: number;
    testsAbsent: number;
}

/** Every subject together. */
export interface OverviewTotal {
    obtained: DecimalText;
    total: DecimalText;
    percentage: DecimalText | null;
    grade: string | null;
    testsCounted: number;
    testsAbsent: number;
    testsPassed: number;
    testsFailed: number;
}

export interface OverviewStudent {
    studentId: string;
    name: string;
    admissionNumber: string | null;
    classroomId: string | null;
    section: string;
    entries: OverviewEntry[];
    subjects: OverviewSubject[];
    overall: OverviewTotal;
}

/** Class Test results **or** School Exam results for the year on screen - never mixed. */
export interface ResultOverview {
    kind: "class_test" | "school_exam";
    academicYearId: string | null;
    /** `section` (the class view, staff) or `family` (the caller's own children). */
    view: "section" | "family";
    classroomId: string | null;
    section: string;
    tests: OverviewTest[];
    students: OverviewStudent[];
    /** Tests that exist but are not published yet (staff only). */
    unpublished: number;
    displayMode: "marks" | "grades" | "both";
}

/** One subject's syllabus (`GET /exams/papers/{id}/syllabus`). */
export interface Syllabus {
    paperId: string;
    examId: string;
    subject: string;
    section: string;
    examName: string;
    syllabusText: string | null;
    /** True when this caller may change it. */
    canEdit: boolean;
}

export interface ExamResults {
    examId: string;
    name: string;
    status: string;
    /** `section` / `class` / `school` - what the rank is against (the school's setting). */
    rankDisplay: string;
    /** `percentage` / `grade` - which number the report card prints. */
    gradeScale: string;
    papers: ExamResultPaper[];
    rows: ExamResultRow[];
    /** Papers nobody has published yet - the principal's to-do list. */
    unpublished: string[];
    /** True when `rows` was narrowed to the caller's own children. */
    ownOnly: boolean;
}

export interface MarksRow {
    subject: string;
    /** The section subject's id, when the row came from a class-section's marks. */
    classroomSubjectId?: string;
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
    /** The teacher's employee id - counts and clashes match on this, not the name. */
    teacherId?: string | null;
    /** The class-section's id - "is this my class" is answered by id, not by label. */
    sectionId?: string | null;
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
    /** What the teacher is listed as able to teach ("english, maths"); "" when none. */
    subjectTags: string;
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
    /** One of the closed `doc_type` vocabulary (`aadhaar`, `degree`, â€¦). */
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
    /** What the teacher is listed as able to teach, as plain text. */
    subjectTags: string;
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

/** One ingredient of the overall score; `value` is null when there is no data. */
export interface StaffPerformanceComponent {
    key: "attendance" | "workload" | "course";
    label: string;
    value: number | null;
    weight: number;
    /** What the row shows in the tooltip ("96% of marked days", "no data"). */
    display: string;
}

export interface StaffPerformanceRow {
    id: string;
    staff: string;
    /** Which tab the row belongs to: staff have no timetable or plan (0.9). */
    kind: "teacher" | "staff";
    /** The session these numbers describe ("2026-27"). */
    session: string;
    sessionStart: string | null;
    sessionEnd: string | null;
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
    description: string;
    /** The class-section it was set for - the API's `section_id`. */
    sectionId: string;
    classroomSubjectId: string;
    teacherId: string;
    /** `YYYY-MM-DD`. */
    dueDate: string;
    subject: string;
    className: string;
    /** "Overdue" / "Today" / "Tomorrow" / "4 days" - the server's own word. */
    due: string;
    assignedBy: string;
    /** How many children have handed it in, out of `total` (the section's roll). */
    submitted: number;
    total: number;
}

export interface SubmissionItem {
    /** `null` when the child has not handed anything in yet - nothing to grade. */
    id: string | null;
    homeworkId: string;
    homeworkTitle: string;
    studentId: string;
    student: string;
    sectionId: string | null;
    subject: string | null;
    /** "Pending" | "Submitted" | "Graded" - lateness is `isLate`, its own fact. */
    status: "Pending" | "Submitted" | "Graded";
    /** `YYYY-MM-DD HH:MM`, or "" when it has not arrived. */
    submittedAt: string;
    isLate: boolean;
    marksAwarded: number | string | null;
    feedback: string | null;
    gradedAt: string | null;
}

export interface DiaryEntry {
    id: string;
    className: string;
    /** `YYYY-MM-DD`. */
    date: string;
    /** "Mon", "Tue" â€¦ */
    day: string;
    subject: string;
    /** "09:50 - 10:35", or "" for the day-level line. */
    period: string;
    topic: string;
}

/** One slot of the school's day (a lesson or a break). */
export interface BellSlot {
    periodNo: number;
    label: string;
    /** `HH:MM:SS` - what the API sends. */
    startTime: string;
    endTime: string;
    isBreak: boolean;
    /** True for the extra classes (E1, E2...). */
    extra?: boolean;
}

export interface ClassroomItem {
    id: string;
    title: string;
    subject: string;
    className: string;
    /** The class-section's id â€” what "Open Class" links to. */
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
    /** Weekly plans waiting for the principal in this section. */
    pendingApprovals: number;
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
    classroomSubjectId: string;
    name: string;
    code: string | null;
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
    /** The class's own id â€” the Timetable tab reads this section's week by it. */
    classroomId: string;
    /** The section letter on its own ("J") - what the Students / Attendance tabs scope by. */
    sectionName: string;
    stage: string;
    classTeacher: SectionClassTeacher | null;
    strength: number;
    boys: number;
    girls: number;
    attendancePercent: number | null;
    /** Open days `attendancePercent` divides by — the header prints "N open days this month". */
    attendanceOpenDays: number;
    /** Completed chapters out of all planned chapters; `null` when no subject has chapters. */
    syllabusPercent: number | null;
    /** How many subjects that average is made of. */
    subjectsTracked: number;
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
    /** Renamed from `user` (reserved word) â€” Phase 1. */
    actor_email: string;
    /** Renamed from `when` (reserved word) â€” Phase 1. */
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
    /** Renamed from `when` (reserved word) â€” Phase 1. */
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

/** Everything the admission form collects â€” mirrors the
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
    // FATHER â€” family detail. The **contact** belongs to the guardian: a phone or an
    // email typed here would be dropped by the server, which stores one contact per
    // person (see the GUARDIAN block below).
    fatherName: string;
    fatherOccupation: string;
    fatherAnnualIncome: string;
    // MOTHER â€” family detail, exactly like the father's.
    motherName: string;
    motherOccupation: string;
    motherAnnualIncome: string;
    // GUARDIAN â€” the family's contact, and the only block that carries one.
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
    /**
     * The session this admission is recorded in. Empty means the server uses the
     * current year; the form defaults it to that year and offers the next one for
     * advance admission.
     */
    targetAcademicYearId: string;
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
    /** The academic year the student was admitted in. */
    admissionYear?: string | null;
    createdOn: string;
    /** Present once the student has been separated (â†’ Inactive). */
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
 * The four tiles on the Admission screen â€” counted by the server, for this school.
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
    /** What this teacher can teach, as plain text ("English, Maths"). Informational. */
    subjectTags: string;
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

/** A hired staff member â€” the login + employee record the server created. */
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
    /** What this teacher can teach, as plain text. */
    subjectTags: string | null;
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
    /** The roles that were withdrawn â€” reactivating restores exactly these. */
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

/**
 * The student lifecycle routes answer with the same `LifecycleRead`
 * (`app/core/lifecycle.py`) - `kind` is `"student"`, the login is always kept and the
 * roles are the child's own. A named alias so the directory does not have to read
 * "Staff" to describe a child.
 */
export type StudentLifecycleResult = StaffLifecycleResult;

export type HiringStatus = "Resume" | "Shortlisted" | "Interview" | "Hired" | "Rejected";

export interface HiringCandidateRow {
    id: string;
    candidateNo: string | null;
    /** assigned on hire â€” shown in place of the candidate id */
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
    /** The subject applied for, as typed. Free text - not a link to anything. */
    subjectName: string | null;
    resumePath: string | null;
    /** scheduled interview date + time */
    interviewAt: string | null;
    interviewNote: string | null;
}

/** `feestructure.frequency` â€” monthly | term | yearly | one_time */
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
// Substitution (Phase 7) â€” the cover board
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
    classroomSubjectId: string;
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
// Phase 9 â€” the three staff aggregates (`GET /reports/staff-summary`)
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

export interface StaffPerformanceSummary {
    /** The session the numbers describe, from `academic_year` (or the calendar). */
    session: string;
    sessionStart: string | null;
    sessionEnd: string | null;
    people: number;
    /** How many of them had a score at all - `average` is null when nobody did. */
    scored: number;
    average: number | null;
    maximum: number | null;
    minimum: number | null;
    /** Each component averaged over the people who have it. */
    attendance: number | null;
    workload: number | null;
    course: number | null;
}

export interface StaffSummaryReport {
    attendance: StaffAttendanceSummary;
    workload: StaffWorkloadSummary;
    performance: StaffPerformanceSummary;
    /** `school` for the office, `scoped` when the caller only sees some people. */
    scope: string;
    people: number;
}

// ============================================================
// The academic year (`/settings/academic-years`)
//
// One row per school academic year, 1 April -> 31 March, derived from the name on
// the server - the browser never sends dates. `isCurrent` is the year the screens
// read; at most one row per school can hold it.
// ============================================================

export interface AcademicYear {
    id: string;
    /** "2026-27" - the words the school prints. */
    name: string;
    startDate: string;
    endDate: string;
    /** True for the academic year the screens treat as "now". */
    isCurrent: boolean;
}

/** One holiday the school declared: a single day, or a range that may cross a month. */
export interface SchoolHoliday {
    id: string;
    name: string;
    /** `public` / `school` / `vacation` / `other` (older rows may say festival/local). */
    kind: string;
    /** The words the list prints beside the type. */
    kindLabel: string;
    startDate: string;
    endDate: string;
    days: number;
    createdById: string | null;
    createdBy: string | null;
}

/** One date the school opened although a weekly off or a holiday closes it. */
export interface SchoolOpenDay {
    onDate: string;
    createdById: string | null;
    /** The name the calendar prints beside the row. */
    createdBy: string | null;
}

/** Everything the calendar draws for one window. */
export interface HolidayCalendar {
    fromDate: string;
    toDate: string;
    /** The holiday rows only - a weekly off closes a day but is not a holiday. */
    holidays: SchoolHoliday[];
    /** `date.weekday()`-style values (0 = Monday) the school closes every week. */
    weeklyOffDays: number[];
    /** The Saturday rules as `"5#1"` tokens (the 1st Saturday of every month). */
    nthOffDays: string[];
    /**
     * Every day in the window the calendar shades as a weekly off, already worked out by the
     * server (whole weekday, Saturday rule or dated extra off). The screen draws this list.
     */
    weeklyOffDates: string[];
    /** Days dated as an extra weekly off - grey on the calendar, absent from the list. */
    weekOffDates: string[];
    /** The extra weekly off rows themselves, so a mistaken date can be deleted. */
    weekOffs: SchoolHoliday[];
    /**
     * Single dates the school reopened although a rule (or a holiday) closes them - the
     * calendar's "just this one day" override. Clicking one offers "close it again".
     */
    openDays: SchoolOpenDay[];
    /** Every closed day of the window with its reason ("Sunday", "Diwali break"). */
    closedDays: ClosedDay[];
    /** Days in the window that already have a register - the calendar's dots. */
    markedDates: string[];
    /**
     * The page's three cards, computed by the server on **this** read (over the school's
     * current session). One payload, so a card can never disagree with the list under it.
     */
    summary?: HolidaySummary;
}

/** Everything the Calendar page's three cards print. */
export interface HolidaySummary {
    fromDate: string;
    toDate: string;
    /** "2026-27" when the window is the school's session; empty for a calendar year. */
    sessionLabel: string;
    /** Holiday rows in the window - a weekly off is a closure, not a holiday. */
    total: number;
    public: number;
    school: number;
    vacation: number;
    other: number;
    /** Days the vacations cover (a 10-day break is 10, not 1). */
    vacationDays: number;
}

/** One class-section that already holds a register on a day being closed. */
export interface ClosureImpactSection {
    sectionId: string;
    className: string;
    sectionName: string;
    /** Children with at least one mark that day. */
    students: number;
    /** Rows a confirmed delete would remove. */
    records: number;
}

/** One day being closed, and the class-sections whose register would go. */
export interface ClosureImpactDay {
    date: string;
    /** Why the day is (or would be) closed, in the calendar's own words. */
    reason: string;
    /** `weeklyOff` / `weekOff` / `holiday`. */
    kind: string;
    totalRecords: number;
    sections: ClosureImpactSection[];
}

/** The warning before a closure: what already exists on the days about to close. */
export interface ClosureImpact {
    fromDate: string;
    toDate: string;
    /** 0 = nothing to lose, so the closure can be saved at once. */
    totalRecords: number;
    days: ClosureImpactDay[];
}

/** What a confirmed delete removed. */
export interface ClosureDelete {
    deletedRecords: number;
    deletedAuditRows: number;
    days: string[];
}

/** What a saved holiday means for registers that already exist. */
export interface HolidayImpact {
    holiday: SchoolHoliday;
    /** A warning, never a delete: the rows stay, the days leave every count. */
    savedRegisterDays: number;
}

export interface WeeklyOffDays {
    days: number[];
    /** `"5#1"` = the 1st Saturday of every month, `"5#3"` the third. */
    nth: string[];
}

/** One day of a child's history: the date, the mark, and what it was recorded for. */
export interface StudentAttendanceEntry {
    id: string;
    date: string;
    status: string;
    subjectName: string | null;
    className: string | null;
    remarks: string | null;
}

/** One child on the late list: how many late days, and what share of the month. */
export interface LateStudentRow {
    studentId: string;
    name: string;
    late: number;
    percent: number;
}

/** The last complete month's late list, with what the card needs to explain it. */
export interface LateStudents {
    fromDate: string;
    toDate: string;
    /** "November 2026" - the words the card prints. */
    monthLabel: string;
    openDays: number;
    /** Days of that month with any register row - 0 means "no data". */
    markedDays: number;
    /** `attendance.late_share_percent` - the bar a child has to clear. */
    threshold: number;
    rows: LateStudentRow[];
}
