"use client";

import React, { useState, useCallback, useMemo, type Dispatch, type SetStateAction } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { PageHeader, Table, Badge, Select, Spinner } from "@/components/ui";
import { useAuthorization } from "@/hooks/use-authorization";
import { api } from "@/lib/api/client";
import { useApiQuery } from "@/lib/api/use-api-query";
import {
    getAllPermissions,
    getRolePermissionMap,
    updateRolePermissions,
    type GroupedPermissions,
    type RolePermissionMap,
    type PermissionItem,
} from "@/services/permissions.service";

interface UserResponse {
    id: number;
    email: string;
    full_name: string;
    role: string;
}

const ROLES = ["admin", "director", "principal", "teacher", "student", "guardian"] as const;
type Role = (typeof ROLES)[number];

const ROLE_LABELS: Record<Role, string> = {
    admin: "Admin",
    director: "Director",
    principal: "Principal",
    teacher: "Teacher",
    student: "Student",
    guardian: "Guardian",
};

// ── Helpers ─────────────────────────────────────────────────────────────────

/** Build a codename→id lookup from grouped permissions */
function buildCodenameMap(grouped: GroupedPermissions): Map<string, number> {
    const map = new Map<string, number>();
    for (const items of Object.values(grouped)) {
        for (const p of items) map.set(p.codename, p.id);
    }
    return map;
}

// ── Main Page ────────────────────────────────────────────────────────────────

export default function RBACAdminPage() {
    const hasPermission = useAuthorization(["roles.manage", "users.manage"], true);
    const queryClient = useQueryClient();

    // ── User role-assignment state ───────────────────────────────────────────
    const usersQuery = useApiQuery<UserResponse[]>(["users"], () => api.get<UserResponse[]>("/users?limit=50"), {
        enabled: hasPermission,
    });
    const users = usersQuery.data ?? [];
    const loadingUsers = hasPermission && usersQuery.isPending;
    const setUsers: Dispatch<SetStateAction<UserResponse[]>> = (action) => {
        queryClient.setQueryData<UserResponse[]>(["users"], (prev) =>
            typeof action === "function" ? action(prev ?? []) : action,
        );
    };
    const [savingId, setSavingId] = useState<number | null>(null);

    // ── Permission matrix state ──────────────────────────────────────────────
    const permsQuery = useApiQuery<GroupedPermissions>(["permissions"], getAllPermissions, {
        enabled: hasPermission,
    });
    const roleMapQuery = useApiQuery<RolePermissionMap>(
        ["permissions", "roles"],
        getRolePermissionMap,
        { enabled: hasPermission },
    );
    const groupedPerms = permsQuery.data ?? {};
    const rolePermMap = roleMapQuery.data ?? {};
    const setRolePermMap: Dispatch<SetStateAction<RolePermissionMap>> = (action) => {
        queryClient.setQueryData<RolePermissionMap>(["permissions", "roles"], (prev) =>
            typeof action === "function" ? action(prev ?? {}) : action,
        );
    };
    const [selectedRole, setSelectedRole] = useState<Role>("admin");
    const loadingPerms = hasPermission && (permsQuery.isPending || roleMapQuery.isPending);
    const [savingPerms, setSavingPerms] = useState(false);
    const codenameMap = useMemo(() => buildCodenameMap(groupedPerms), [groupedPerms]);

    // ── Checkbox helpers ─────────────────────────────────────────────────────
    const roleCodenames = new Set(rolePermMap[selectedRole] ?? []);

    const isChecked = (codename: string) => roleCodenames.has(codename);

    const togglePermission = useCallback((codename: string) => {
        setRolePermMap((prev) => {
            const current = new Set(prev[selectedRole] ?? []);
            if (current.has(codename)) current.delete(codename);
            else current.add(codename);
            return { ...prev, [selectedRole]: Array.from(current) };
        });
    }, [selectedRole]);

    const toggleCategory = useCallback((items: PermissionItem[]) => {
        const codenames = items.map((p) => p.codename);
        const allChecked = codenames.every((c) => roleCodenames.has(c));
        setRolePermMap((prev) => {
            const current = new Set(prev[selectedRole] ?? []);
            codenames.forEach((c) => allChecked ? current.delete(c) : current.add(c));
            return { ...prev, [selectedRole]: Array.from(current) };
        });
    }, [selectedRole, roleCodenames]);

    const handleSavePermissions = async () => {
        setSavingPerms(true);
        try {
            const ids = Array.from(roleCodenames)
                .map((c) => codenameMap.get(c))
                .filter((id): id is number => id !== undefined);
            await updateRolePermissions(selectedRole, ids);
            // Re-sync the role map from the server so the matrix reflects saved state.
            await queryClient.invalidateQueries({ queryKey: ["permissions", "roles"] });
            alert(`Permissions for "${ROLE_LABELS[selectedRole]}" saved successfully.`);
        } catch {
            alert("Failed to save permissions. Please try again.");
        } finally {
            setSavingPerms(false);
        }
    };

    // ── User role change ─────────────────────────────────────────────────────
    const handleRoleChange = async (userId: number, newRole: string) => {
        setSavingId(userId);
        try {
            const updatedUser = await api.patch<UserResponse>(`/users/${userId}/role?role=${newRole}`);
            setUsers(users.map((u) => (u.id === userId ? updatedUser : u)));
        } catch {
            alert("Failed to update role. Please ensure you have the correct permissions.");
        } finally {
            setSavingId(null);
        }
    };

    // ── Access guard ─────────────────────────────────────────────────────────
    if (!hasPermission) {
        return (
            <div>
                <PageHeader title="RBAC Administration" subtitle="Role-Based Access Control" />
                <div className="rounded-md bg-red-50 p-4 text-red-600">
                    You do not have permission to manage roles.
                </div>
            </div>
        );
    }

    // ── User assignment table columns ────────────────────────────────────────
    const columns = [
        { key: "full_name", header: "Name", render: (u: UserResponse) => <b>{u.full_name}</b> },
        { key: "email", header: "Email" },
        {
            key: "current_role",
            header: "Current Role",
            render: (u: UserResponse) => <Badge tone="accent">{u.role}</Badge>,
        },
        {
            key: "actions",
            header: "Change Role",
            render: (u: UserResponse) => (
                <div className="flex items-center gap-2">
                    <Select
                        value={u.role}
                        onChange={(e) => handleRoleChange(u.id, e.target.value)}
                        disabled={savingId === u.id}
                    >
                        {ROLES.map((r) => (
                            <option key={r} value={r}>{ROLE_LABELS[r]}</option>
                        ))}
                    </Select>
                    {savingId === u.id && <Spinner size="sm" />}
                </div>
            ),
        },
    ];

    return (
        <div>
            <PageHeader
                title="RBAC Administration"
                subtitle="Manage user roles and system access permissions."
            />

            {/* ── User Role Assignments ─────────────────────────────────── */}
            <div className="mt-6 rounded-lg bg-white p-6 shadow">
                <h3 className="mb-4 text-lg font-bold">User Role Assignments</h3>
                {loadingUsers ? (
                    <Spinner />
                ) : (
                    <Table
                        columns={columns}
                        rows={users}
                        rowKey={(u) => u.id}
                        empty="No users found."
                    />
                )}
            </div>

            {/* ── Permission Matrix ─────────────────────────────────────── */}
            <div className="mt-6 rounded-lg bg-white p-6 shadow">
                <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                    <h3 className="text-lg font-bold">Role Permission Matrix</h3>
                    <div className="flex items-center gap-3">
                        <Select
                            value={selectedRole}
                            onChange={(e) => setSelectedRole(e.target.value as Role)}
                        >
                            {ROLES.map((r) => (
                                <option key={r} value={r}>{ROLE_LABELS[r]}</option>
                            ))}
                        </Select>
                        <button
                            onClick={handleSavePermissions}
                            disabled={savingPerms || loadingPerms}
                            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                        >
                            {savingPerms ? "Saving…" : "Save Changes"}
                        </button>
                    </div>
                </div>

                {loadingPerms ? (
                    <Spinner />
                ) : (
                    <div className="space-y-6">
                        {Object.entries(groupedPerms).map(([category, items]) => {
                            const allChecked = items.every((p) => isChecked(p.codename));
                            const someChecked = items.some((p) => isChecked(p.codename));
                            return (
                                <div key={category}>
                                    <div className="mb-2 flex items-center gap-2 border-b pb-1">
                                        <input
                                            type="checkbox"
                                            id={`cat-${category}`}
                                            checked={allChecked}
                                            ref={(el) => { if (el) el.indeterminate = !allChecked && someChecked; }}
                                            onChange={() => toggleCategory(items)}
                                            className="h-4 w-4 rounded"
                                        />
                                        <label htmlFor={`cat-${category}`} className="font-semibold text-gray-800 cursor-pointer">
                                            {category}
                                        </label>
                                        <span className="ml-auto text-xs text-gray-400">
                                            {items.filter((p) => isChecked(p.codename)).length}/{items.length}
                                        </span>
                                    </div>
                                    <div className="grid grid-cols-2 gap-1 sm:grid-cols-3 lg:grid-cols-4">
                                        {items.map((perm) => (
                                            <label
                                                key={perm.codename}
                                                className="flex cursor-pointer items-center gap-2 rounded p-1.5 hover:bg-gray-50"
                                            >
                                                <input
                                                    type="checkbox"
                                                    checked={isChecked(perm.codename)}
                                                    onChange={() => togglePermission(perm.codename)}
                                                    className="h-4 w-4 rounded"
                                                />
                                                <span className="text-sm text-gray-700">{perm.label}</span>
                                            </label>
                                        ))}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                )}
            </div>
        </div>
    );
}
