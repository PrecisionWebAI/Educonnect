import { api } from "@/lib/api/client";
import type { Role, Session, User } from "@/types";

/**
 * Shape of the user object returned by the backend's _build_user_dict().
 * Keys are camelCase because that's what the backend sends.
 */
interface BackendUser {
    id: number;
    username: string;
    email: string;
    fullName: string;          // camelCase — backend sends "fullName" not "full_name"
    roles: string[];           // e.g. ["ADMIN"]
    role?: string;             // lowercase role value e.g. "admin" (for PBAC)
    permissions: string[];     // list of permission codenames from DB
    department?: string;
}

interface TokenResponse {
    access_token: string;
    token_type: string;
    refresh_token: string;
    user: BackendUser;
}

export async function loginUser(identifier: string, password: string): Promise<Session> {
    const data = await api.post<TokenResponse>("/auth/token", {
        username: identifier,
        password,
    });

    const backendUser = data.user;
    const frontendUser: User = {
        id: backendUser.id,
        username: backendUser.username ?? backendUser.email,
        email: backendUser.email,
        fullName: backendUser.fullName || "Unknown User",
        roles: (backendUser.roles ?? []).map((r) => r.toUpperCase() as Role),
        role: backendUser.role,
        permissions: backendUser.permissions ?? [],
    };

    return {
        accessToken: data.access_token,
        refreshToken: data.refresh_token,
        user: frontendUser,
    };
}

export async function logoutUser(): Promise<void> {
    try {
        await api.post("/auth/logout");
    } catch {
        /* best effort */
    }
}

export async function getCurrentUser(): Promise<User> {
    const backendUser = await api.get<BackendUser>("/auth/me");
    return {
        id: backendUser.id,
        username: backendUser.username ?? backendUser.email,
        email: backendUser.email,
        fullName: backendUser.fullName || "Unknown User",
        roles: (backendUser.roles ?? []).map((r) => r.toUpperCase() as Role),
        role: backendUser.role,
        permissions: backendUser.permissions ?? [],
    };
}
