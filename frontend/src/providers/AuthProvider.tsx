"use client";
import { useCallback, useEffect, useState, useSyncExternalStore, type ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import type { Session, User } from "../types";
import { loginUser, logoutUser } from "@/services/auth.service";
import { AuthContext, STORAGE_KEY, type AuthContextValue } from "./auth-context";

// ============================================================
// AuthProvider — holds the current session via real backend API.
// ============================================================

const emptySubscribe = () => () => {};

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
    const queryClient = useQueryClient();

    // useSyncExternalStore:
    // - Server snapshot & initial hydration snapshot: false
    // - Client snapshot: true
    // This allows SSR and initial client hydration to render the exact same DOM (unauthed state),
    // and then seamlessly transition on the client once mounted without triggering a hydration error.
    const isClient = useSyncExternalStore(
        emptySubscribe,
        () => true,
        () => false,
    );

    const [session, setSession] = useState<Session | null>(() => readStoredSession());

    useEffect(() => {
        if (!isClient) return;
        if (session) {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
        } else {
            localStorage.removeItem(STORAGE_KEY);
            localStorage.removeItem("EduConnect.session");
            localStorage.removeItem("educonnect.session");
        }
    }, [session, isClient]);

    const login = useCallback(
        async (identifier: string, password: string): Promise<User> => {
            const s = await loginUser(identifier, password);
            // Drop any cached data from a previous session before switching users.
            queryClient.clear();
            setSession(s);
            return s.user;
        },
        [queryClient],
    );

    const logout = useCallback(async () => {
        if (session) {
            try {
                await logoutUser();
            } catch {
                /* best effort */
            }
        }
        // Never leak this user's cached pages into the next session.
        queryClient.clear();
        setSession(null);
    }, [session, queryClient]);

    const setUser = useCallback((user: User) => {
        setSession((prev) => (prev ? { ...prev, user } : prev));
    }, []);

    const value: AuthContextValue = {
        session,
        user: session?.user ?? null,
        isAuthed: isClient && session !== null,
        isInitialized: isClient,
        login,
        logout,
        setUser,
    };

    return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
