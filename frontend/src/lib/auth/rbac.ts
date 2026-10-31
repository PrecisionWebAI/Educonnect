import type { Role } from "@/types";

// ============================================================
// Centralized Role-Based Access Control (RBAC) definitions
// ============================================================

export const LEADERSHIP_ROLES: Role[] = [
    "SYSTEM_ADMIN",
    "SCHOOL_ADMIN",
    "PRINCIPAL",
    "VICE_PRINCIPAL",
    "HOD",
];
export const TEACHER_ROLES: Role[] = ["CLASS_TEACHER", "SUBJECT_TEACHER", "TEACHER"];
export const ALL_STAFF_ROLES: Role[] = [
    "SYSTEM_ADMIN",
    "SCHOOL_ADMIN",
    "PRINCIPAL",
    "VICE_PRINCIPAL",
    "HOD",
    "TEACHER",
    "CLASS_TEACHER",
    "SUBJECT_TEACHER",
    "ACCOUNTANT",
    "LIBRARIAN",
    "TRANSPORT",
    "STAFF",
];
export const ACADEMIC_STAFF_ROLES: Role[] = [
    "SYSTEM_ADMIN",
    "SCHOOL_ADMIN",
    "PRINCIPAL",
    "VICE_PRINCIPAL",
    "HOD",
    "TEACHER",
    "CLASS_TEACHER",
    "SUBJECT_TEACHER",
    "STAFF",
];
export const STUDENT_ROLES: Role[] = ["STUDENT"];
export const PARENT_ROLES: Role[] = ["GUARDIAN"];
export const FINANCE_ROLES: Role[] = ["ACCOUNTANT", "PRINCIPAL", "SYSTEM_ADMIN", "SCHOOL_ADMIN"];

/**
 * Checks if the user has at least one of the allowed roles.
 * If allowedRoles is undefined or empty, returns true (open to all).
 */
export function hasAnyRole(userRoles?: Role[] | null, allowedRoles?: Role[] | null): boolean {
    if (!allowedRoles || allowedRoles.length === 0) return true;
    if (!userRoles || userRoles.length === 0) return false;
    return userRoles.some((r) => allowedRoles.includes(r));
}

/** Check if user belongs to staff (teachers, leadership, administration) */
export function isStaff(userRoles?: Role[] | null): boolean {
    return hasAnyRole(userRoles, ALL_STAFF_ROLES);
}

/** Check if user is student */
export function isStudent(userRoles?: Role[] | null): boolean {
    return hasAnyRole(userRoles, STUDENT_ROLES);
}

/** Check if user is parent / guardian */
export function isParent(userRoles?: Role[] | null): boolean {
    return hasAnyRole(userRoles, PARENT_ROLES);
}

/**
 * Mapping of dashboard routes to allowed roles.
 * Routes not listed here are open to all authenticated users.
 * Must stay in sync with NAV_GROUPS in lib/constants/nav.ts.
 */
export const ROUTE_ROLES: Record<string, Role[]> = {
    // ── Academic ──────────────────────────────────────────────
    "/dashboard/students": [
        "SYSTEM_ADMIN",
        "PRINCIPAL",
        "HOD",
        "CLASS_TEACHER",
        "SUBJECT_TEACHER",
        "STAFF",
        "GUARDIAN",
    ],
    "/dashboard/attendance": [
        "SYSTEM_ADMIN",
        "PRINCIPAL",
        "HOD",
        "CLASS_TEACHER",
        "SUBJECT_TEACHER",
        "STUDENT",
        "GUARDIAN",
    ],
    "/dashboard/academics": [
        "SYSTEM_ADMIN",
        "PRINCIPAL",
        "HOD",
        "CLASS_TEACHER",
        "SUBJECT_TEACHER",
        "STUDENT",
        "GUARDIAN",
    ],
    "/dashboard/exams": [
        "SYSTEM_ADMIN",
        "PRINCIPAL",
        "HOD",
        "CLASS_TEACHER",
        "SUBJECT_TEACHER",
    ],
    "/dashboard/homework": [
        "SYSTEM_ADMIN",
        "PRINCIPAL",
        "HOD",
        "CLASS_TEACHER",
        "SUBJECT_TEACHER",
        "STUDENT",
        "GUARDIAN",
    ],
    "/dashboard/classroom": [
        "SYSTEM_ADMIN",
        "PRINCIPAL",
        "HOD",
        "CLASS_TEACHER",
        "SUBJECT_TEACHER",
        "STUDENT",
    ],
    "/dashboard/timetable": [
        "SYSTEM_ADMIN",
        "PRINCIPAL",
        "HOD",
        "CLASS_TEACHER",
        "SUBJECT_TEACHER",
        "STUDENT",
        "GUARDIAN",
    ],
    // ── People & Finance ─────────────────────────────────────
    "/dashboard/teachers": ["SYSTEM_ADMIN", "PRINCIPAL", "HOD", "ACCOUNTANT"],
    "/dashboard/payroll": [
        "ACCOUNTANT",
        "PRINCIPAL",
        "SYSTEM_ADMIN",
        "CLASS_TEACHER",
        "SUBJECT_TEACHER",
    ],
    "/dashboard/finance": [
        "ACCOUNTANT",
        "SYSTEM_ADMIN",
        "PRINCIPAL",
        "GUARDIAN",
        "STUDENT",
    ],
    // ── Services ─────────────────────────────────────────────
    "/dashboard/transport": [
        "SYSTEM_ADMIN",
        "PRINCIPAL",
        "TRANSPORT",
        "CLASS_TEACHER",
        "STUDENT",
        "GUARDIAN",
    ],
    "/dashboard/meetings": [
        "SYSTEM_ADMIN",
        "PRINCIPAL",
        "HOD",
        "CLASS_TEACHER",
        "SUBJECT_TEACHER",
        "GUARDIAN",
        "STUDENT",
    ],
    // ── Operations ────────────────────────────────────────────
    "/dashboard/operations/admission": ["SYSTEM_ADMIN", "PRINCIPAL", "HOD", "STAFF"],
    "/dashboard/operations/staff-hiring": ["SYSTEM_ADMIN", "PRINCIPAL", "HOD"],
    "/dashboard/operations/fees-structure": ["SYSTEM_ADMIN", "PRINCIPAL", "ACCOUNTANT"],
    "/dashboard/operations/salary": ["SYSTEM_ADMIN", "PRINCIPAL", "ACCOUNTANT"],
    // ── Insights & Admin ─────────────────────────────────────
    "/dashboard/reports": ["PRINCIPAL", "HOD", "ACCOUNTANT", "SYSTEM_ADMIN"],
    "/dashboard/settings": ["SYSTEM_ADMIN", "PRINCIPAL"],
};

/**
 * Check whether a user is allowed to visit a given route.
 * Returns true if the route has no restriction or the user holds at least one
 * of the required roles.
 */
export function canAccessRoute(pathname: string, userRoles?: Role[] | null): boolean {
    // The school admin is the whole-of-school admin (the backend's BYPASS_ROLES):
    // it may open every dashboard route for its school. Platform-only endpoints
    // are still enforced by the API.
    if (userRoles?.includes("SCHOOL_ADMIN")) return true;
    const allowedRoles = ROUTE_ROLES[pathname];
    return hasAnyRole(userRoles, allowedRoles);
}

/** Check if user has a specific permission */
export function hasPermission(userPermissions?: string[] | null, permission?: string): boolean {
    if (!permission) return true;
    if (!userPermissions || userPermissions.length === 0) return false;
    return userPermissions.includes(permission);
}

/** Check if user has ALL specified permissions */
export function hasAllPermissions(
    userPermissions?: string[] | null,
    permissions?: string[],
): boolean {
    if (!permissions || permissions.length === 0) return true;
    if (!userPermissions || userPermissions.length === 0) return false;
    return permissions.every((p) => userPermissions.includes(p));
}

/** Check if user has ANY of the specified permissions */
export function hasAnyPermission(
    userPermissions?: string[] | null,
    permissions?: string[],
): boolean {
    if (!permissions || permissions.length === 0) return true;
    if (!userPermissions || userPermissions.length === 0) return false;
    return permissions.some((p) => userPermissions.includes(p));
}
