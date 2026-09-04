"use client";

import React, { createContext, useContext, useEffect, useSyncExternalStore } from "react";

export type Theme = "light" | "dark" | "system";
export type ResolvedTheme = "light" | "dark";

interface ThemeContextType {
    theme: Theme;
    resolvedTheme: ResolvedTheme;
    setTheme: (theme: Theme) => void;
}

const STORAGE_KEY = "educonnect-theme";

const themeListeners = new Set<() => void>();

function subscribeTheme(callback: () => void) {
    themeListeners.add(callback);
    const handleStorage = (e: StorageEvent) => {
        if (e.key === STORAGE_KEY) {
            callback();
        }
    };
    window.addEventListener("storage", handleStorage);
    return () => {
        themeListeners.delete(callback);
        window.removeEventListener("storage", handleStorage);
    };
}

function subscribeSystemTheme(callback: () => void) {
    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
    mediaQuery.addEventListener("change", callback);
    return () => {
        mediaQuery.removeEventListener("change", callback);
    };
}

function getSystemThemeSnapshot(): boolean {
    return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export function ThemeProvider({
    children,
    defaultTheme = "system",
}: {
    children: React.ReactNode;
    defaultTheme?: Theme;
}) {
    const theme = useSyncExternalStore(
        subscribeTheme,
        () => {
            try {
                const saved = localStorage.getItem(STORAGE_KEY) as Theme | null;
                if (saved === "light" || saved === "dark" || saved === "system") {
                    return saved;
                }
            } catch {
                // Ignore localStorage errors (e.g. incognito/SSR)
            }
            return defaultTheme;
        },
        () => defaultTheme,
    );

    const isSystemDark = useSyncExternalStore(
        subscribeSystemTheme,
        getSystemThemeSnapshot,
        () => defaultTheme === "dark",
    );

    const resolvedTheme: ResolvedTheme =
        theme === "system" ? (isSystemDark ? "dark" : "light") : theme;

    // Synchronize the DOM with the resolved theme
    useEffect(() => {
        const root = document.documentElement;
        if (resolvedTheme === "dark") {
            root.classList.add("dark");
            root.classList.remove("light");
        } else {
            root.classList.add("light");
            root.classList.remove("dark");
        }
    }, [resolvedTheme]);

    const setTheme = (newTheme: Theme) => {
        try {
            localStorage.setItem(STORAGE_KEY, newTheme);
        } catch {
            // Ignore write errors
        }
        themeListeners.forEach((listener) => listener());
    };

    return (
        <ThemeContext.Provider value={{ theme, resolvedTheme, setTheme }}>
            {children}
        </ThemeContext.Provider>
    );
}

export function useTheme() {
    const context = useContext(ThemeContext);
    if (!context) {
        throw new Error("useTheme must be used within a ThemeProvider");
    }
    return context;
}
