import { api } from "@/lib/api/client";
import type { Session, User } from "@/types";

interface TokenResponse {
    access_token: string;
    token_type: string;
    refresh_token: string;
    user: User;
}

export async function loginUser(identifier: string, password: string): Promise<Session> {
    const data = await api.post<TokenResponse>("/auth/token", {
        username: identifier,
        password,
    });

    return {
        accessToken: data.access_token,
        refreshToken: data.refresh_token,
        user: data.user,
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
    return api.get<User>("/auth/me");
}
