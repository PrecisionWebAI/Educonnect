"use client";

import { useState } from "react";
import { ArrowUpRight, ChevronDown, GraduationCap, UsersRound } from "lucide-react";
import Link from "next/link";
import type { ClassGroup, ClassSectionCard } from "@/types";

export const STAGE_LABELS: Record<string, string> = {
    pre_primary: "Pre-primary",
    primary: "Primary",
    middle: "Middle",
    secondary: "Secondary",
    senior_secondary: "Senior secondary",
};

export const STAGE_ORDER = ["pre_primary", "primary", "middle", "secondary", "senior_secondary"];

function formatPercent(value: number | null): string {
    if (value === null) return "—";
    return `${new Intl.NumberFormat(undefined, { maximumFractionDigits: 1 }).format(value)}%`;
}

function summarizeSections(sections: ClassSectionCard[]) {
    const students = sections.reduce((total, section) => total + section.strength, 0);
    const attendanceSections = sections.filter(
        (section) => section.attendancePercent !== null && section.strength > 0,
    );
    const attendanceStudents = attendanceSections.reduce(
        (total, section) => total + section.strength,
        0,
    );
    const attendance =
        attendanceStudents > 0
            ? attendanceSections.reduce(
                  (total, section) => total + (section.attendancePercent ?? 0) * section.strength,
                  0,
              ) / attendanceStudents
            : null;

    return { students, attendance };
}

function SectionLink({ group, section }: { group: ClassGroup; section: ClassSectionCard }) {
    return (
        <Link
            href={`/dashboard/classroom/${section.sectionId}`}
            aria-label={`Open ${group.className}, section ${section.sectionName}`}
            className="classroom-section-mini-row group"
        >
            <span className="classroom-section-initial" aria-hidden="true">
                {section.sectionName.slice(0, 1)}
            </span>
            <span className="min-w-0 flex-1">
                <span className="block truncate text-sm font-semibold">
                    Section {section.sectionName}
                </span>
                <span className="text-muted-foreground mt-0.5 block truncate text-xs">
                    {section.classTeacher ?? "Class teacher not assigned"}
                </span>
            </span>
            <span className="classroom-section-mini-stats">
                <span>
                    {section.strength.toLocaleString()}{" "}
                    {section.strength === 1 ? "student" : "students"}
                </span>
                <span>
                    {section.attendancePercent === null
                        ? "No attendance"
                        : `${formatPercent(section.attendancePercent)} attendance`}
                </span>
                {section.attendanceDate && (
                    <span>{section.presentToday.toLocaleString()} present today</span>
                )}
            </span>
            <ArrowUpRight
                aria-hidden="true"
                className="text-muted-foreground group-hover:text-primary size-4 shrink-0 transition group-hover:translate-x-0.5 group-hover:-translate-y-0.5"
            />
        </Link>
    );
}

function ClassTile({
    group,
    isSelected,
    onSelect,
}: {
    group: ClassGroup;
    isSelected: boolean;
    onSelect: () => void;
}) {
    const summary = summarizeSections(group.sections);
    const attendancePercent =
        summary.attendance === null ? null : Math.max(0, Math.min(100, summary.attendance));
    const visibleSectionCount = group.sections.length;
    const sectionCountLabel =
        visibleSectionCount === group.sectionCount
            ? `${group.sectionCount} ${group.sectionCount === 1 ? "section" : "sections"}`
            : `${visibleSectionCount} of ${group.sectionCount} sections`;
    const sectionsId = `class-sections-${group.classroomId}`;

    return (
        <article
            className="classroom-class-tile"
            data-stage={group.stage}
            data-selected={isSelected}
        >
            <button
                type="button"
                aria-expanded={isSelected}
                aria-controls={sectionsId}
                onClick={onSelect}
                className="classroom-class-tile-trigger"
            >
                <span className="classroom-class-tile-heading">
                    <span className="classroom-class-tile-icon" aria-hidden="true">
                        <GraduationCap className="size-5" />
                    </span>
                    <span className="min-w-0 flex-1">
                        <span className="classroom-class-tile-stage">
                            {STAGE_LABELS[group.stage] ?? group.stage}
                        </span>
                        <span className="block truncate text-lg font-semibold tracking-tight">
                            {group.className}
                        </span>
                    </span>
                    <span
                        className="classroom-attendance-ring"
                        role="img"
                        aria-label={
                            attendancePercent === null
                                ? "Average attendance unavailable"
                                : `Average attendance ${formatPercent(attendancePercent)}`
                        }
                        style={{
                            background:
                                attendancePercent === null
                                    ? "conic-gradient(var(--muted-surface) 0 100%)"
                                    : `conic-gradient(var(--classroom-stage-accent) 0 ${attendancePercent}%, var(--muted-surface) ${attendancePercent}% 100%)`,
                        }}
                    >
                        <span>{formatPercent(attendancePercent)}</span>
                    </span>
                </span>

                <span className="classroom-class-tile-summary">
                    <span>
                        <UsersRound aria-hidden="true" className="size-3.5" />
                        {summary.students.toLocaleString()} students
                    </span>
                    <span>{sectionCountLabel}</span>
                </span>

                <span className="classroom-section-chips" aria-hidden="true">
                    {group.sections.slice(0, 3).map((section) => (
                        <span className="classroom-section-chip" key={section.sectionId}>
                            {section.sectionName}
                        </span>
                    ))}
                    {visibleSectionCount > 3 && (
                        <span className="classroom-section-chip classroom-section-chip-more">
                            +{visibleSectionCount - 3}
                        </span>
                    )}
                </span>

                <span className="classroom-class-tile-action">
                    {isSelected ? "Hide sections" : "Explore sections"}
                    <ChevronDown
                        aria-hidden="true"
                        className={`size-4 transition-transform duration-200 ${
                            isSelected ? "rotate-180" : ""
                        }`}
                    />
                </span>
            </button>

            <div
                id={sectionsId}
                hidden={!isSelected}
                className={`classroom-section-mini-list ${isSelected ? "grid" : "hidden"}`}
            >
                {group.sections.map((section) => (
                    <SectionLink key={section.sectionId} group={group} section={section} />
                ))}
            </div>
        </article>
    );
}

export default function ClassroomCards({
    groups,
    activeStage,
}: {
    groups: ClassGroup[];
    activeStage: string;
}) {
    const [selectedClassId, setSelectedClassId] = useState<string | null>(null);

    const groupsByStage = new Map<string, ClassGroup[]>();
    for (const group of groups) {
        const stageGroups = groupsByStage.get(group.stage) ?? [];
        stageGroups.push(group);
        groupsByStage.set(group.stage, stageGroups);
    }

    const orderedStages = [...groupsByStage.entries()].sort(([stageA], [stageB]) => {
        const indexA = STAGE_ORDER.indexOf(stageA);
        const indexB = STAGE_ORDER.indexOf(stageB);
        return (
            (indexA < 0 ? STAGE_ORDER.length : indexA) -
                (indexB < 0 ? STAGE_ORDER.length : indexB) || stageA.localeCompare(stageB)
        );
    });

    return (
        <div className="space-y-6">
            {orderedStages.map(([stage, stageGroups]) => {
                const stageSections = stageGroups.reduce(
                    (total, group) => total + group.sections.length,
                    0,
                );
                const stageStudents = stageGroups.reduce(
                    (total, group) =>
                        total +
                        group.sections.reduce(
                            (sectionTotal, section) => sectionTotal + section.strength,
                            0,
                        ),
                    0,
                );

                return (
                    <section
                        key={stage}
                        className="classroom-campus-stage"
                        data-stage={stage}
                        aria-labelledby={`classroom-stage-${stage}`}
                    >
                        <header
                            className="classroom-campus-stage-heading"
                            data-selected={activeStage === stage}
                        >
                            <span className="classroom-stage-filter-dot" aria-hidden="true" />
                            <h3 id={`classroom-stage-${stage}`} className="font-semibold">
                                {STAGE_LABELS[stage] ?? stage}
                            </h3>
                            <span className="classroom-campus-stage-meta">
                                {stageGroups.length}{" "}
                                {stageGroups.length === 1 ? "class" : "classes"} · {stageSections}{" "}
                                {stageSections === 1 ? "section" : "sections"} ·{" "}
                                {stageStudents.toLocaleString()} students
                            </span>
                        </header>
                        <div className="grid items-start gap-3 sm:grid-cols-2 2xl:grid-cols-3">
                            {[...stageGroups]
                                .sort(
                                    (a, b) =>
                                        a.level - b.level ||
                                        a.className.localeCompare(b.className, undefined, {
                                            numeric: true,
                                            sensitivity: "base",
                                        }),
                                )
                                .map((group) => (
                                    <ClassTile
                                        key={group.classroomId}
                                        group={group}
                                        isSelected={group.classroomId === selectedClassId}
                                        onSelect={() =>
                                            setSelectedClassId((current) =>
                                                current === group.classroomId
                                                    ? null
                                                    : group.classroomId,
                                            )
                                        }
                                    />
                                ))}
                        </div>
                    </section>
                );
            })}
        </div>
    );
}
