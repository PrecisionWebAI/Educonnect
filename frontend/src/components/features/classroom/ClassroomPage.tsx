"use client";

import { useMemo, useState } from "react";
import { BookOpen, Layers, Search, School, TrendingUp, UsersRound, X } from "lucide-react";
import { Input, Spinner } from "@/components/ui";
import RoleGuard from "@/components/auth/RoleGuard";
import { pct } from "@/lib/format";
import ClassroomCards, { STAGE_LABELS, STAGE_ORDER } from "./ClassroomCards";
import TeacherClassroom from "./TeacherClassroom";
import { useClassroomOverview } from "./useClassroomOverview";

function SchoolClassroom() {
    const { groups, loading, error, hasData } = useClassroomOverview();
    const [search, setSearch] = useState("");
    const [stageFilter, setStageFilter] = useState("all");
    const errorMessage = error instanceof Error ? error.message : "Please try again in a moment.";

    const totals = useMemo(() => {
        const sections = groups.flatMap((group) => group.sections);
        const attendanceSections = sections.filter(
            (section) => section.attendancePercent !== null && section.strength > 0,
        );
        const attendanceStudents = attendanceSections.reduce(
            (sum, section) => sum + section.strength,
            0,
        );
        const weightedAttendance =
            attendanceStudents > 0
                ? attendanceSections.reduce(
                      (sum, section) => sum + (section.attendancePercent ?? 0) * section.strength,
                      0,
                  ) / attendanceStudents
                : null;

        return {
            classCount: groups.length,
            sectionCount: sections.length,
            studentCount: groups.reduce((sum, group) => sum + group.strength, 0),
            weightedAttendance,
        };
    }, [groups]);

    const stageOptions = useMemo(
        () =>
            [...new Set(groups.map((group) => group.stage))].sort((a, b) => {
                const aIndex = STAGE_ORDER.indexOf(a);
                const bIndex = STAGE_ORDER.indexOf(b);
                return (
                    (aIndex < 0 ? STAGE_ORDER.length : aIndex) -
                    (bIndex < 0 ? STAGE_ORDER.length : bIndex)
                );
            }),
        [groups],
    );

    const visibleGroups = useMemo(() => {
        const query = search.trim().toLowerCase();

        return groups
            .filter((group) => stageFilter === "all" || group.stage === stageFilter)
            .map((group) => {
                const classMatches =
                    !query ||
                    [group.className, STAGE_LABELS[group.stage] ?? group.stage].some((value) =>
                        value.toLowerCase().includes(query),
                    );
                const sections = group.sections.filter(
                    (section) =>
                        classMatches ||
                        [section.sectionName, section.classTeacher ?? ""].some((value) =>
                            value.toLowerCase().includes(query),
                        ),
                );

                return { ...group, sections };
            })
            .filter((group) => group.sections.length > 0);
    }, [groups, search, stageFilter]);

    const visibleSectionCount = visibleGroups.reduce(
        (sum, group) => sum + group.sections.length,
        0,
    );
    const visibleStudentCount = visibleGroups.reduce(
        (sum, group) =>
            sum + group.sections.reduce((sectionSum, section) => sectionSum + section.strength, 0),
        0,
    );

    const stats = [
        {
            label: "Classes",
            value: totals.classCount.toLocaleString(),
            detail: "Across your school",
            accent: "people",
            icon: <School aria-hidden="true" className="size-5" />,
        },
        {
            label: "Sections",
            value: totals.sectionCount.toLocaleString(),
            detail: "Ready to explore",
            accent: "services",
            icon: <Layers aria-hidden="true" className="size-5" />,
        },
        {
            label: "Students",
            value: totals.studentCount.toLocaleString(),
            detail: "Enrolled across classes",
            accent: "operations",
            icon: <UsersRound aria-hidden="true" className="size-5" />,
        },
        {
            label: "Average attendance",
            value: pct(totals.weightedAttendance),
            detail:
                totals.weightedAttendance === null
                    ? "No registers recorded yet"
                    : "Weighted by class size",
            accent: "dashboard",
            icon: <TrendingUp aria-hidden="true" className="size-5" />,
        },
    ];

    return (
        <div className="classroom-page space-y-5 sm:space-y-6">
            <section className="classroom-hero relative overflow-hidden rounded-3xl p-5 sm:p-7">
                <div className="relative flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between">
                    <div className="max-w-3xl">
                        <div className="classroom-hero-kicker mb-3">
                            <School aria-hidden="true" className="size-3.5" />
                            School overview
                        </div>
                        <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
                            Classrooms, at a glance
                        </h1>
                        <p className="mt-2 max-w-2xl text-sm leading-relaxed sm:text-base">
                            Find a class quickly, see how each section is progressing, and open its
                            students, attendance, and learning tools.
                        </p>
                    </div>
                    <div className="classroom-hero-highlight">
                        <span className="classroom-hero-highlight-icon">
                            <Layers aria-hidden="true" className="size-5" />
                        </span>
                        <div>
                            <p className="text-xs font-medium">Learning spaces</p>
                            <div className="flex items-baseline gap-1.5">
                                <span className="text-2xl leading-tight font-semibold">
                                    {loading || (error && !hasData)
                                        ? "—"
                                        : totals.sectionCount.toLocaleString()}
                                </span>
                                <span className="text-xs">sections</span>
                            </div>
                            <p className="text-xs">
                                {loading || (error && !hasData)
                                    ? "Overview unavailable"
                                    : `Across ${totals.classCount} classes`}
                            </p>
                        </div>
                    </div>
                </div>
            </section>

            {loading ? (
                <div className="glass-tile flex min-h-40 items-center justify-center rounded-2xl">
                    <Spinner />
                </div>
            ) : error && !hasData ? (
                <div role="alert" className="glass-tile rounded-2xl border border-red-500/20 p-5">
                    <h2 className="font-semibold">Classrooms could not be loaded</h2>
                    <p className="text-muted-foreground mt-1 text-sm">{errorMessage}</p>
                </div>
            ) : (
                <>
                    {error && hasData && (
                        <div
                            role="alert"
                            className="glass-tile rounded-2xl border border-amber-500/20 px-4 py-3 text-sm"
                        >
                            Some classroom data could not be refreshed. Showing the most recently
                            loaded information.
                            <span className="text-muted-foreground mt-1 block text-xs">
                                {errorMessage}
                            </span>
                        </div>
                    )}
                    <div className="grid gap-3 sm:grid-cols-2 2xl:grid-cols-4">
                        {stats.map((stat) => (
                            <article
                                key={stat.label}
                                className="glass-tile classroom-stat flex items-center gap-3 rounded-2xl p-4 sm:p-5"
                                data-accent={stat.accent}
                            >
                                <span className="classroom-stat-icon grid size-11 shrink-0 place-items-center rounded-xl">
                                    {stat.icon}
                                </span>
                                <div className="min-w-0">
                                    <p className="text-muted-foreground truncate text-xs font-medium">
                                        {stat.label}
                                    </p>
                                    <p className="truncate text-2xl leading-tight font-semibold tracking-tight">
                                        {stat.value}
                                    </p>
                                    <p className="text-muted-foreground mt-0.5 truncate text-[0.68rem]">
                                        {stat.detail}
                                    </p>
                                </div>
                            </article>
                        ))}
                    </div>

                    <section
                        aria-labelledby="classroom-list-title"
                        className="glass-backdrop classroom-directory rounded-3xl p-4 sm:p-6"
                    >
                        <header className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
                            <div>
                                <h2
                                    id="classroom-list-title"
                                    className="text-xl font-semibold tracking-tight"
                                >
                                    Explore classes
                                </h2>
                                <p className="text-muted-foreground mt-1 text-sm">
                                    Search by class, section, or class teacher.
                                </p>
                            </div>
                            <p
                                className="text-muted-foreground text-xs"
                                role="status"
                                aria-live="polite"
                            >
                                Showing {visibleSectionCount} of {totals.sectionCount} sections
                                {visibleSectionCount > 0
                                    ? ` · ${visibleStudentCount.toLocaleString()} students`
                                    : ""}
                            </p>
                        </header>

                        <div className="mb-5 space-y-4">
                            <div className="relative">
                                <Search
                                    aria-hidden="true"
                                    className="text-muted-foreground pointer-events-none absolute top-1/2 left-3.5 size-4 -translate-y-1/2"
                                />
                                <Input
                                    type="text"
                                    aria-label="Search classes, sections, and teachers"
                                    placeholder="Search classes, sections, teachers..."
                                    value={search}
                                    onChange={(event) => setSearch(event.target.value)}
                                    className="bg-card/40 h-11 rounded-xl pr-10 pl-10 dark:bg-black/15"
                                />
                                {search && (
                                    <button
                                        type="button"
                                        aria-label="Clear search"
                                        onClick={() => setSearch("")}
                                        className="text-muted-foreground hover:text-foreground focus-visible:ring-ring absolute top-1/2 right-3 -translate-y-1/2 rounded-md p-1 focus-visible:ring-2"
                                    >
                                        <X aria-hidden="true" className="size-4" />
                                    </button>
                                )}
                            </div>
                            <div className="classroom-stage-journey-panel">
                                <header className="classroom-stage-journey-header">
                                    <div>
                                        <p className="classroom-stage-journey-eyebrow">
                                            Learning journey
                                        </p>
                                        <h3>Choose a school stage</h3>
                                    </div>
                                    <button
                                        type="button"
                                        aria-pressed={stageFilter === "all"}
                                        data-stage="all"
                                        data-selected={stageFilter === "all"}
                                        onClick={() => setStageFilter("all")}
                                        className="classroom-stage-journey-all"
                                    >
                                        <span>All stages</span>
                                        <span>
                                            {groups.length}{" "}
                                            {groups.length === 1 ? "class" : "classes"}
                                        </span>
                                    </button>
                                </header>
                                <div
                                    role="group"
                                    aria-label="Choose a school stage"
                                    className="classroom-stage-journey"
                                >
                                    {stageOptions.map((stage, index) => {
                                        const stageGroups = groups.filter(
                                            (group) => group.stage === stage,
                                        );
                                        const stageSectionCount = stageGroups.reduce(
                                            (total, group) => total + group.sectionCount,
                                            0,
                                        );

                                        return (
                                            <button
                                                key={stage}
                                                type="button"
                                                aria-pressed={stageFilter === stage}
                                                data-stage={stage}
                                                data-selected={stageFilter === stage}
                                                onClick={() => setStageFilter(stage)}
                                                className="classroom-stage-step"
                                            >
                                                <span className="classroom-stage-step-node">
                                                    {index + 1}
                                                </span>
                                                <span className="classroom-stage-step-label">
                                                    {STAGE_LABELS[stage] ?? stage}
                                                </span>
                                                <span className="classroom-stage-step-meta">
                                                    {stageGroups.length}{" "}
                                                    {stageGroups.length === 1 ? "class" : "classes"}{" "}
                                                    · {stageSectionCount}{" "}
                                                    {stageSectionCount === 1
                                                        ? "section"
                                                        : "sections"}
                                                </span>
                                            </button>
                                        );
                                    })}
                                </div>
                            </div>
                        </div>

                        {groups.length === 0 ? (
                            <div className="glass-tile rounded-2xl px-6 py-10 text-center">
                                <BookOpen
                                    aria-hidden="true"
                                    className="text-primary mx-auto mb-3 size-8"
                                />
                                <h3 className="font-semibold">No classrooms yet</h3>
                                <p className="text-muted-foreground mt-1 text-sm">
                                    Classes and sections will appear here once they are set up for
                                    your school.
                                </p>
                            </div>
                        ) : visibleGroups.length === 0 ? (
                            <div className="glass-tile rounded-2xl px-6 py-10 text-center">
                                <Search
                                    aria-hidden="true"
                                    className="text-muted-foreground mx-auto mb-3 size-7"
                                />
                                <h3 className="font-semibold">No matching sections</h3>
                                <p className="text-muted-foreground mt-1 text-sm">
                                    Try another search or clear the stage filter.
                                </p>
                                <button
                                    type="button"
                                    onClick={() => {
                                        setSearch("");
                                        setStageFilter("all");
                                    }}
                                    className="text-primary focus-visible:ring-ring mt-3 rounded-md text-sm font-semibold hover:underline focus-visible:ring-2"
                                >
                                    Clear filters
                                </button>
                            </div>
                        ) : (
                            <ClassroomCards groups={visibleGroups} activeStage={stageFilter} />
                        )}
                    </section>
                </>
            )}
        </div>
    );
}

export default function ClassroomPage() {
    return (
        <RoleGuard
            allowedRoles={["SYSTEM_ADMIN", "SCHOOL_ADMIN", "PRINCIPAL", "VICE_PRINCIPAL", "HOD"]}
            fallback={<TeacherClassroom />}
        >
            <SchoolClassroom />
        </RoleGuard>
    );
}
