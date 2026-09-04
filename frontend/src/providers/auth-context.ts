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
    login: (identifier: string, password: string) => Promise<User>;
    logout: () => Promise<void>;
    setUser: (user: User) => void;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

export function useAuth(): AuthContextValue {
    const ctx = useContext(AuthContext);
    if (!ctx) throw new Error("useAuth must be used within AuthProvider");
    return ctx;
}
