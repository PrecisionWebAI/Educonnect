import { api } from "@/lib/api/client";
import { toSession, type TokenResponse } from "@/services/auth.service";
import type { Session } from "@/types";

// ============================================================
// Super-admin "switch account" (impersonation).
//
// Only a session holding `users.impersonate` - the platform admin role alone -
// can use these routes; the backend answers 403 for every other account, so the
// UI gate is convenience, not the security boundary.
//
//   GET  /auth/impersonate/roles   role dropdown, with how many people hold each
//   GET  /auth/impersonate/users   people list: role filter + e-mail/name search
//   POST /auth/impersonate         switch into an account
//   POST /auth/impersonate/stop    return to the admin's own account
//
// The switched session carries its own token; the administrator rides along in
// that token's `act` claim, which is why "Return" needs no stored copy of the
// admin's token and still works after a page refresh.
// ============================================================

export interface ImpersonationRoleOption {
    codename: string;
    label: string;
    users: number;
}

export interface ImpersonationTarget {
    id: string;
    email: string;
    full_name: string;
    roles: string[];
    role: string;
    /** Shown *under* the person's name in the picker. */
    role_label: string;
}

// The switched session is built by the *same* mapper a login uses
// (`toSession` in `auth.service`): the two endpoints return the same envelope, and
// a private copy here is what used to drop `schoolId`/`schoolName` - and the
// `impersonatedBy` the banner needs - from a switched session.

export async function getImpersonationRoles(): Promise<ImpersonationRoleOption[]> {
    const data = await api.get<{ roles: ImpersonationRoleOption[] }>("/auth/impersonate/roles");
    return data.roles;
}

export async function searchImpersonationTargets(params: {
    role?: string;
    search?: string;
    limit?: number;
}): Promise<ImpersonationTarget[]> {
    const query = new URLSearchParams();
    if (params.role) query.set("role", params.role);
    if (params.search) query.set("search", params.search);
    query.set("limit", String(params.limit ?? 100));
    const data = await api.get<{ users: ImpersonationTarget[] }>(
        `/auth/impersonate/users?${query.toString()}`,
    );
    return data.users;
}

export async function startImpersonation(userId: string, reason?: string): Promise<Session> {
    const data = await api.post<TokenResponse>("/auth/impersonate", {
        user_id: userId,
        reason,
    });
    return toSession(data);
}

export async function stopImpersonation(): Promise<Session> {
    const data = await api.post<TokenResponse>("/auth/impersonate/stop");
    return toSession(data);
}
