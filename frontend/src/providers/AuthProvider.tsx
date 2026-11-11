"use client";
import {
    useCallback,
    useEffect,
    useRef,
    useState,
    useSyncExternalStore,
    type ReactNode,
} from "react";
import { useQueryClient } from "@tanstack/react-query";
import type { Session, User } from "../types";
import { setAccessToken } from "@/lib/api/client";
import { getCurrentUser, loginUser, logoutUser } from "@/services/auth.service";
import { AuthContext, STORAGE_KEY, type AuthContextValue } from "./auth-context";

// ============================================================
// AuthProvider — holds the current session via real backend API.
// ============================================================

const emptySubscribe = () => () => {};

/** The stored session, in the one shape the rest of the app reads it. */
function writeStoredSession(next: Session | null): void {
    // The in-memory token goes first: the next API call reads it synchronously, so
    // no request can be signed with the session we are replacing.
    setAccessToken(next?.accessToken ?? null);
    try {
        if (next) {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
        } else {
            localStorage.removeItem(STORAGE_KEY);
            localStorage.removeItem("educonnect.session");
        }
    } catch {
        /* storage disabled (private mode, quota) - the in-memory session still works */
    }
}

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

    // The storage copy follows the session, so a `setUser` (a renamed account, new
    // permissions from `/auth/me`) survives a reload. Writes made by `adoptSession`
    // below land first; this effect repeats them with the same value.
    useEffect(() => {
        if (!isClient) return;
        writeStoredSession(session);
    }, [session, isClient]);

    /**
     * Take on a whole session - login, switch account, switch school, logout.
     *
     * Order matters, and getting it wrong is what made a switch look broken:
     *
     * 1. **storage first.** `lib/api/client` reads the token from localStorage on
     *    every call, so anything that fires before this write is signed with the
     *    *previous* token - and is answered for the previous identity.
     * 2. then the state, so the UI re-renders as the new account.
     * 3. then `resetQueries`, which drops every cached page (no leak from the old
     *    identity) **and refetches what is mounted right now**. `clear()` alone
     *    empties the cache but leaves the visible page showing the data it had.
     *
     * A page that caches in plain `useState` instead of React Query is covered by
     * the `key` on `AppLayout`'s main area, which remounts on a change of
     * identity/school and therefore refetches too.
     */
    const adoptSession = useCallback(
        (next: Session | null) => {
            writeStoredSession(next);
            setSession(next);
            void queryClient.resetQueries({ type: "all" });
        },
        [queryClient],
    );

    const login = useCallback(
        async (identifier: string, password: string): Promise<User> => {
            const s = await loginUser(identifier, password);
            adoptSession(s);
            return s.user;
        },
        [adoptSession],
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
        adoptSession(null);
    }, [session, adoptSession]);

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

    /** Swap the whole session - the "switch account" / "switch school" path. */
    const switchSession = useCallback(
        (next: Session) => {
            // Same single path as a login: storage first, then the state, then a
            // reset that refetches what is on screen. Without it a switched session
            // kept showing the previous school's numbers until a page reload.
            adoptSession(next);
        },
        [adoptSession],
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
