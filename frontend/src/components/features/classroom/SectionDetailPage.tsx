"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Badge, Select, Spinner } from "@/components/ui";
import { getSectionDetail, getTeacherOptions, setClassTeacher } from "@/services";
import { useApiQuery } from "@/lib/api/use-api-query";

// One class-section - the card's own page: the class it is, who runs it, and the
// same figures the grid card carries. Attendance, timetable, homework, diary,
// marks and the subject list live in their own modules, so they are not repeated
// here as tabs.

const STAGE_LABELS: Record<string, string> = {
    pre_primary: "Pre-primary",
    primary: "Primary",
    middle: "Middle",
    secondary: "Secondary",
    senior_secondary: "Senior secondary",
};

/** `90.5` -> `90.5%`, `null` -> `—`. */
function pct(value: number | null): string {
    return value === null ? "—" : `${value}%`;
}

/** Compact rupees: 425000 -> `₹4.3L`. */
function inr(value: number | null): string {
    if (value === null) return "—";
    if (value >= 100000) return `₹${(value / 100000).toFixed(1)}L`;
    if (value >= 1000) return `₹${Math.round(value / 1000)}K`;
    return `₹${Math.round(value)}`;
}

/** One glass stat in the header strip. */
function Stat({ label, value }: { label: string; value: string }) {
    return (
        <div className="glass-tile rounded-xl px-3 py-2">
            <div className="text-muted-foreground text-[0.68rem] font-medium tracking-wide uppercase">
                {label}
            </div>
            <div className="truncate text-sm font-semibold">{value}</div>
        </div>
    );
}

export default function SectionDetailPage() {
    const params = useParams<{ sectionId: string }>();
    const sectionId = params?.sectionId ?? "";
    const query = useApiQuery(
        ["classroom", "section", sectionId],
        () => getSectionDetail(sectionId),
        { enabled: Boolean(sectionId) },
    );
    const teachersQuery = useApiQuery(["classroom", "teachers"], getTeacherOptions);
    const queryClient = useQueryClient();
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const detail = query.data;
    const teachers = teachersQuery.data ?? [];

    /** Run the assignment, then re-read the section and the grid behind it. */
    async function assign(action: () => Promise<void>) {
        setSaving(true);
        setError(null);
        try {
            await action();
            await queryClient.invalidateQueries({ queryKey: ["classroom"] });
        } catch (cause) {
            setError(
                cause instanceof Error ? cause.message : "Could not save the change.",
            );
        } finally {
            setSaving(false);
        }
    }

    return (
        <div className="glass-backdrop min-h-[70vh] rounded-3xl p-4 sm:p-6">
            <Link
                href="/dashboard/classroom"
                className="text-muted-foreground mb-4 inline-block text-sm hover:underline"
            >
                ← All classrooms
            </Link>

            {query.isPending ? (
                <Spinner />
            ) : !detail ? (
                <div className="glass-tile rounded-2xl p-8 text-center">
                    <p className="text-muted-foreground text-sm">
                        This class-section could not be loaded.
                    </p>
                </div>
            ) : (
                <>
                    <header className="mb-5 flex flex-wrap items-center gap-3">
                        <h1 className="text-2xl font-semibold">{detail.classLabel}</h1>
                        <Badge tone="violet">
                            {STAGE_LABELS[detail.stage] ?? detail.stage}
                        </Badge>
                        <span className="text-muted-foreground text-sm">
                            {detail.classTeacher?.name
                                ? `Class teacher: ${detail.classTeacher.name}`
                                : "No class teacher assigned"}
                            {detail.classTeacher?.email
                                ? ` · ${detail.classTeacher.email}`
                                : ""}
                            {detail.classTeacher?.phone
                                ? ` · ${detail.classTeacher.phone}`
                                : ""}
                        </span>
                    </header>

                    <div className="mb-5 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
                        <Stat label="Students" value={String(detail.strength)} />
                        <Stat
                            label="Boys / Girls"
                            value={`${detail.boys} / ${detail.girls}`}
                        />
                        <Stat label="Attendance" value={pct(detail.attendancePercent)} />
                        <Stat
                            label="Course complete"
                            value={pct(detail.syllabusPercent)}
                        />
                        <Stat
                            label="Fees received"
                            value={`${inr(detail.feesCollected)} / ${inr(detail.feesExpected)}`}
                        />
                        <Stat label="Fees %" value={pct(detail.feesPercent)} />
                    </div>

                    <div className="glass-tile flex flex-wrap items-center gap-3 rounded-2xl p-3">
                        <div className="text-sm font-semibold">Class teacher</div>
                        <Select
                            value={detail.classTeacher?.employeeId ?? ""}
                            disabled={saving}
                            onChange={(e) =>
                                void assign(() =>
                                    setClassTeacher(sectionId, e.target.value || null),
                                )
                            }
                            aria-label="Class teacher"
                        >
                            <option value="">— nobody yet —</option>
                            {teachers.map((teacher) => (
                                <option
                                    key={teacher.employeeId}
                                    value={teacher.employeeId}
                                >
                                    {teacher.name}
                                </option>
                            ))}
                        </Select>
                        {saving && <Spinner size="sm" />}
                        {error && <span className="text-sm text-red-500">{error}</span>}
                    </div>
                </>
            )}
        </div>
    );
}
