import { api } from "@/lib/api/client";
import { titleCase } from "@/lib/format";
import type { Role, Session, User } from "@/types";

/**
 * Shape of the user object returned by the backend's _build_user_dict().
 * Keys are camelCase because that's what the backend sends.
 */
interface BackendUser {
    id: string;
    username: string;
    email: string;
    fullName: string; // camelCase — backend sends "fullName" not "full_name"
    roles: string[]; // e.g. ["SYSTEM_ADMIN"]
    role?: string; // lowercase role value e.g. "SYSTEM_ADMIN" (for PBAC)
    permissions: string[]; // list of permission codenames from DB
    department?: string;
    //: The school this session is confined to; absent for a platform admin.
    schoolId?: string | null;
    //: That school's name — the header shows it where the search box used to be.
    schoolName?: string | null;
}

/** The backend's payload → the shape the app renders. */
function toFrontendUser(backendUser: BackendUser): User {
    return {
        id: backendUser.id,
        username: backendUser.username ?? backendUser.email,
        email: backendUser.email,
        // Stored lower-case (`app/core/text.py`); the header and the profile show
        // it the way a school writes it.
        fullName: titleCase(backendUser.fullName) || "Unknown User",
        roles: (backendUser.roles ?? []).map((r) => r.toUpperCase() as Role),
        role: backendUser.role,
        permissions: backendUser.permissions ?? [],
        schoolId: backendUser.schoolId ?? null,
        schoolName: titleCase(backendUser.schoolName) || null,
    };
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

    return {
        accessToken: data.access_token,
        refreshToken: data.refresh_token,
        user: toFrontendUser(data.user),
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
    return toFrontendUser(backendUser);
}
