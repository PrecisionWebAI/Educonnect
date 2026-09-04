import { api } from "@/lib/api/client";
import type {
    BookIssue,
    Bus,
    ChatConversation,
    ChatFile,
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
    SecurityLog,
    SettingUser,
    StaffLeaveRow,
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

export async function getLessonDetail(): Promise<LessonDetail> {
    return api.get<LessonDetail>("/classroom/lesson-detail");
}

export async function getNotifications(): Promise<NotificationItem[]> {
    return api.get<NotificationItem[]>("/notifications");
}

export async function markAllNotificationsRead(): Promise<void> {
    await api.post("/notifications/mark-read");
}

export async function getChatFiles(): Promise<ChatFile[]> {
    return api.get<ChatFile[]>("/chat/files");
}

export async function getChatConversations(): Promise<ChatConversation[]> {
    return [
        {
            id: 1,
            name: "Aarav Mehta",
            group: false,
            lastMessage: "Can you share the Physics notes?",
            time: "10m",
            unread: 2,
            online: true,
        },
        {
            id: 2,
            name: "Class 10-A",
            group: true,
            lastMessage: "P. Menon: Homework due tomorrow",
            time: "1h",
            unread: 5,
        },
        {
            id: 3,
            name: "Diya Sharma",
            group: false,
            lastMessage: "Thanks for the schedule!",
            time: "2h",
            unread: 0,
            online: false,
        },
    ];
}
