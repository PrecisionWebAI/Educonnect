"use client";
import { useCallback, useEffect, useState, type ReactNode } from "react";
import type { Session, User } from "../types";
import { loginUser, logoutUser } from "@/services/auth.service";
import { AuthContext, STORAGE_KEY, type AuthContextValue } from "./auth-context";

// ============================================================
// AuthProvider — holds the current session via real backend API.
// ============================================================

function readStoredSession(): Session | null {
    try {
        const raw =
            localStorage.getItem(STORAGE_KEY) ??
            localStorage.getItem("EduConnect.session") ??
            localStorage.getItem("educonnect.session");
        return raw ? (JSON.parse(raw) as Session) : null;
    } catch {
        return null;
    }
}

export function AuthProvider({ children }: { children: ReactNode }) {
    const [session, setSession] = useState<Session | null>(() =>
        typeof window !== "undefined" ? readStoredSession() : null,
    );

    useEffect(() => {
        if (session) {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
        } else {
            localStorage.removeItem(STORAGE_KEY);
            localStorage.removeItem("EduConnect.session");
            localStorage.removeItem("educonnect.session");
        }
    }, [session]);

    const login = useCallback(async (identifier: string, password: string): Promise<User> => {
        const s = await loginUser(identifier, password);
        setSession(s);
        return s.user;
    }, []);

    const logout = useCallback(async () => {
        if (session) {
            try {
                await logoutUser();
            } catch {
                /* best effort */
            }
        }
        setSession(null);
    }, [session]);

    const setUser = useCallback((user: User) => {
        setSession((prev) => (prev ? { ...prev, user } : prev));
    }, []);

    const value: AuthContextValue = {
        session,
        user: session?.user ?? null,
        isAuthed: session !== null,
        login,
        logout,
        setUser,
    };

    return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
