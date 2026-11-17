"use client";

import { useEffect, useRef, useState } from "react";
import { ChevronDown } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { useApiQuery } from "@/lib/api/use-api-query";
import { errorMessage } from "@/lib/api/client";
import { hasPermission } from "@/lib/auth/rbac";
import { useAuth } from "@/providers/auth-context";
import { getSessionYears, openSessionYear, setCurrentSessionYear } from "@/services";

/**
 * The session year, in the top bar just before the theme toggle.
 *
 * Why it is here and not on a settings page: the year is **context**, like the theme.
 * Every screen that shows "this year" - the course plan, the leave balances, the
 * performance score - reads the current `academic_year` row, so switching it is a
 * change of what the whole application is looking at. A settings screen three clicks
 * away would make that feel like an edit rather than a switch.
 *
 * Two rights, two behaviours:
 *
 * * everybody with `settings.read` sees the year and where it is (it is printed on
 *   most screens, and hiding the control would only hide the label);
 * * only `academic_year.manage` gets "Open next session", because opening a year is
 *   the office's decision.
 *
 * Switching invalidates **every** query: the answer to "which year is current" is
 * baked into the data of half the app, and a stale cache would show last year's
 * chapters under this year's heading.
 */
export function SessionYearSelect({ className = "" }: { className?: string }) {
    const { user } = useAuth();
    const queryClient = useQueryClient();
    const [open, setOpen] = useState(false);
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState<unknown>(null);
    const box = useRef<HTMLDivElement | null>(null);

    const canManage = hasPermission(user?.permissions, "academic_year.manage");
    const query = useApiQuery(["session", "years"], getSessionYears);
    const years = query.data ?? [];
    const current = years.find((year) => year.isCurrent) ?? null;

    // Clicking anywhere else closes the menu - the same rule the account switcher
    // follows, so the two controls in this corner behave alike.
    useEffect(() => {
        if (!open) return;
        function onPointerDown(event: MouseEvent) {
            if (box.current && !box.current.contains(event.target as Node)) {
                setOpen(false);
            }
        }
        document.addEventListener("mousedown", onPointerDown);
        return () => document.removeEventListener("mousedown", onPointerDown);
    }, [open]);

    async function run(work: () => Promise<unknown>) {
        setBusy(true);
        setError(null);
        try {
            await work();
            await queryClient.invalidateQueries();
            setOpen(false);
        } catch (problem) {
            setError(problem);
        } finally {
            setBusy(false);
        }
    }

    /** The next year to open: one after the newest the school has. */
    function nextStartYear(): number {
        const starts = years
            .map((year) => Number(year.name.slice(0, 4)))
            .filter((value) => Number.isFinite(value));
        if (starts.length > 0) return Math.max(...starts) + 1;
        const today = new Date();
        return today.getMonth() >= 3 ? today.getFullYear() : today.getFullYear() - 1;
    }

    if (years.length === 0) {
        // Nothing opened yet (and no right to open one): the control prints nothing
        // rather than an empty dropdown. The first placement opens the row anyway.
        return null;
    }

    return (
        <div className="relative" ref={box}>
            <button
                type="button"
                onClick={() => setOpen((value) => !value)}
                className={className}
                aria-haspopup="menu"
                aria-expanded={open}
                title={
                    current === null
                        ? "No session is current - open or pick one"
                        : `Session ${current.name} (1 April - 31 March)`
                }
            >
                <span className="text-sm font-semibold">{current?.name ?? "No session"}</span>
                <ChevronDown size={14} />
            </button>

            {open && (
                <div className="app-navigation-panel absolute right-0 z-50 mt-2 w-72 p-2">
                    <p className="app-navigation-empty" style={{ margin: "0 0 0.5rem" }}>
                        The year every screen reads. A session runs 1 April to 31 March.
                    </p>
                    <ul>
                        {years.map((year) => (
                            <li key={year.id}>
                                <button
                                    type="button"
                                    disabled={busy || year.isCurrent}
                                    onClick={() => run(() => setCurrentSessionYear(year.id))}
                                    className="flex w-full items-center justify-between gap-2 rounded-md px-2 py-1.5 text-left text-sm disabled:opacity-60"
                                >
                                    <span>
                                        {year.name}
                                        <span
                                            className="ml-2 text-xs"
                                            style={{ color: "var(--muted)" }}
                                        >
                                            {year.startDate} - {year.endDate}
                                        </span>
                                    </span>
                                    {year.isCurrent && <span aria-label="Current">✓</span>}
                                </button>
                            </li>
                        ))}
                    </ul>

                    {canManage && (
                        <button
                            type="button"
                            disabled={busy}
                            onClick={() => run(() => openSessionYear(nextStartYear()))}
                            className="mt-2 w-full rounded-md px-2 py-1.5 text-left text-sm font-medium disabled:opacity-60"
                        >
                            + Open {nextStartYear()}-{String(nextStartYear() + 1).slice(-2)}
                        </button>
                    )}

                    {error !== null && (
                        <p className="mt-2 text-xs" style={{ color: "var(--danger, #b42318)" }}>
                            {errorMessage(error, "The session could not be changed.")}
                        </p>
                    )}
                </div>
            )}
        </div>
    );
}
