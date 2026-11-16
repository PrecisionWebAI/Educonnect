"use client";

import React, { createContext, useContext, useEffect, useSyncExternalStore } from "react";

/** Light or dark — what the DOM actually renders. */
export type ResolvedTheme = "light" | "dark";

/** The two supported appearance modes. */
export type Theme = "light" | "dark";

export interface ThemePreset {
    /** Stable id persisted in localStorage. */
    id: Theme;
    label: string;
    /** DOM class applied for this mode. */
    mode: ResolvedTheme;
}

/** Click order for the toggle. */
export const THEME_CYCLE: Theme[] = ["light", "dark"];

export const THEME_PRESETS: ThemePreset[] = [
    { id: "light", label: "Light", mode: "light" },
    { id: "dark", label: "Dark", mode: "dark" },
];

const PRESET_BY_ID = new Map<Theme, ThemePreset>(
    THEME_PRESETS.map((preset) => [preset.id, preset]),
);

const DEFAULT_PRESET: ThemePreset = THEME_PRESETS[0];

export function isTheme(value: unknown): value is Theme {
    return value === "light" || value === "dark";
}

/** Preset for a theme id, falling back to the default for unknown values. */
export function getPreset(theme: Theme): ThemePreset {
    return PRESET_BY_ID.get(theme) ?? DEFAULT_PRESET;
}

/** Next theme in the click cycle (wraps around at the end). */
export function nextTheme(theme: Theme): Theme {
    const index = THEME_CYCLE.indexOf(theme);
    return THEME_CYCLE[(index + 1) % THEME_CYCLE.length];
}

interface ThemeContextType {
    theme: Theme;
    resolvedTheme: ResolvedTheme;
    /** Metadata for the active theme (label + resolved mode). */
    preset: ThemePreset;
    setTheme: (theme: Theme) => void;
}

export const THEME_STORAGE_KEY = "educonnect-theme";

const themeListeners = new Set<() => void>();

function readStoredTheme(fallback: Theme): Theme {
    try {
        const saved = localStorage.getItem(THEME_STORAGE_KEY);
        if (saved === "pure-dark" || saved === "midnight-blue") {
            return "dark";
        }
        if (isTheme(saved)) {
            return saved;
        }
    } catch {
        // Ignore localStorage errors (private mode, SSR)
    }
    return fallback;
}

function subscribeTheme(callback: () => void) {
    themeListeners.add(callback);
    const handleStorage = (e: StorageEvent) => {
        if (e.key === THEME_STORAGE_KEY) {
            callback();
        }
    };
    window.addEventListener("storage", handleStorage);
    return () => {
        themeListeners.delete(callback);
        window.removeEventListener("storage", handleStorage);
    };
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export function ThemeProvider({
    children,
    defaultTheme = "light",
}: {
    children: React.ReactNode;
    defaultTheme?: Theme;
}) {
    const theme = useSyncExternalStore(
        subscribeTheme,
        () => readStoredTheme(defaultTheme),
        () => defaultTheme,
    );

    const preset = getPreset(theme);
    const resolvedTheme: ResolvedTheme = preset.mode;

    // Keep the DOM in sync with the two Tailwind theme variants.
    useEffect(() => {
        const root = document.documentElement;
        root.classList.toggle("dark", resolvedTheme === "dark");
        root.classList.toggle("light", resolvedTheme === "light");
        root.removeAttribute("data-theme");
    }, [theme, resolvedTheme]);

    const setTheme = (newTheme: Theme) => {
        try {
            localStorage.setItem(THEME_STORAGE_KEY, newTheme);
        } catch {
            // Ignore write errors
        }
        themeListeners.forEach((listener) => listener());
    };

    return (
        <ThemeContext.Provider value={{ theme, resolvedTheme, preset, setTheme }}>
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
