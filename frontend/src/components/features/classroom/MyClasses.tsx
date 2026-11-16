"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { ArrowUpRight, BookOpen, CalendarDays, Search, UsersRound, X } from "lucide-react";
import { Badge, Input } from "@/components/ui";
import type { ClassroomItem } from "@/types";

export default function MyClasses({ rows }: { rows: ClassroomItem[] }) {
    const [search, setSearch] = useState("");
    const filteredRows = useMemo(() => {
        const query = search.trim().toLowerCase();
        if (!query) return rows;

        return rows.filter((row) =>
            [row.className, row.title, row.subject, row.teacher, row.nextLesson].some((value) =>
                value.toLowerCase().includes(query),
            ),
        );
    }, [rows, search]);

    return (
        <section aria-labelledby="my-classes-title" className="space-y-4">
            <header className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
                <div>
                    <h2 id="my-classes-title" className="text-lg font-semibold tracking-tight">
                        My classes
                    </h2>
                    <p className="text-muted-foreground mt-1 text-xs" role="status">
                        Showing {filteredRows.length} of {rows.length} classes
                    </p>
                </div>
                {rows.length > 0 && (
                    <div className="relative w-full sm:max-w-sm">
                        <Search
                            aria-hidden="true"
                            className="text-muted-foreground pointer-events-none absolute top-1/2 left-3.5 size-4 -translate-y-1/2"
                        />
                        <Input
                            type="text"
                            aria-label="Search my classes"
                            placeholder="Search classes or subjects..."
                            value={search}
                            onChange={(event) => setSearch(event.target.value)}
                            className="bg-card/40 h-10 rounded-xl pr-10 pl-10 dark:bg-black/15"
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
                )}
            </header>

            {rows.length === 0 ? (
                <div className="glass-tile rounded-2xl px-6 py-10 text-center">
                    <BookOpen aria-hidden="true" className="text-primary mx-auto mb-3 size-8" />
                    <h3 className="font-semibold">No classes assigned yet</h3>
                    <p className="text-muted-foreground mt-1 text-sm">
                        Your assigned classes will appear here.
                    </p>
                </div>
            ) : filteredRows.length === 0 ? (
                <div className="glass-tile rounded-2xl px-6 py-10 text-center">
                    <Search
                        aria-hidden="true"
                        className="text-muted-foreground mx-auto mb-3 size-7"
                    />
                    <h3 className="font-semibold">No matching classes</h3>
                    <p className="text-muted-foreground mt-1 text-sm">
                        Try a class name, subject, teacher, or lesson title.
                    </p>
                </div>
            ) : (
                <div className="grid items-stretch gap-4 sm:grid-cols-2 2xl:grid-cols-3">
                    {filteredRows.map((classroom) => (
                        <Link
                            key={classroom.id}
                            href={`/dashboard/classroom/${classroom.sectionId}`}
                            aria-label={`Open ${classroom.className}, ${classroom.subject}`}
                            className="focus-visible:ring-ring focus-visible:ring-offset-background block h-full rounded-2xl focus-visible:ring-2 focus-visible:ring-offset-2"
                        >
                            <article className="glass-tile classroom-section-card group flex h-full flex-col gap-4 rounded-2xl p-4 sm:p-5">
                                <header className="flex items-start justify-between gap-3">
                                    <div className="flex min-w-0 items-center gap-3">
                                        <span className="bg-primary/10 text-primary grid size-10 shrink-0 place-items-center rounded-xl">
                                            <BookOpen aria-hidden="true" className="size-5" />
                                        </span>
                                        <div className="min-w-0">
                                            <h3 className="truncate font-semibold">
                                                {classroom.className}
                                            </h3>
                                            <p className="text-muted-foreground truncate text-xs">
                                                {classroom.title}
                                            </p>
                                        </div>
                                    </div>
                                    <Badge tone="amber">{classroom.subject}</Badge>
                                </header>

                                <div className="border-border/70 space-y-2 border-y py-3 text-sm">
                                    <div className="text-muted-foreground flex items-center gap-2">
                                        <UsersRound
                                            aria-hidden="true"
                                            className="text-primary size-4 shrink-0"
                                        />
                                        <span className="truncate">
                                            {classroom.teacher} ·{" "}
                                            {classroom.students.toLocaleString()} students
                                        </span>
                                    </div>
                                    <div className="text-muted-foreground flex items-center gap-2">
                                        <CalendarDays
                                            aria-hidden="true"
                                            className="text-primary size-4 shrink-0"
                                        />
                                        <span className="truncate">
                                            Next lesson: {classroom.nextLesson}
                                        </span>
                                    </div>
                                </div>

                                <footer className="text-primary mt-auto flex items-center justify-between text-xs font-semibold">
                                    <span>Open class</span>
                                    <ArrowUpRight
                                        aria-hidden="true"
                                        className="size-4 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5"
                                    />
                                </footer>
                            </article>
                        </Link>
                    ))}
                </div>
            )}
        </section>
    );
}
