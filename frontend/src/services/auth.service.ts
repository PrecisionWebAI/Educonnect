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
    //: A platform admin who picked one school: own identity, that school's data.
    schoolScope?: boolean;
    //: Set when a platform admin switched into this account ("view as").
    impersonatedBy?: { id: string; fullName: string; email: string } | null;
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
        // True while a platform admin is looking at one school: the header shows
        // that school's name and the strip offers "All schools" back.
        schoolScope: backendUser.schoolScope ?? false,
        // Who to return to. Without this mapping a switched session loses the
        // fact that it *is* one as soon as `/auth/me` refreshes it, and the
        // "Viewing as … — Return" banner disappears on the next page load.
        impersonatedBy: backendUser.impersonatedBy
            ? {
                  id: backendUser.impersonatedBy.id,
                  fullName: titleCase(backendUser.impersonatedBy.fullName),
                  email: backendUser.impersonatedBy.email,
              }
            : null,
    };
}

export interface TokenResponse {
    access_token: string;
    token_type: string;
    refresh_token: string;
    user: BackendUser;
}

/**
 * A login-shaped API payload → the session the auth context stores.
 *
 * Exported and shared: `/auth/impersonate` answers with exactly the same envelope
 * as `/auth/token`, so the "switch account" flow must build the session the same
 * way - a second copy of this mapper is how the switched session used to lose its
 * `schoolId`/`schoolName` (`impersonation.service.ts` had its own).
 */
export function toSession(data: TokenResponse): Session {
    return {
        accessToken: data.access_token,
        refreshToken: data.refresh_token,
        user: toFrontendUser(data.user),
    };
}

export async function loginUser(identifier: string, password: string): Promise<Session> {
    const data = await api.post<TokenResponse>("/auth/token", {
        username: identifier,
        password,
    });

    return toSession(data);
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
