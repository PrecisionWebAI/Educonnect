"use client";
import { useCallback, useEffect, useRef, useState, useSyncExternalStore, type ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import type { Session, User } from "../types";
import { getCurrentUser, loginUser, logoutUser } from "@/services/auth.service";
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

    // Permissions and roles belong to the server and can change while a tab stays
    // open (a role granted, a permission added, an impersonated session). Refresh
    // them once per token, so a session stored weeks ago can never hide a control
    // the account now qualifies for - and the "viewing as" banner stays true after
    // a page reload.
    const refreshedToken = useRef<string | null>(null);
    useEffect(() => {
        if (!isClient || !session) return;
        if (refreshedToken.current === session.accessToken) return;
        refreshedToken.current = session.accessToken;
        void getCurrentUser()
            .then(setUser)
            .catch(() => {
                /* keep the stored session; the next API call re-checks auth */
            });
    }, [isClient, session, setUser]);

    /** Swap the whole session - the "switch account" path. */
    const switchSession = useCallback(
        (next: Session) => {
            // Never leak the previous user's cached pages into the new identity.
            queryClient.clear();
            setSession(next);
        },
        [queryClient],
    );

    const value: AuthContextValue = {
        session,
        user: session?.user ?? null,
        isAuthed: isClient && session !== null,
        isInitialized: isClient,
        login,
        logout,
        setUser,
        switchSession,
    };

    return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
