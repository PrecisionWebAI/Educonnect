"use client";

import { useMemo } from "react";
import { Button, Spinner } from "@/components/ui";
import { errorMessage } from "@/lib/api/client";
import { useApiQuery } from "@/lib/api/use-api-query";
import { gridRows, hhmm, subjectColor } from "@/lib/timetable/view";
import { getTeacherTimetable } from "@/services";

/** Monday to Saturday always; Sunday only when the teacher actually has a period on it. */
const DAYS: { value: string; label: string }[] = [
    { value: "monday", label: "Mon" },
    { value: "tuesday", label: "Tue" },
    { value: "wednesday", label: "Wed" },
    { value: "thursday", label: "Thu" },
    { value: "friday", label: "Fri" },
    { value: "saturday", label: "Sat" },
    { value: "sunday", label: "Sun" },
];

/**
 * One teacher's whole week, drawn like a class-section's timetable.
 *
 * Same grid as Classroom > Timetable (days across, the school's periods down) and the same
 * subject colours, but each cell names the **class-section** the teacher is in, with the
 * subject under it. Read only: the timetable is edited in the classroom, so this view can
 * never disagree with it.
 */
export default function TeacherTimetable({
    employeeId,
    name,
    onBack,
}: {
    employeeId: string;
    name: string;
    onBack: () => void;
}) {
    const timetable = useApiQuery(["course", "teacher-timetable", employeeId], () =>
        getTeacherTimetable(employeeId),
    );
    const periods = timetable.data?.periods;
    const bell = timetable.data?.bell;

    const rows = useMemo(() => gridRows(bell ?? [], periods ?? []), [bell, periods]);
    const days = useMemo(
        () =>
            DAYS.filter(
                (day) =>
                    day.value !== "sunday" ||
                    (periods ?? []).some((period) => period.dayOfWeek === "sunday"),
            ),
        [periods],
    );

    function cellAt(day: string, start: string) {
        return (periods ?? []).find(
            (period) => period.dayOfWeek === day && hhmm(period.startTime) === start,
        );
    }

    return (
        <div className="space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                    <h3 className="font-semibold">{name}</h3>
                    <p className="text-muted-foreground text-xs">
                        Weekly timetable · {periods?.length ?? 0} period
                        {periods?.length === 1 ? "" : "s"} a week
                    </p>
                </div>
                <Button variant="ghost" size="sm" onClick={onBack}>
                    ← Back to teachers
                </Button>
            </div>

            {timetable.isPending ? (
                <Spinner />
            ) : timetable.error ? (
                <p className="text-sm text-red-500">
                    {errorMessage(timetable.error, "The timetable could not be loaded.")}
                </p>
            ) : (periods ?? []).length === 0 ? (
                <p className="text-muted-foreground text-sm">
                    This teacher is not placed in any timetable slot yet.
                </p>
            ) : (
                <div className="table-wrap">
                    <table className="tt-table tt-week">
                        <thead>
                            <tr>
                                <th className="tt-day">Period</th>
                                {days.map((day) => (
                                    <th key={day.value} className="tt-dayhead">
                                        {day.label}
                                    </th>
                                ))}
                            </tr>
                        </thead>
                        <tbody>
                            {rows.map((row) => (
                                <tr key={row.key}>
                                    <th className="tt-period">
                                        <b>{row.label || row.start}</b>
                                        <span>
                                            {row.start} - {row.end}
                                        </span>
                                    </th>
                                    {row.isBreak ? (
                                        <td colSpan={days.length} className="tt-cell tt-break">
                                            Break
                                        </td>
                                    ) : (
                                        days.map((day) => {
                                            const slot = cellAt(day.value, row.start);
                                            return (
                                                <td key={`${day.value}-${row.key}`}>
                                                    {slot ? (
                                                        <div
                                                            className={`tt-cell ${subjectColor(slot.subject)}`}
                                                        >
                                                            <b>
                                                                {slot.className}{" "}
                                                                {slot.sectionName}
                                                            </b>
                                                            <span>{slot.subject}</span>
                                                            {slot.room && <span>{slot.room}</span>}
                                                        </div>
                                                    ) : (
                                                        <div className="tt-cell tt-empty">
                                                            <span>·</span>
                                                        </div>
                                                    )}
                                                </td>
                                            );
                                        })
                                    )}
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}
