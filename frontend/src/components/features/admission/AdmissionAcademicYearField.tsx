"use client";

import { useId, useMemo, useState } from "react";

import { Button, Modal, Select } from "@/components/ui";
import { errorMessage } from "@/lib/api/client";
import {
    academicYearLabelForStart,
    academicYearRange,
    nextAcademicYearStartAfterCurrent,
} from "@/lib/academic-year/view";
import { useApiQuery } from "@/lib/api/use-api-query";
import { useAcademicYear } from "@/providers/academic-year-context";
import { getAcademicYears, openAcademicYear } from "@/services";
import type { AcademicYear } from "@/types";

/**
 * The admission's session picker.
 *
 * The form needs the same two facts the navbar shows - the running session and
 * the one after it - but choosing here must **not** switch the whole app's lens.
 * It only changes which `enrollment` the admission is written to. The next year
 * can be opened from here exactly like the navbar's "+ Open 2027-28" action; it
 * is created as a planned year, not made current.
 */
export default function AdmissionAcademicYearField({
    label,
    value,
    onChange,
    readOnly = false,
}: {
    label: string;
    value: string;
    onChange?: (yearId: string) => void;
    readOnly?: boolean;
}) {
    const { current, canManage, refresh } = useAcademicYear();
    const yearsQuery = useApiQuery(["academic-year", "years"], getAcademicYears, {
        enabled: canManage && Boolean(current),
    });
    const [busy, setBusy] = useState(false);
    const [notice, setNotice] = useState<string | null>(null);
    const [error, setError] = useState<unknown>(null);
    const [pendingYear, setPendingYear] = useState<AcademicYear | null>(null);
    const selectId = useId();

    const nextStart = nextAcademicYearStartAfterCurrent(current);
    const nextName = academicYearLabelForStart(nextStart);
    const years = useMemo(() => yearsQuery.data ?? [], [yearsQuery.data]);
    const nextYear = years.find((year) => year.name === nextName) ?? null;

    /** Only the running session and the one after it belong in this form. */
    const visibleYears = useMemo(() => {
        const rows: AcademicYear[] = [];
        if (current) rows.push(current);
        if (nextYear && nextYear.id !== current?.id) rows.push(nextYear);
        // A saved form may carry a year that is no longer in the two-item window
        // (for example a year opened earlier, then a new one became current).
        const selected = years.find((year) => year.id === value);
        if (selected && !rows.some((year) => year.id === selected.id)) {
            rows.push(selected);
        }
        return rows;
    }, [current, nextYear, value, years]);

    const selected = visibleYears.find((year) => year.id === value) ?? current ?? null;

    /** A session other than the running one must be confirmed before it sticks. */
    function chooseYear(yearId: string) {
        const chosen = visibleYears.find((year) => year.id === yearId) ?? null;
        if (!chosen) return;
        if (current && chosen.id !== current.id) {
            setPendingYear(chosen);
            return;
        }
        setNotice(null);
        setError(null);
        onChange?.(chosen.id);
    }

    async function openNextYear() {
        setBusy(true);
        setError(null);
        setNotice(null);
        try {
            const opened = await openAcademicYear(nextStart);
            // The current-year provider and this form's list share the same key
            // prefix, so one refresh makes the new planned year selectable.
            await refresh();
            setNotice(`${opened.name} is open. Select it above to admit in that session.`);
        } catch (cause) {
            setError(cause);
        } finally {
            setBusy(false);
        }
    }

    if (readOnly) {
        return (
            <div className="space-y-1.5">
                <span className="block text-sm font-medium">{label}</span>
                <p className={value ? "text-sm" : "text-muted-foreground text-sm"}>
                    {value ? (selected?.name ?? "—") : "—"}
                </p>
            </div>
        );
    }

    return (
        <div className="space-y-1.5">
            <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
                <label htmlFor={selectId} className="text-sm leading-none font-medium">
                    {label}
                </label>
                {selected ? (
                    <span className="text-muted-foreground text-xs">
                        *{academicYearRange(selected)}
                    </span>
                ) : null}
            </div>
            <Select
                id={selectId}
                aria-label={label}
                value={selected?.id ?? ""}
                onChange={(event) => chooseYear(event.target.value)}
                disabled={busy || visibleYears.length === 0}
            >
                {visibleYears.length === 0 ? <option value="">No academic year open</option> : null}
                {visibleYears.map((year) => (
                    <option key={year.id} value={year.id}>
                        {year.name}
                    </option>
                ))}
            </Select>

            {current && selected && selected.id !== current.id ? (
                <p className="text-muted-foreground text-xs">
                    Recorded for this future session; today&apos;s class placement stays in the
                    current year.
                </p>
            ) : null}

            {canManage && current && !nextYear && !yearsQuery.isLoading ? (
                <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    loading={busy}
                    onClick={() => void openNextYear()}
                >
                    + Open {nextName}
                </Button>
            ) : null}

            {notice ? (
                <p className="text-primary text-xs" role="status">
                    {notice}
                </p>
            ) : null}

            {error !== null ? (
                <p className="text-xs text-red-600 dark:text-red-400" role="alert">
                    {errorMessage(error, "The next academic year could not be opened.")}
                </p>
            ) : null}

            <Modal
                open={pendingYear !== null}
                title="Confirm academic year"
                onClose={() => setPendingYear(null)}
            >
                <div className="space-y-4">
                    <p className="text-sm">
                        Are you sure you want to take admission in academic year{" "}
                        <strong>{pendingYear ? academicYearRange(pendingYear) : ""}</strong>?
                    </p>
                    {pendingYear ? (
                        <p className="text-muted-foreground text-sm">
                            This admission will be recorded in {pendingYear.name}. The
                            student&apos;s current class placement stays in{" "}
                            {current?.name ?? "the current year"}.
                        </p>
                    ) : null}
                    <div className="flex justify-end gap-2">
                        <Button
                            type="button"
                            variant="outline"
                            onClick={() => setPendingYear(null)}
                        >
                            Cancel
                        </Button>
                        <Button
                            type="button"
                            onClick={() => {
                                if (!pendingYear) return;
                                setNotice(null);
                                setError(null);
                                onChange?.(pendingYear.id);
                                setPendingYear(null);
                            }}
                        >
                            Yes, continue
                        </Button>
                    </div>
                </div>
            </Modal>
        </div>
    );
}
