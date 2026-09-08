import { api } from "@/lib/api/client";

// ── Types ────────────────────────────────────────────────────────────────────

export interface PermissionItem {
    id: number;
    codename: string;
    label: string;
}

export interface GroupedPermissions {
    [category: string]: PermissionItem[];
}

export interface RolePermissionMap {
    [role: string]: string[]; // role → [codename, ...]
}

// ── API calls ────────────────────────────────────────────────────────────────

/**
 * Fetch all available permissions grouped by category.
 * Requires: permissions.manage
 */
export async function getAllPermissions(): Promise<GroupedPermissions> {
    const data = await api.get<{ permissions: GroupedPermissions }>("/auth/permissions");
    return data.permissions;
}

/**
 * Fetch the full role → [codename] map.
 * Requires: permissions.manage
 */
export async function getRolePermissionMap(): Promise<RolePermissionMap> {
    const data = await api.get<{ role_permissions: RolePermissionMap }>("/auth/permissions/roles");
    return data.role_permissions;
}

/**
 * Replace a role's permission set with the given permission IDs.
 * Requires: permissions.manage
 */
export async function updateRolePermissions(
    role: string,
    permissionIds: number[],
): Promise<void> {
    await api.put(`/auth/permissions/roles/${role}`, {
        permission_ids: permissionIds,
    });
}
