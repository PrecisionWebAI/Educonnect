/**
 * Authorization hooks.
 *
 * Permissions now come from user.permissions[] populated by the backend API —
 * NOT from a hardcoded role→permissions map on the frontend.
 */

import { useAuth } from "../providers/auth-context";
import { hasPermission, hasAllPermissions, hasAnyPermission } from "../lib/auth/rbac";

/**
 * Returns true if the current user has the given permission.
 * Checks user.permissions[] from the API response.
 */
export function usePermission(permission: string): boolean {
    const { user } = useAuth();
    if (!user) return false;
    return hasPermission(user.permissions, permission);
}

/**
 * Returns true if the current user has ANY of the given permissions,
 * or ALL of them depending on the `requireAll` flag.
 */
export function useAuthorization(permissions: string[], requireAll = true): boolean {
    const { user } = useAuth();
    if (!user) return false;

    if (requireAll) {
        return hasAllPermissions(user.permissions, permissions);
    } else {
        return hasAnyPermission(user.permissions, permissions);
    }
}

/**
 * Returns true if the user's role matches any of the given role strings.
 */
export function useRole(roles: string | string[]): boolean {
    const { user } = useAuth();
    if (!user || !user.role) return false;
    const roleList = Array.isArray(roles) ? roles : [roles];
    return roleList.includes(user.role.toLowerCase());
}
