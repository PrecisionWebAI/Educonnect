"use client";

import { useState } from "react";
import { BookOpen, GraduationCap, School, UsersRound } from "lucide-react";
import { Spinner, Tabs } from "@/components/ui";
import { useClassroom, type ClassroomTab } from "./useClassroom";
import MyClasses from "./MyClasses";
import LessonPlan from "./LessonPlan";

const TABS: ClassroomTab[] = ["My Classes", "Lesson Plan"];

export default function TeacherClassroom() {
    const [tab, setTab] = useState<ClassroomTab>("My Classes");
    const classroom = useClassroom();

    const stats = [
        {
            label: "My classes",
            value: classroom.classrooms.length.toLocaleString(),
            detail: "Assigned to you",
            icon: <School aria-hidden="true" className="size-5" />,
        },
        {
            label: "Students",
            value: classroom.totalStudents.toLocaleString(),
            detail: "Across your classes",
            icon: <UsersRound aria-hidden="true" className="size-5" />,
        },
        {
            label: "Lesson topics",
            value: classroom.lesson ? classroom.lesson.topics.length.toLocaleString() : "—",
            detail: classroom.lesson ? "In your current plan" : "No lesson plan available",
            icon: <BookOpen aria-hidden="true" className="size-5" />,
        },
    ];

    return (
        <div className="classroom-page space-y-5 sm:space-y-6">
            <section className="classroom-hero relative overflow-hidden rounded-3xl p-5 sm:p-7">
                <div className="relative flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between">
                    <div className="max-w-3xl">
                        <div className="classroom-hero-kicker mb-3">
                            <GraduationCap aria-hidden="true" className="size-3.5" />
                            Your teaching space
                        </div>
                        <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
                            Classroom
                        </h1>
                        <p className="mt-2 max-w-2xl text-sm leading-relaxed sm:text-base">
                            Your classes, students, and lesson plan—organized in one clear view.
                        </p>
                    </div>
                    <div className="classroom-hero-highlight">
                        <span className="classroom-hero-highlight-icon">
                            <School aria-hidden="true" className="size-5" />
                        </span>
                        <div>
                            <p className="text-xs font-medium">Your teaching load</p>
                            <div className="flex items-baseline gap-1.5">
                                <span className="text-2xl leading-tight font-semibold">
                                    {classroom.classrooms.length.toLocaleString()}
                                </span>
                                <span className="text-xs">classes</span>
                            </div>
                            <p className="text-xs">
                                {classroom.totalStudents.toLocaleString()} students
                            </p>
                        </div>
                    </div>
                </div>
            </section>

            {classroom.loading ? (
                <div className="glass-tile flex min-h-40 items-center justify-center rounded-2xl">
                    <Spinner />
                </div>
            ) : (
                <>
                    <div className="grid gap-3 sm:grid-cols-2 2xl:grid-cols-3">
                        {stats.map((stat) => (
                            <article
                                key={stat.label}
                                className="glass-tile classroom-stat flex items-center gap-3 rounded-2xl p-4 sm:p-5"
                            >
                                <span className="bg-primary/10 text-primary grid size-11 shrink-0 place-items-center rounded-xl">
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

                    <section className="glass-backdrop classroom-directory rounded-3xl p-4 sm:p-5">
                        <Tabs
                            tabs={TABS}
                            active={tab}
                            onChange={(next) => setTab(next as ClassroomTab)}
                        />
                        {tab === "My Classes" ? (
                            <MyClasses rows={classroom.classrooms} />
                        ) : classroom.lesson ? (
                            <LessonPlan lesson={classroom.lesson} />
                        ) : (
                            <div className="glass-tile rounded-2xl px-6 py-10 text-center">
                                <BookOpen
                                    aria-hidden="true"
                                    className="text-primary mx-auto mb-3 size-8"
                                />
                                <h2 className="font-semibold">No lesson plan available</h2>
                                <p className="text-muted-foreground mt-1 text-sm">
                                    Your next lesson plan and its resources will appear here.
                                </p>
                            </div>
                        )}
                    </section>
                </>
            )}
        </div>
    );
}
