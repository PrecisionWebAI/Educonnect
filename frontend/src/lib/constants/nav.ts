import type { IconName } from "@/components/ui/Icon";
import type { Role } from "@/types";

// ============================================================
// Sidebar navigation — one entry per blueprinted module page.
// Next.js routes: /dashboard/<module>. Icons are SVG names
// (see components/ui/Icon.tsx) — no emoji anywhere.
//
// A group here is a MENU heading: it groups pages for the user.
// A backend folder is a BOUNDARY: one set of tables + permissions.
// The two are allowed to differ, so a menu group can span multiple
// backend packages:
//
//   Dashboard             -> backend/app/domains/main
//   Academic              -> backend/app/domains/academic
//   People                -> backend/app/domains/people + finance
//   Services              -> backend/app/domains/services
//   Operations & Insights -> backend/app/domains/operations + finance + insights + admin
//   (no menu entry)       -> backend/app/domains/auth
//
// Full screen -> package -> permission table:
// backend/app/domains/README.md
// ============================================================

export interface NavItem {
    to: string;
    label: string;
    icon: IconName;
    permissions?: string[];
    /** When set, only these roles see the entry (a page that is only for them). */
    roles?: Role[];
    badge?: number;
}

export interface NavGroup {
    title: string;
    items: NavItem[];
}

export const NAV_GROUPS: NavGroup[] = [
    {
        title: "Dashboard",
        items: [
            {
                to: "/dashboard",
                label: "Dashboard",
                icon: "dashboard",
                permissions: ["dashboard.read"],
            },
        ],
    },
    {
        title: "Academic",
        items: [
            {
                to: "/dashboard/classroom",
                label: "Classroom",
                icon: "school",
                permissions: ["classes.read"],
            },
            {
                // A student's or guardian's own children's exam results - published
                // marks only. Staff read results inside a class-section's Exams tab.
                to: "/dashboard/exam-results",
                label: "Exams",
                icon: "book",
                permissions: ["marks.read"],
                roles: ["STUDENT", "GUARDIAN"],
            },
        ],
    },
    {
        title: "People",
        items: [
            {
                to: "/dashboard/teachers",
                label: "Teachers",
                icon: "guardian",
                permissions: ["teachers.read"],
            },
            {
                // The other half of the split (0.9): everybody whose roles are not
                // teaching. Same permission - it is the same directory, scoped.
                to: "/dashboard/staff",
                label: "Staff",
                icon: "guardian",
                permissions: ["teachers.read"],
            },
            {
                to: "/dashboard/payroll",
                label: "Payroll / Payslip",
                icon: "money",
                permissions: ["payroll.read", "payroll.view_payslip"],
            },
        ],
    },
    {
        title: "Services",
        items: [
            { to: "/dashboard/chat", label: "Chat", icon: "chat", permissions: ["messages.read"] },
            {
                to: "/dashboard/library",
                label: "Library",
                icon: "book",
                permissions: ["library.read"],
            },
            {
                to: "/dashboard/transport",
                label: "Transport",
                icon: "bus",
                permissions: ["transport.read"],
            },
            {
                to: "/dashboard/meetings",
                label: "Meetings",
                icon: "groups",
                permissions: ["ptm.read"],
            },
            {
                to: "/dashboard/tickets",
                label: "Tickets & Support",
                icon: "warning",
                permissions: ["dashboard.read"],
            },
            {
                to: "/dashboard/leave",
                label: "Leave & Applications",
                icon: "calendar",
                permissions: ["leave.read"],
            },
        ],
    },
    {
        title: "Operations & Insights",
        items: [
            {
                to: "/dashboard/finance",
                label: "Finance (Fees)",
                icon: "wallet",
                permissions: ["fees.read"],
            },
            {
                to: "/dashboard/operations/admission",
                label: "Admission",
                icon: "students",
                permissions: ["admissions.read"],
            },
            {
                to: "/dashboard/operations/staff-hiring",
                label: "Staff Hiring",
                icon: "guardian",
                permissions: ["hiring.read"],
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
            {
                // The school's own calendar (holidays, weekly offs, vacation). It belongs to
                // the school, not to a class, so it sits here and not inside a section's
                // Attendance tab. The whole page is `holiday.manage` (principal and above):
                // it moves every class's percentages, and the register keeps its own reads.
                to: "/dashboard/operations/calendar",
                label: "Calendar",
                icon: "calendar",
                permissions: ["holiday.manage"],
            },
            {
                to: "/dashboard/reports",
                label: "Reports & Analytics",
                icon: "trending",
                permissions: ["reports.read"],
            },
            {
                to: "/dashboard/settings",
                label: "Settings",
                icon: "more",
                permissions: ["settings.read", "profile.read"],
            },
        ],
    },
];
