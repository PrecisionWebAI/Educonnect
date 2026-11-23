"use client";

import * as React from "react";
import { CalendarIcon } from "lucide-react";
import type { DayButton } from "react-day-picker";

import { Button } from "@/components/ui/button";
import { Calendar, CalendarDayButton } from "@/components/ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { closedTone, isoDate } from "@/lib/attendance/view";
import type { SectionCalendarDay } from "@/types";

// The register's date control.
//
// It is a **button in the tab row**, not a card: the day is what Daily Attendance is
// about, so it sits beside the tab's own name. Opening it shows the same month grid with
// the school's calendar painted on it - a weekly off (a weekday, a "1st Saturday" rule or
// a dated extra off) in the neutral shade, a holiday in the brand colour, and a green dot
// on every day this class-section already has a register for - and the legend that names
// those three states **inside** the calendar, so the colours are explained where they are
// read.
//
// A closed day stays **clickable**: the register behind it is history, and opening a
// holiday shows the "school closed" card with its own reason instead of a dead control.
//
// Only the days of the month on screen can be picked. The neighbouring months' days are drawn
// faint and refuse the tap (the shared `Calendar` scopes them away), so stepping to another
// month is the arrow - never a lucky click on a greyed-out "1".
//
// A **future** day is not pickable at all: the register records what happened, and the server
// refuses a future save with `422`. Past days stay clickable - a correction is normal work.

function parseISODate(value: string): Date | undefined {
    if (!value) return undefined;
    const date = new Date(`${value}T00:00:00`);
    return Number.isNaN(date.getTime()) ? undefined : date;
}

/**
 * The day button, with the saved-register dot drawn **inside it**.
 *
 * The dot cannot be CSS on the modifier class: react-day-picker puts that class on the day
 * **cell** (`td`), which is not a positioned box, so an absolutely-positioned dot escaped the
 * cell - and inside a popover it anchored to the panel itself, which is why nothing showed.
 * A real child of the button removes the guess: it shares the number's own box and stays on
 * top of whatever colour the day wears (including the selected day's fill).
 */
function AttendanceDayButton(props: React.ComponentProps<typeof CalendarDayButton>) {
    const saved = Boolean(props.modifiers?.saved);
    // Nested children override the `children` inside `{...props}`, so the number and the dot
    // are the button's whole content.
    return (
        <CalendarDayButton {...props}>
            {props.children}
            {saved ? <i className="att-saved-dot" aria-hidden /> : null}
        </CalendarDayButton>
    );
}

export default function AttendanceDatePicker({
    date,
    days,
    onChange,
    yearWindow,
}: {
    /** The day the register is showing, `yyyy-MM-dd`. */
    date: string;
    /** The days of the loaded window, with their closed kind and saved flag. */
    days: SectionCalendarDay[];
    onChange: (value: string) => void;
    /** The selected session year: days outside it cannot be picked. */
    yearWindow?: { startDate: string; endDate: string } | null;
}) {
    const [open, setOpen] = React.useState(false);
    const selected = parseISODate(date);

    const byDate = React.useMemo(() => new Map(days.map((day) => [day.date, day])), [days]);

    const kindOf = (day: Date) => byDate.get(isoDate(day))?.closedKind ?? null;
    const isHoliday = (day: Date) => closedTone(kindOf(day)) === "holiday";
    const isWeeklyOff = (day: Date) => {
        const kind = kindOf(day);
        return Boolean(kind) && closedTone(kind) === "off";
    };
    const isSaved = (day: Date) => byDate.get(isoDate(day))?.saved ?? false;

    return (
        <Popover open={open} onOpenChange={setOpen}>
            <PopoverTrigger
                render={
                    <Button
                        type="button"
                        variant="outline"
                        aria-label={`Change the register's date, now ${date}`}
                    >
                        <CalendarIcon className="size-3.5" />
                        {selected
                            ? selected.toLocaleDateString("en-IN", {
                                  day: "numeric",
                                  month: "short",
                                  year: "numeric",
                              })
                            : "Pick a date"}
                    </Button>
                }
            />
            <PopoverContent align="start" className="w-auto p-0">
                <Calendar
                    mode="single"
                    selected={selected}
                    defaultMonth={selected}
                    // A future day cannot hold a register: it is refused here as well as by
                    // the API, so the control never offers a day the save would reject.
                    disabled={(day: Date) => {
                        const iso = isoDate(day);
                        if (iso > isoDate(new Date())) return true;
                        return Boolean(
                            yearWindow && (iso < yearWindow.startDate || iso > yearWindow.endDate),
                        );
                    }}
                    // The dot is part of the button (see `AttendanceDayButton`), so it is the
                    // button - not the cell - that has to know the day is saved.
                    components={{ DayButton: AttendanceDayButton as typeof DayButton }}
                    modifiers={{
                        holiday: isHoliday,
                        weeklyOff: isWeeklyOff,
                        saved: isSaved,
                        today: new Date(),
                    }}
                    modifiersClassNames={{
                        holiday: "att-day-holiday",
                        weeklyOff: "att-day-off",
                        today: "att-day-today",
                    }}
                    onSelect={(day) => {
                        if (!day) return;
                        onChange(isoDate(day));
                        setOpen(false);
                    }}
                />
                <div className="px-3 pb-2">
                    <div className="att-calendar-legend">
                        <span>
                            <span className="att-legend att-legend-holiday" /> Holiday
                        </span>
                        <span>
                            <span className="att-legend att-legend-off" /> Weekly off
                        </span>
                        <span>
                            <span className="att-legend att-legend-saved" /> Register saved
                        </span>
                    </div>
                </div>
            </PopoverContent>
        </Popover>
    );
}
