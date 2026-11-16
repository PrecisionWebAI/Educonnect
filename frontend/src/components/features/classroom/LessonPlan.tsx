"use client";

import { BookOpen, ClipboardCheck, FileText } from "lucide-react";
import { Badge } from "@/components/ui";
import type { LessonDetail } from "@/types";

export default function LessonPlan({ lesson }: { lesson: LessonDetail }) {
    return (
        <div className="grid gap-4 xl:grid-cols-[minmax(0,1.3fr)_minmax(18rem,0.7fr)]">
            <section className="glass-tile rounded-2xl p-4 sm:p-5">
                <header className="flex flex-wrap items-start justify-between gap-3">
                    <div className="flex min-w-0 items-center gap-3">
                        <span className="bg-primary/10 text-primary grid size-10 shrink-0 place-items-center rounded-xl">
                            <BookOpen aria-hidden="true" className="size-5" />
                        </span>
                        <div className="min-w-0">
                            <p className="text-muted-foreground text-[0.65rem] font-semibold tracking-[0.14em] uppercase">
                                Lesson plan
                            </p>
                            <h2 className="truncate text-lg font-semibold">{lesson.title}</h2>
                            <p className="text-muted-foreground truncate text-sm">
                                {lesson.subject} · {lesson.className}
                            </p>
                        </div>
                    </div>
                    <Badge tone="amber">{lesson.duration}</Badge>
                </header>

                <div className="border-border/70 mt-5 border-t pt-4">
                    <h3 className="mb-3 text-sm font-semibold">
                        Topics{" "}
                        <span className="text-muted-foreground">({lesson.topics.length})</span>
                    </h3>
                    {lesson.topics.length > 0 ? (
                        <ol className="grid gap-2 sm:grid-cols-2">
                            {lesson.topics.map((topic, index) => (
                                <li
                                    key={topic}
                                    className="border-border/70 bg-card/35 flex min-w-0 items-center gap-3 rounded-xl border px-3 py-2.5 text-sm"
                                >
                                    <span className="bg-primary/10 text-primary grid size-6 shrink-0 place-items-center rounded-full text-xs font-semibold">
                                        {index + 1}
                                    </span>
                                    <span className="min-w-0">{topic}</span>
                                </li>
                            ))}
                        </ol>
                    ) : (
                        <p className="text-muted-foreground text-sm">
                            No topics have been added to this lesson yet.
                        </p>
                    )}
                </div>
            </section>

            <div className="space-y-4">
                <section className="glass-tile rounded-2xl p-4 sm:p-5">
                    <header className="mb-3 flex items-center gap-2">
                        <FileText aria-hidden="true" className="text-primary size-4" />
                        <h3 className="font-semibold">Resources</h3>
                        <span className="text-muted-foreground ml-auto text-xs">
                            {lesson.resources.length}
                        </span>
                    </header>
                    {lesson.resources.length > 0 ? (
                        <ul className="space-y-2">
                            {lesson.resources.map((resource) => (
                                <li
                                    key={resource.id}
                                    className="border-border/70 bg-card/35 flex items-center justify-between gap-3 rounded-xl border px-3 py-2.5"
                                >
                                    <span className="min-w-0 truncate text-sm">
                                        {resource.title}
                                    </span>
                                    <Badge
                                        tone={
                                            resource.type === "Video"
                                                ? "violet"
                                                : resource.type === "PDF"
                                                  ? "teal"
                                                  : "amber"
                                        }
                                    >
                                        {resource.type}
                                    </Badge>
                                </li>
                            ))}
                        </ul>
                    ) : (
                        <p className="text-muted-foreground text-sm">
                            No resources attached to this plan.
                        </p>
                    )}
                </section>

                <section className="glass-tile rounded-2xl p-4 sm:p-5">
                    <header className="mb-2 flex items-center gap-2">
                        <ClipboardCheck aria-hidden="true" className="text-primary size-4" />
                        <h3 className="font-semibold">Homework</h3>
                    </header>
                    <p className="text-muted-foreground text-sm leading-relaxed">
                        {lesson.homework || "No homework set for this lesson."}
                    </p>
                </section>
            </div>
        </div>
    );
}
