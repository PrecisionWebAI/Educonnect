"use client";
import { createContext, useContext } from "react";
import type { Session, User } from "../types";

// ============================================================
// Auth context + hook (non-component exports live here so the
// provider file satisfies react-refresh). Components import
// `useAuth` from this module.
// ============================================================

export const STORAGE_KEY = "EduConnect.session";

export interface AuthContextValue {
    session: Session | null;
    user: User | null;
    isAuthed: boolean;
    isInitialized: boolean;
    login: (identifier: string, password: string) => Promise<User>;
    logout: () => Promise<void>;
    setUser: (user: User) => void;
    /**
     * Replace the whole session (token + user).
     *
     * Used by the super-admin "switch account" flow: the API hands back a token
     * for the account being viewed, and the previous user's cached queries must
     * not survive the swap - exactly like a fresh login.
     */
    switchSession: (session: Session) => void;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

export function useAuth(): AuthContextValue {
    const ctx = useContext(AuthContext);
    if (!ctx) throw new Error("useAuth must be used within AuthProvider");
    return ctx;
}
