"use client";

import React, { useSyncExternalStore } from "react";
import {
    getPreset,
    nextTheme,
    useTheme,
    type ResolvedTheme,
} from "@/providers/ThemeProvider";

interface ThemeToggleProps {
    className?: string;
    showLabel?: boolean;
}

const emptySubscribe = () => () => {};

/** Sun for light presets, moon for dark presets. */
function ModeIcon({ mode }: { mode: ResolvedTheme }) {
    if (mode === "dark") {
        return (
            <svg
                xmlns="http://www.w3.org/2000/svg"
                className="h-5 w-5 text-indigo-400 transition-transform duration-300 hover:-rotate-12"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth="2"
            >
                <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"
                />
            </svg>
        );
    }
    return (
        <svg
            xmlns="http://www.w3.org/2000/svg"
            className="h-5 w-5 text-amber-400 transition-transform duration-300 hover:rotate-45"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth="2"
        >
            <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"
            />
        </svg>
    );
}

/**
 * Single-button theme switcher — no dropdown. Each click advances one step
 * through the cycle: Light -> Pure Dark -> Dark -> Midnight Blue -> Light.
 */
export function ThemeToggle({ className = "", showLabel = false }: ThemeToggleProps) {
    const { theme, resolvedTheme, preset, setTheme } = useTheme();
    const mounted = useSyncExternalStore(
        emptySubscribe,
        () => true,
        () => false,
    );

    if (!mounted) {
        return (
            <button
                type="button"
                disabled
                className={`text-muted-foreground inline-flex items-center justify-center rounded-lg p-2 opacity-50 transition-colors ${className}`}
                aria-label="Loading theme toggle"
            >
                <span className="block h-5 w-5" />
            </button>
        );
    }

    const upcoming = getPreset(nextTheme(theme));

    return (
        <button
            type="button"
            onClick={() => setTheme(upcoming.id)}
            className={`text-muted-foreground hover:text-foreground hover:bg-surface-hover focus:ring-accent relative inline-flex items-center justify-center gap-2 rounded-lg p-2 transition-all duration-200 focus:ring-2 focus:outline-none ${className}`}
            aria-label={`Theme: ${preset.label}. Click to switch to ${upcoming.label}.`}
            title={`Theme: ${preset.label} — click for ${upcoming.label}`}
        >
            <ModeIcon mode={resolvedTheme} />
            {showLabel && <span className="text-sm font-medium">{preset.label}</span>}
        </button>
    );
}
