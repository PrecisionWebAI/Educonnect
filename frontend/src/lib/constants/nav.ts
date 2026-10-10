import type { IconName } from "@/components/ui/Icon";

// ============================================================
// Sidebar navigation — one entry per blueprinted module page.
// Next.js routes: /dashboard/<module>. Icons are SVG names
// (see components/ui/Icon.tsx) — no emoji anywhere.
// ============================================================

export interface NavItem {
    to: string;
    label: string;
    icon: IconName;
    permissions?: string[];
    badge?: number;
}

export interface NavGroup {
    title: string;
    items: NavItem[];
}

export const NAV_GROUPS: NavGroup[] = [
    {
        title: "Main",
        items: [
            { to: "/dashboard", label: "Dashboard", icon: "dashboard", permissions: ["dashboard.read"] },

            { to: "/dashboard/chat", label: "Chat", icon: "chat", permissions: ["messages.read"] },
        ],
    },
    {
        title: "Academic",
        items: [
            { to: "/dashboard/students", label: "Students", icon: "students", permissions: ["students.read"] },
            { to: "/dashboard/attendance", label: "Attendance", icon: "attendance", permissions: ["attendance.read"] },
            { to: "/dashboard/academics", label: "Academics & Marks", icon: "book", permissions: ["dashboard.read"] },
            { to: "/dashboard/exams", label: "Exams & AI Papers", icon: "edit", permissions: ["exams.read"] },
            { to: "/dashboard/homework", label: "Homework & Diary", icon: "book", permissions: ["homework.read", "diary.read"] },
            { to: "/dashboard/classroom", label: "Classroom", icon: "school", permissions: ["classes.read"] },
            { to: "/dashboard/timetable", label: "Timetable", icon: "calendar", permissions: ["timetable.read"] },
        ],
    },
    {
        title: "People & Finance",
        items: [
            { to: "/dashboard/teachers", label: "Teachers & Staff", icon: "guardian", permissions: ["teachers.read"] },
            { to: "/dashboard/payroll", label: "Payroll / Payslip", icon: "money", permissions: ["payroll.read", "payroll.view_payslip"] },
            { to: "/dashboard/finance", label: "Finance (Fees)", icon: "wallet", permissions: ["fees.read"] },
        ],
    },
    {
        title: "Services",
        items: [
            { to: "/dashboard/library", label: "Library", icon: "book", permissions: ["library.read"] },
            { to: "/dashboard/transport", label: "Transport", icon: "bus", permissions: ["transport.read"] },
            { to: "/dashboard/meetings", label: "Meetings", icon: "groups", permissions: ["ptm.read"] },
            { to: "/dashboard/tickets", label: "Tickets & Support", icon: "warning", permissions: ["dashboard.read"] },
            { to: "/dashboard/leave", label: "Leave & Applications", icon: "calendar", permissions: ["leave.read"] },
        ],
    },
    {
        title: "Operations",
        items: [
            {
                to: "/dashboard/operations/admission",
                label: "Admission",
                icon: "students",
                permissions: ["students.read", "students.create"],
            },
            {
                to: "/dashboard/operations/staff-hiring",
                label: "Staff Hiring",
                icon: "guardian",
                permissions: ["teachers.read", "teachers.create"],
            },
            {
                to: "/dashboard/operations/fees-structure",
                label: "Fees Structure",
                icon: "wallet",
                permissions: ["fees.read", "fees.manage_structure"],
            },
            {
                to: "/dashboard/operations/salary",
                label: "Staff Salary",
                icon: "money",
                permissions: ["payroll.read", "payroll.manage"],
            },
        ],
    },
    {
        title: "Insights & Admin",
        items: [
            { to: "/dashboard/reports", label: "Reports & Analytics", icon: "trending", permissions: ["reports.read"] },
            { to: "/dashboard/settings", label: "Settings", icon: "more", permissions: ["settings.read", "profile.read"] },
        ],
    },
];
