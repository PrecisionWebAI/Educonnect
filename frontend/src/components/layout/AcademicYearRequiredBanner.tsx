"use client";

import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { Button } from "@/components/ui";
import { errorMessage } from "@/lib/api/client";
import { useAcademicYear } from "@/providers/academic-year-context";
import { useAuth } from "@/providers/auth-context";
import { openAcademicYear } from "@/services";

/**
 * The one "no academic year" notice used by data pages.
 *
 * The navbar stays the place to switch years; this banner only explains why a
 * write is blocked and gives a manager the same server-side bootstrap the navbar
 * uses. Non-managers get the read-only sentence and no button.
 */
export default function AcademicYearRequiredBanner({
    className = "",
}: {
    className?: string;
}) {
    const { current, isLoading, canManage, refresh } = useAcademicYear();
    const { user } = useAuth();
    const queryClient = useQueryClient();
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState<unknown>(null);

    if (current || isLoading) return null;

    // A platform session without a school cannot own an academic year. The
    // school-scope banner is the correct prompt; do not offer a broken CTA.
    if (!user?.schoolId) {
        return (
            <div
                role="status"
                className={`border-amber-300/70 bg-amber-50 text-amber-900 dark:border-amber-400/30 dark:bg-amber-500/10 dark:text-amber-200 rounded-lg border p-4 text-sm ${className}`}
            >
                <p className="font-semibold">Select a school first.</p>
                <p className="mt-1 opacity-80">
                    Academic years belong to a school. Choose a school from the
                    selector at the top of the page.
                </p>
            </div>
        );
    }

    async function openCurrentYear() {
        setBusy(true);
        setError(null);
        try {
            await openAcademicYear();
            await queryClient.invalidateQueries();
            await refresh();
        } catch (problem) {
            setError(problem);
        } finally {
            setBusy(false);
        }
    }

    return (
        <div
            role="status"
            className={`border-amber-300/70 bg-amber-50 text-amber-900 dark:border-amber-400/30 dark:bg-amber-500/10 dark:text-amber-200 rounded-lg border p-4 text-sm ${className}`}
        >
            <p className="font-semibold">No academic year is open.</p>
            <p className="mt-1 opacity-80">
                {canManage
                    ? "Open the current academic year before adding or changing data. The year is also available from the control below the school name."
                    : "Ask the school admin to open the current academic year before adding or changing data."}
            </p>
            {canManage && (
                <Button
                    size="sm"
                    className="mt-3"
                    loading={busy}
                    disabled={busy}
                    onClick={() => void openCurrentYear()}
                >
                    Open current academic year
                </Button>
            )}
            {error !== null && (
                <p className="mt-2 text-xs text-red-700 dark:text-red-300" role="alert">
                    {errorMessage(error, "Could not open the academic year.")}
                </p>
            )}
        </div>
    );
}
