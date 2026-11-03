import { api } from "@/lib/api/client";
import type {
    BookIssue,
    Bus,
    ClassGroup,
    ClassroomItem,
    CopilotAutomation,
    CopilotSuggestion,
    DataQualityRow,
    EducationReportRow,
    GatewayStatus,
    LeaveApplicationItem,
    LessonDetail,
    LibraryBook,
    MeetingItem,
    NotificationItem,
    PaletteCommand,
    ReportCard,
    SchoolInfo,
    SectionDetail,
    SecurityLog,
    SettingUser,
    StaffLeaveRow,
    TeacherOption,
    TicketItem,
    TransportRoute,
} from "@/types";

export async function getLeaveApplications(): Promise<LeaveApplicationItem[]> {
    return api.get<LeaveApplicationItem[]>("/leave/applications");
}

export async function getStaffLeaveRequests(): Promise<StaffLeaveRow[]> {
    return api.get<StaffLeaveRow[]>("/leave/staff-requests");
}

export async function getMeetings(): Promise<MeetingItem[]> {
    return api.get<MeetingItem[]>("/meetings");
}

export async function getTickets(): Promise<TicketItem[]> {
    return api.get<TicketItem[]>("/tickets");
}

export async function getReportCards(): Promise<ReportCard[]> {
    return api.get<ReportCard[]>("/reports/cards");
}

export async function getDataQuality(): Promise<DataQualityRow[]> {
    return api.get<DataQualityRow[]>("/reports/data-quality");
}

export async function getEducationReports(): Promise<EducationReportRow[]> {
    return api.get<EducationReportRow[]>("/reports/education");
}

export async function getSettingUsers(): Promise<SettingUser[]> {
    return api.get<SettingUser[]>("/settings/users");
}

export async function getSchoolInfo(): Promise<SchoolInfo[]> {
    return api.get<SchoolInfo[]>("/settings/school-info");
}

export async function getSecurityLogs(): Promise<SecurityLog[]> {
    return api.get<SecurityLog[]>("/settings/security-logs");
}

export async function getGateways(): Promise<GatewayStatus[]> {
    return api.get<GatewayStatus[]>("/settings/gateways");
}

export async function getAutomations(): Promise<CopilotAutomation[]> {
    return api.get<CopilotAutomation[]>("/copilot/automations");
}

export async function getCopilotSuggestions(): Promise<CopilotSuggestion[]> {
    return api.get<CopilotSuggestion[]>("/copilot/suggestions");
}

export async function getPaletteCommands(): Promise<PaletteCommand[]> {
    return api.get<PaletteCommand[]>("/copilot/commands");
}

export async function getLibraryBooks(): Promise<LibraryBook[]> {
    return api.get<LibraryBook[]>("/library/books");
}

export async function getBookIssues(): Promise<BookIssue[]> {
    return api.get<BookIssue[]>("/library/issues");
}

export async function getTransportRoutes(): Promise<TransportRoute[]> {
    return api.get<TransportRoute[]>("/transport/routes");
}

export async function getBuses(): Promise<Bus[]> {
    return api.get<Bus[]>("/transport/buses");
}

export async function getClassrooms(): Promise<ClassroomItem[]> {
    return api.get<ClassroomItem[]>("/classroom/classes");
}

/** The school-wide class grid: a group per class, a card per class-section. */
export async function getClassroomOverview(): Promise<ClassGroup[]> {
    return api.get<ClassGroup[]>("/classroom/overview");
}

/** One class-section in full: students, attendance, timetable, homework, diary, marks. */
export async function getSectionDetail(sectionId: string): Promise<SectionDetail> {
    return api.get<SectionDetail>(`/classroom/sections/${sectionId}`);
}

/** Every teacher this school can put in front of a class-section. */
export async function getTeacherOptions(): Promise<TeacherOption[]> {
    return api.get<TeacherOption[]>("/classroom/teachers");
}

/** Set the section's class teacher. Pass `null` to leave the section unassigned. */
export async function setClassTeacher(
    sectionId: string,
    teacherId: string | null,
): Promise<void> {
    await api.put(`/classroom/sections/${sectionId}/class-teacher`, { teacherId });
}

/** Set who takes one subject in one section. Pass `null` to clear it. */
export async function setSubjectTeacher(
    sectionId: string,
    subjectId: string,
    teacherId: string | null,
): Promise<void> {
    await api.put(`/classroom/sections/${sectionId}/subjects/${subjectId}/teacher`, {
        teacherId,
    });
}

export async function getLessonDetail(): Promise<LessonDetail> {
    return api.get<LessonDetail>("/classroom/lesson-detail");
}

export async function getNotifications(): Promise<NotificationItem[]> {
    return api.get<NotificationItem[]>("/notifications");
}

export async function markAllNotificationsRead(): Promise<void> {
    await api.post("/notifications/mark-read");
}
export { getChatFiles, getChatConversations } from "./chat.service";
