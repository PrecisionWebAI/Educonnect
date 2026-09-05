import type { Role } from "@/types";

// ============================================================
// Centralized Role-Based Access Control (RBAC) definitions
// ============================================================

export const LEADERSHIP_ROLES: Role[] = ["DIRECTOR", "ADMIN", "PRINCIPAL", "HOD"];
export const TEACHER_ROLES: Role[] = ["CLASS_TEACHER", "SUBJECT_TEACHER"];
export const ALL_STAFF_ROLES: Role[] = [
    "DIRECTOR",
    "ADMIN",
    "PRINCIPAL",
    "HOD",
    "CLASS_TEACHER",
    "SUBJECT_TEACHER",
    "STAFF",
    "ACCOUNTANT",
    "LIBRARIAN",
    "TRANSPORT",
];
export const ACADEMIC_STAFF_ROLES: Role[] = [
    "DIRECTOR",
    "ADMIN",
    "PRINCIPAL",
    "HOD",
    "CLASS_TEACHER",
    "SUBJECT_TEACHER",
    "STAFF",
];
export const STUDENT_ROLES: Role[] = ["STUDENT"];
export const PARENT_ROLES: Role[] = ["GUARDIAN"];
export const FINANCE_ROLES: Role[] = ["ACCOUNTANT", "DIRECTOR", "ADMIN", "PRINCIPAL"];

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
 */
export const ROUTE_ROLES: Record<string, Role[]> = {
    "/dashboard/students": [
        "ADMIN",
        "DIRECTOR",
        "PRINCIPAL",
        "CLASS_TEACHER",
        "SUBJECT_TEACHER",
        "STAFF",
        "GUARDIAN",
    ],
    "/dashboard/teachers": ["ADMIN", "DIRECTOR", "PRINCIPAL", "HOD", "ACCOUNTANT"],
    "/dashboard/payroll": [
        "ACCOUNTANT",
        "DIRECTOR",
        "PRINCIPAL",
        "ADMIN",
        "CLASS_TEACHER",
        "SUBJECT_TEACHER",
    ],
    "/dashboard/finance": ["ACCOUNTANT", "DIRECTOR", "ADMIN", "PRINCIPAL", "GUARDIAN", "STUDENT"],
    "/dashboard/reports": ["DIRECTOR", "PRINCIPAL", "HOD", "ACCOUNTANT", "ADMIN"],
    "/dashboard/settings": [
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
};
