import type { Role } from "@/types";
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
    roles?: Role[];
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
            { to: "/dashboard", label: "Dashboard", icon: "dashboard" },
            { to: "/dashboard/notifications", label: "Notifications", icon: "bell", badge: 5 },
            { to: "/dashboard/ai-copilot", label: "AI Copilot", icon: "ai" },
            { to: "/dashboard/chat", label: "Chat", icon: "chat" },
        ],
    },
    {
        title: "Academic",
        items: [
            {
                to: "/dashboard/students",
                label: "Students",
                icon: "students",
                roles: [
                    "ADMIN",
                    "DIRECTOR",
                    "PRINCIPAL",
                    "CLASS_TEACHER",
                    "SUBJECT_TEACHER",
                    "STAFF",
                    "GUARDIAN",
                ],
            },
            { to: "/dashboard/attendance", label: "Attendance", icon: "attendance" },
            {
                to: "/dashboard/academics",
                label: "Academics & Marks",
                icon: "book",
                roles: [
                    "ADMIN",
                    "DIRECTOR",
                    "PRINCIPAL",
                    "HOD",
                    "CLASS_TEACHER",
                    "SUBJECT_TEACHER",
                    "STUDENT",
                    "GUARDIAN",
                    "STAFF",
                ],
            },
            {
                to: "/dashboard/exams",
                label: "Exams & AI Papers",
                icon: "edit",
                roles: [
                    "ADMIN",
                    "DIRECTOR",
                    "PRINCIPAL",
                    "HOD",
                    "CLASS_TEACHER",
                    "SUBJECT_TEACHER",
                    "STUDENT",
                    "GUARDIAN",
                    "STAFF",
                ],
            },
            {
                to: "/dashboard/homework",
                label: "Homework & Diary",
                icon: "book",
                roles: [
                    "ADMIN",
                    "DIRECTOR",
                    "PRINCIPAL",
                    "HOD",
                    "CLASS_TEACHER",
                    "SUBJECT_TEACHER",
                    "STUDENT",
                    "GUARDIAN",
                    "STAFF",
                ],
            },
            {
                to: "/dashboard/classroom",
                label: "Classroom",
                icon: "school",
                roles: [
                    "ADMIN",
                    "DIRECTOR",
                    "PRINCIPAL",
                    "HOD",
                    "CLASS_TEACHER",
                    "SUBJECT_TEACHER",
                    "STUDENT",
                    "STAFF",
                ],
            },
            { to: "/dashboard/timetable", label: "Timetable", icon: "calendar" },
        ],
    },
    {
        title: "People & Finance",
        items: [
            {
                to: "/dashboard/teachers",
                label: "Teachers & Staff",
                icon: "guardian",
                roles: ["ADMIN", "DIRECTOR", "PRINCIPAL", "HOD", "ACCOUNTANT"],
            },
            {
                to: "/dashboard/payroll",
                label: "Payroll / Payslip",
                icon: "money",
                roles: [
                    "ACCOUNTANT",
                    "DIRECTOR",
                    "PRINCIPAL",
                    "ADMIN",
                    "CLASS_TEACHER",
                    "SUBJECT_TEACHER",
                ],
            },
            {
                to: "/dashboard/finance",
                label: "Finance (Fees)",
                icon: "wallet",
                roles: ["ACCOUNTANT", "DIRECTOR", "ADMIN", "PRINCIPAL", "GUARDIAN", "STUDENT"],
            },
        ],
    },
    {
        title: "Services",
        items: [
            { to: "/dashboard/library", label: "Library", icon: "book" },
            { to: "/dashboard/transport", label: "Transport", icon: "bus" },
            {
                to: "/dashboard/meetings",
                label: "Meetings",
                icon: "groups",
                roles: [
                    "CLASS_TEACHER",
                    "SUBJECT_TEACHER",
                    "PRINCIPAL",
                    "HOD",
                    "DIRECTOR",
                    "GUARDIAN",
                    "STUDENT",
                ],
            },
            { to: "/dashboard/tickets", label: "Tickets & Support", icon: "warning" },
            { to: "/dashboard/leave", label: "Leave & Applications", icon: "calendar" },
        ],
    },
    {
        title: "Insights & Admin",
        items: [
            {
                to: "/dashboard/reports",
                label: "Reports & Analytics",
                icon: "trending",
                roles: [
                    "DIRECTOR",
                    "PRINCIPAL",
                    "HOD",
                    "ACCOUNTANT",
                    "ADMIN",
                    "CLASS_TEACHER",
                    "SUBJECT_TEACHER",
                ],
            },
            {
                to: "/dashboard/settings",
                label: "Settings",
                icon: "more",
                roles: [
                    "ADMIN",
                    "DIRECTOR",
                    "PRINCIPAL",
                    "HOD",
                    "CLASS_TEACHER",
                    "SUBJECT_TEACHER",
                    "STAFF",
                    "ACCOUNTANT",
                    "LIBRARIAN",
                    "TRANSPORT",
                ],
            },
        ],
    },
];
