import type { IconName } from "@/components/ui/Icon";

// ============================================================
// Sidebar navigation — one entry per blueprinted module page.
// Next.js routes: /dashboard/<module>. Icons are SVG names
// (see components/ui/Icon.tsx) — no emoji anywhere.
//
// A group here is a MENU heading: it groups pages for the user.
// A backend folder is a BOUNDARY: one set of tables + permissions.
// The two are allowed to differ, so "People & Finance" is two
// backend packages and "Insights & Admin" is two as well:
//
//   Main             -> backend/app/domains/main
//   Academic         -> backend/app/domains/academic
//   People & Finance -> backend/app/domains/people + finance
//   Services         -> backend/app/domains/services
//   Operations       -> backend/app/domains/operations
//   Insights & Admin -> backend/app/domains/insights + admin
//   (no menu entry)  -> backend/app/domains/auth
//
// Full screen -> package -> permission table:
// backend/app/domains/README.md
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
            {
                to: "/dashboard",
                label: "Dashboard",
                icon: "dashboard",
                permissions: ["dashboard.read"],
            },

            { to: "/dashboard/chat", label: "Chat", icon: "chat", permissions: ["messages.read"] },
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
        ],
    },
    {
        title: "People & Finance",
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
            {
                to: "/dashboard/finance",
                label: "Finance (Fees)",
                icon: "wallet",
                permissions: ["fees.read"],
            },
        ],
    },
    {
        title: "Services",
        items: [
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
        title: "Operations",
        items: [
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
        ],
    },
    {
        title: "Insights & Admin",
        items: [
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
