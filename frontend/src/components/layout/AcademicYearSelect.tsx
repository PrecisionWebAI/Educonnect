"use client";

import { useEffect, useRef, useState } from "react";
import { ChevronDown } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";

import { Button, Modal } from "@/components/ui";
import { errorMessage } from "@/lib/api/client";
import { useApiQuery } from "@/lib/api/use-api-query";
import {
    academicYearChipState,
    academicYearLabel,
    academicYearLabelForStart,
    academicYearRange,
    nextAcademicYearStartAfterCurrent,
} from "@/lib/academic-year/view";
import { useAcademicYear } from "@/providers/academic-year-context";
import {
    getAcademicYears,
    openAcademicYear,
    setCurrentAcademicYear,
} from "@/services";
import type { AcademicYear } from "@/types";

/**
 * The academic year, a plain one-line label under the school name.
 *
 * It is context like the theme: every screen that says "this year" reads the same
 * `academic_year` row. The chip is always visible, including when the school has not
 * opened one (`Academic year not set`), because hiding it turned a setup gap into a
 * dead end.
 *
 * Reading the current year is auth-only. The full history is fetched for a manager
 * so the native dropdown can show every opened year; opening/switching is
 * `academic_year.manage` plus a role senior to the principal (the server enforces
 * both). A switch asks for confirmation before it changes every screen's context.
 *
 * Switching invalidates **every** query: the answer to "which year is current" is
 * baked into half the app's data, and a stale cache would show last year's chapters
 * under this year's heading.
 */
export function AcademicYearSelect({ className = "" }: { className?: string }) {
    const queryClient = useQueryClient();
    const { current, isLoading, canManage, refresh } = useAcademicYear();
    const [open, setOpen] = useState(false);
    const [pending, setPending] = useState<AcademicYear | null>(null);
    const [notice, setNotice] = useState<string | null>(null);
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState<unknown>(null);
    const box = useRef<HTMLDivElement | null>(null);

    // The native select mirrors the platform's other dropdowns. Managers need the
    // full history even while the menu is closed, so the list loads with the control.
    const yearsQuery = useApiQuery(["academic-year", "years"], getAcademicYears, {
        enabled: canManage,
    });
    const years = yearsQuery.data ?? [];
    const options = years.length > 0 ? years : current ? [current] : [];
    const nextStart = nextAcademicYearStartAfterCurrent(current);
    const nextName = academicYearLabelForStart(nextStart);
    const nextAlreadyOpen = options.some((year) => year.name === nextName);
    const nextAllowed = !nextAlreadyOpen;
    const state = academicYearChipState(current, canManage);

    useEffect(() => {
        if (!open) return;
        function onPointerDown(event: MouseEvent) {
            if (box.current && !box.current.contains(event.target as Node)) {
                setOpen(false);
                setNotice(null);
            }
        }
        function onKeyDown(event: KeyboardEvent) {
            if (event.key === "Escape") {
                setOpen(false);
                setNotice(null);
            }
        }
        document.addEventListener("mousedown", onPointerDown);
        document.addEventListener("keydown", onKeyDown);
        return () => {
            document.removeEventListener("mousedown", onPointerDown);
            document.removeEventListener("keydown", onKeyDown);
        };
    }, [open]);

    async function run(work: () => Promise<unknown>) {
        setBusy(true);
        setError(null);
        setNotice(null);
        try {
            await work();
            await queryClient.invalidateQueries();
            await refresh();
            setOpen(false);
            setPending(null);
        } catch (problem) {
            setError(problem);
        } finally {
            setBusy(false);
        }
    }

    function choose(year: AcademicYear) {
        if (year.isCurrent) {
            setOpen(false);
            return;
        }
        setError(null);
        setNotice(null);
        setOpen(false);
        setPending(year);
    }

    function openNextYear() {
        if (!nextAllowed) {
            setNotice(
                `${nextName} is already open. Only one year can be added after ${
                    current?.name ?? "the current year"
                }.`,
            );
            return;
        }
        void run(() => openAcademicYear(nextStart));
    }

    const title = current
        ? `Academic year ${current.name}`
        : canManage
          ? "Academic year not set - open one"
          : "Academic year not set - ask the school admin";

    return (
        <>
            <div className={`relative min-w-0 ${className}`} ref={box}>
                <button
                    type="button"
                    onClick={() => setOpen((value) => !value)}
                    className={`app-academic-year-trigger ${
                        state === "current" ? "" : "is-missing"
                    }`}
                    aria-haspopup="listbox"
                    aria-expanded={open}
                    aria-label={title}
                    title={title}
                >
                    <span>
                        {isLoading && !current
                            ? "Academic year"
                            : academicYearLabel(current)}
                    </span>
                    <ChevronDown size={13} aria-hidden="true" />
                </button>

                {open && (
                    <div className="app-navigation-panel app-academic-year-menu absolute left-0 z-50 mt-2 w-64 p-2">
                        {!canManage && (
                            <p className="app-navigation-empty px-2 py-1">
                                Ask the school admin to change the academic year.
                            </p>
                        )}

                        {canManage && (
                            <ul className="space-y-0.5">
                                {options.map((year) => (
                                    <li key={year.id}>
                                        <button
                                            type="button"
                                            disabled={busy}
                                            onClick={() => choose(year)}
                                            className="app-academic-year-option"
                                            aria-current={year.isCurrent ? "true" : undefined}
                                        >
                                            <span>
                                                {year.name}
                                                {year.isCurrent ? " (current)" : ""}
                                            </span>
                                            <span className="app-academic-year-dates">
                                                {academicYearRange(year)}
                                            </span>
                                        </button>
                                    </li>
                                ))}
                                {isLoading && options.length === 0 && (
                                    <li className="app-navigation-empty px-2 py-1">
                                        Loading academic years…
                                    </li>
                                )}
                            </ul>
                        )}

                        {canManage && (
                            <button
                                type="button"
                                onClick={openNextYear}
                                className={`app-academic-year-add ${
                                    nextAllowed ? "" : "is-disabled"
                                }`}
                                aria-disabled={!nextAllowed}
                                title={
                                    nextAllowed
                                        ? `Open ${nextName} as the next academic year`
                                        : `Only one year can be added after ${
                                              current?.name ?? "the current year"
                                          }`
                                }
                            >
                                + Open {nextName}
                            </button>
                        )}

                        {notice && (
                            <p className="app-academic-year-notice" role="status">
                                {notice}
                            </p>
                        )}

                        {error !== null && pending === null && (
                            <p className="app-academic-year-notice is-error" role="alert">
                                {errorMessage(
                                    error,
                                    "The academic year could not be changed.",
                                )}
                            </p>
                        )}
                    </div>
                )}
            </div>

            <Modal
                open={pending !== null}
                title="Switch academic year?"
                onClose={() => {
                    if (!busy) setPending(null);
                }}
            >
                <div className="space-y-4">
                    <p className="text-muted-foreground text-sm">
                        {current ? `The school is showing ${current.name}. ` : ""}
                        Switching to <strong>{pending?.name}</strong> changes the data
                        every screen reads. You can switch back at any time.
                    </p>
                    {error !== null && (
                        <p className="text-sm text-red-600 dark:text-red-400" role="alert">
                            {errorMessage(error, "The academic year could not be changed.")}
                        </p>
                    )}
                    <div className="flex justify-end gap-2">
                        <Button
                            variant="outline"
                            onClick={() => setPending(null)}
                            disabled={busy}
                        >
                            Cancel
                        </Button>
                        <Button
                            loading={busy}
                            disabled={busy}
                            onClick={() =>
                                pending &&
                                run(() => setCurrentAcademicYear(pending.id))
                            }
                        >
                            Switch to {pending?.name}
                        </Button>
                    </div>
                </div>
            </Modal>
        </>
    );
}
