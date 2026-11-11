"use client";

import { useEffect, useMemo, useState } from "react";
import { PageHeader, Select, Spinner } from "@/components/ui";
import { useAuth } from "@/providers/auth-context";
import { getStudents, getTimetable } from "@/services";
import { useApiQuery } from "@/lib/api/use-api-query";
import type { TimetableSlot } from "@/types";

// The **personal** timetable: a student's (or guardian's) own class's week.
//
// Timetabling itself lives inside the Classroom — open a class-section and its
// Timetable tab edits that room's week for real (create, move, clear). This page
// only reads, so nothing here can change the school's schedule.

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];

/** `Monday` → `Mon`. */
function shortDay(day: string): string {
    return day.slice(0, 3);
}

export default function TimetablePage() {
    const { user } = useAuth();
    const timetableQuery = useApiQuery(["timetable"], getTimetable);
    // Only to recognise the viewer's own class-section.
    const studentsQuery = useApiQuery(["students"], () => getStudents());
    const slots: TimetableSlot[] = useMemo(
        () => timetableQuery.data ?? [],
        [timetableQuery.data],
    );

    /** The viewer's own row: a guardian's child, or a student by name. */
    const mine = useMemo(() => {
        const list = studentsQuery.data ?? [];
        return (
            list.find((s) => s.guardianUserId && s.guardianUserId === user?.id) ??
            list.find((s) => s.name === user?.fullName) ??
            null
        );
    }, [studentsQuery.data, user?.id, user?.fullName]);

    const classes = useMemo(
        () => Array.from(new Set(slots.map((s) => s.className))).sort(),
        [slots],
    );
    const [className, setClassName] = useState("all");

    // Start on the viewer's own class as soon as we can tell which one it is.
    useEffect(() => {
        if (mine && className === "all") setClassName(`${mine.className}-${mine.section}`);
    }, [mine, className]);

    const week = useMemo(
        () => slots.filter((s) => className === "all" || s.className === className),
        [slots, className],
    );
    /** The day's own periods, in the order they start. */
    const periods = useMemo(
        () => Array.from(new Set(week.map((s) => s.period))).sort(),
        [week],
    );

    function cell(day: string, period: string): TimetableSlot | undefined {
        return week.find((s) => s.day === day && s.period === period);
    }

    if (timetableQuery.isPending) return <Spinner />;

    return (
        <div>
            <PageHeader
                title={mine ? `${mine.className}-${mine.section} Timetable` : "Timetable"}
                subtitle="Your class's week, period by period."
            />

            <div className="toolbar">
                <Select
                    value={className}
                    onChange={(e) => setClassName(e.target.value)}
                    aria-label="Class"
                >
                    <option value="all">All classes</option>
                    {classes.map((name) => (
                        <option key={name} value={name}>
                            {name}
                        </option>
                    ))}
                </Select>
            </div>

            {week.length === 0 ? (
                <p className="text-muted-foreground rounded-md border border-dashed p-6 text-center text-sm">
                    Nothing is scheduled for this class yet.
                </p>
            ) : (
                <div className="table-wrap">
                    <table className="tt-table">
                        <thead>
                            <tr>
                                <th>Period</th>
                                {DAYS.map((day) => (
                                    <th key={day}>{shortDay(day)}</th>
                                ))}
                            </tr>
                        </thead>
                        <tbody>
                            {periods.map((period) => (
                                <tr key={period}>
                                    <th className="tt-period">
                                        <b>{period}</b>
                                    </th>
                                    {DAYS.map((day) => {
                                        const slot = cell(day, period);
                                        return (
                                            <td key={`${day}-${period}`}>
                                                <div className="tt-cell">
                                                    <b>{slot?.subject ?? "·"}</b>
                                                    {slot?.teacher && <span>{slot.teacher}</span>}
                                                </div>
                                            </td>
                                        );
                                    })}
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}
