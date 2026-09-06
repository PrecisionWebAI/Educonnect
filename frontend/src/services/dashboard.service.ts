import { api } from "@/lib/api/client";
import type {
    AccountantSummary,
    ApprovalItem,
    ChildSummary,
    ClassAttendanceStat,
    DashboardData,
    HomeworkStatusItem,
    MeetingReminderItem,
    OperationsBoard,
    PaperDraftItem,
    PaperReviewItem,
    QbHealthItem,
    StudentPortalData,
    SubjectLeaveItem,
    SubjectPerf,
    TodayClassItem,
} from "@/types";

export async function getDashboard(): Promise<DashboardData> {
    return api.get<DashboardData>("/dashboard");
}

export async function getApprovals(): Promise<ApprovalItem[]> {
    return api.get<ApprovalItem[]>("/dashboard/approvals");
}

export async function getOperationsBoard(): Promise<OperationsBoard> {
    return api.get<OperationsBoard>("/dashboard/operations");
}

export async function getClassAttendance(): Promise<ClassAttendanceStat[]> {
    return api.get<ClassAttendanceStat[]>("/dashboard/class-attendance");
}

export async function getSubjectPerf(): Promise<SubjectPerf[]> {
    return api.get<SubjectPerf[]>("/dashboard/subject-perf");
}

export async function getQbHealth(): Promise<QbHealthItem[]> {
    return api.get<QbHealthItem[]>("/dashboard/qb-health");
}

export async function getTodayClasses(): Promise<TodayClassItem[]> {
    return api.get<TodayClassItem[]>("/dashboard/today-classes");
}

export async function getHomeworkStatus(): Promise<HomeworkStatusItem[]> {
    return api.get<HomeworkStatusItem[]>("/dashboard/homework-status");
}

export async function getSubjectLeaves(): Promise<SubjectLeaveItem[]> {
    return api.get<SubjectLeaveItem[]>("/dashboard/subject-leaves");
}

export async function getMeetingReminders(): Promise<MeetingReminderItem[]> {
    return api.get<MeetingReminderItem[]>("/dashboard/meeting-reminders");
}

export async function getPaperDrafts(): Promise<PaperDraftItem[]> {
    return api.get<PaperDraftItem[]>("/dashboard/paper-drafts");
}

export async function getStudentPortal(): Promise<StudentPortalData> {
    return api.get<StudentPortalData>("/dashboard/student-portal");
}

export async function getParentData(): Promise<ChildSummary[]> {
    return api.get<ChildSummary[]>("/dashboard/parent-data");
}

export async function getAccountantSummary(): Promise<AccountantSummary> {
    return api.get<AccountantSummary>("/dashboard/accountant-summary");
}

export async function getPaperReviews(): Promise<PaperReviewItem[]> {
    return api.get<PaperReviewItem[]>("/dashboard/paper-reviews");
}
