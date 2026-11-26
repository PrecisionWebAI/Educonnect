"use client";

import { useMemo, useState } from "react";
import { Button, Card, EmptyState, Select, Spinner } from "@/components/ui";
import { Calendar } from "@/components/ui/calendar";
import { useToast } from "@/components/ui/toast";
import { usePermission } from "@/hooks/use-authorization";
import { isoDate, nthOffLabel, rangeLabel } from "@/lib/attendance/view";
import { errorMessage } from "@/lib/api/client";
import { titleCase } from "@/lib/format";
import type { SchoolHoliday } from "@/types";
import { useHolidays } from "./useHolidays";
import HolidayFormModal, { WEEK_OFF_VALUE } from "./HolidayFormModal";
import OpenDayDialog from "./OpenDayDialog";

// The school's calendar - a page of its own under **Operations & Insights → Calendar**.
//
// One set of holidays applies to **every** class and section, so nothing here names a
// section: the calendar, the list and the weekly off setting are the school's. The whole
// page is `holiday.manage` (principal and above); the sidebar hides it for everybody else
// and the server refuses the calls besides.
//
// Two answers, and the difference matters:
//
//   * **Weekly off card** - a rule (every Sunday, "the 2nd Saturday"). Saving it deletes
//     nothing: a day that already has a register is never closed by the rule, so those marks
//     stay and stay inside every percentage. The days still ahead are the ones that close.
//   * **Holiday form** (every type, "Weekly off" included) - a dated decision taken now. The
//     form reads the impact, names the class-sections and only the confirm deletes the rows.
//
// Clicking a day does one of three things: a **dated closure row** (a holiday, or the form's
// "Weekly off" type) opens its own form - which carries Delete; a day a **rule** closes offers
// "Open just this day"; a day that was opened that way offers "Close this day again". An open
// day still opens the form, so a holiday can be added on it.

const WEEKDAY_SHORT = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

/** The four Saturday rules, exactly as the setting stores them (`"5#1"` = 1st Saturday). */
const SATURDAY_RULES = [
    { token: "5#1", label: "1st Sat" },
    { token: "5#2", label: "2nd Sat" },
    { token: "5#3", label: "3rd Sat" },
    { token: "5#4", label: "4th Sat" },
];

const KINDS = [
    { value: "public", label: "Public holiday" },
    { value: "school", label: "School holiday" },
    { value: "vacation", label: "Vacation" },
    { value: "other", label: "Other" },
];

/** Every day a holiday's range covers, so the calendar can fill all of them. */
function daysOf(holiday: SchoolHoliday): string[] {
    const days: string[] = [];
    const current = new Date(`${holiday.startDate}T00:00:00`);
    const last = new Date(`${holiday.endDate}T00:00:00`);
    while (current <= last) {
        days.push(isoDate(current));
        current.setDate(current.getDate() + 1);
    }
    return days;
}

function rangeText(holiday: SchoolHoliday): string {
    return rangeLabel(holiday.startDate, holiday.endDate);
}

export default function SchoolCalendar() {
    const toast = useToast();
    const canEdit = usePermission("holiday.manage");
    const cal = useHolidays();
    const [formOpen, setFormOpen] = useState(false);
    const [editing, setEditing] = useState<SchoolHoliday | null>(null);
    /** The day the calendar was clicked on, so the form opens on it. */
    const [formDate, setFormDate] = useState<string | null>(null);
    /**
     * The day a click landed on, and what the one-date dialog can do with it.
     *
     * `reopened` flips the same dialog: a date that already carries an override offers
     * "close it again" instead of "open it".
     */
    const [dayAction, setDayAction] = useState<{
        date: string;
        /** Why the day is closed, in the calendar's own words. */
        reason: string;
        /** The date already carries an "open on purpose" override. */
        reopened: boolean;
        /** The day belongs to a holiday: opening it takes the day out of that holiday. */
        fromHoliday?: boolean;
    } | null>(null);
    const [typeFilter, setTypeFilter] = useState("all");
    const [whenFilter, setWhenFilter] = useState("upcoming");

    const weeklyOffDays = cal.weeklyOffDays;
    const weeklyOffNth = cal.weeklyOffNth;
    // The server's own answer for "which days in this window are weekly offs" - a whole
    // weekday, a "1st/2nd/3rd/4th Saturday" rule or a dated extra off. Shading from this list
    // means the calendar cannot disagree with the register about a Saturday.
    const weeklyOffDates = useMemo(
        () => new Set(cal.calendar?.weeklyOffDates ?? []),
        [cal.calendar],
    );
    // `undefined` means the API behind this screen predates `weekly_off_dates` (a stale
    // build); an **empty array** is a real answer - a school with no weekly offs at all. The
    // screen says which of the two it is instead of drawing a calendar with no shading and
    // leaving the reader to guess.
    const staleShading = Boolean(cal.calendar) && !Array.isArray(cal.calendar?.weeklyOffDates);
    const weekOffs = cal.calendar?.weekOffs ?? [];
    /** Dates opened on purpose ("just this day") - the way back is a click on them. */
    const openDayDates = useMemo(
        () => new Set((cal.calendar?.openDays ?? []).map((row) => row.onDate)),
        [cal.calendar],
    );
    /** Why each closed date is closed, straight from the server ("Sunday", "Diwali break"). */
    const closedReasons = useMemo(
        () => new Map((cal.calendar?.closedDays ?? []).map((row) => [row.date, row.reason])),
        [cal.calendar],
    );

    const today = isoDate(new Date());
    // The month the grid is showing, as the two ISO ends the "This month" filter compares with.
    // Comparing ends, not the start: a break that began in September still belongs to October
    // when it runs into it.
    const monthFrom = isoDate(new Date(cal.month.getFullYear(), cal.month.getMonth(), 1));
    const monthTo = isoDate(new Date(cal.month.getFullYear(), cal.month.getMonth() + 1, 0));
    /** Every holiday the window loaded - the empty list's own words need this count. */
    const holidayCount = (cal.calendar?.holidays ?? []).length;

    const holidayDays = useMemo(() => {
        const set = new Set<string>();
        for (const holiday of cal.calendar?.holidays ?? []) {
            for (const day of daysOf(holiday)) set.add(day);
        }
        return set;
    }, [cal.calendar]);

    /**
     * A weekly off in any of the three shapes the school can declare: a whole weekday, an
     * "1st/2nd/3rd/4th Saturday" rule, or one date added through the form's **Weekly off**
     * type. All three close the day the same way, so all three wear the same shade.
     *
     * The days come from the **server** (`weeklyOffDates`, built by `closure()`): the screen
     * shades a list, it never repeats the "which week of the month is this" arithmetic. One
     * rule, one answer - a 2nd/4th Saturday cannot look right here and wrong in the register.
     */
    const isWeeklyOff = (date: Date) => weeklyOffDates.has(isoDate(date));

    const visible = useMemo(() => {
        const rows = (cal.calendar?.holidays ?? []).filter((holiday) => {
            if (typeFilter !== "all" && holiday.kind !== typeFilter) return false;
            if (whenFilter === "upcoming") return holiday.endDate >= today;
            if (whenFilter === "past") return holiday.endDate < today;
            if (whenFilter === "month")
                return holiday.startDate <= monthTo && holiday.endDate >= monthFrom;
            return true;
        });
        // Upcoming first (soonest at the top), then the ones already over - latest first.
        return [...rows].sort((a, b) => {
            const aUpcoming = a.endDate >= today;
            const bUpcoming = b.endDate >= today;
            if (aUpcoming !== bUpcoming) return aUpcoming ? -1 : 1;
            return aUpcoming
                ? a.startDate.localeCompare(b.startDate)
                : b.startDate.localeCompare(a.startDate);
        });
    }, [cal.calendar, typeFilter, whenFilter, today, monthFrom, monthTo]);

    function openAdd(on?: Date) {
        setEditing(null);
        // A day clicked on the calendar pre-fills the form: the date is the one thing the
        // operator has already chosen, so asking for it twice is a wasted step.
        setFormDate(on ? isoDate(on) : null);
        setFormOpen(true);
    }

    function openEdit(holiday: SchoolHoliday) {
        setEditing(holiday);
        setFormDate(null);
        setFormOpen(true);
    }

    async function removeHoliday(holiday: SchoolHoliday): Promise<boolean> {
        try {
            await cal.remove.mutateAsync(holiday.id);
            toast.push(
                "success",
                `${
                    holiday.kind === WEEK_OFF_VALUE ? "Weekly off" : titleCase(holiday.name)
                } removed - the day is open again.`,
            );
            return true;
        } catch (cause) {
            toast.push("error", errorMessage(cause, "Could not remove the holiday"));
            return false;
        }
    }

    /**
     * Save the weekly offs - and nothing else.
     *
     * A weekday or a Saturday rule closes **every** matching day without a register. A day
     * that already has one is skipped by the rule, so this save never deletes a mark: that is
     * the whole reason the card needs no warning and no confirm.
     */
    async function commitOffs(days: number[], nth: string[]) {
        try {
            const saved = await cal.saveWeeklyOff.mutateAsync({ days, nth });
            // The server echoes what it stored. If a Saturday rule did not survive the round
            // trip, the API behind this screen is older than the screen - say so, instead of
            // showing a calendar that quietly disagrees with the setting.
            if (saved.nth.length !== nth.length) {
                toast.push(
                    "error",
                    "The server did not keep the Saturday rule. Restart the API and save again.",
                );
                return;
            }
            toast.push(
                "success",
                "Weekly off days saved. Days that already have a register keep it and stay counted.",
            );
        } catch (cause) {
            toast.push("error", errorMessage(cause, "Could not save the weekly off days"));
        }
    }

    /** The one-date confirm: reopen the day, and nothing else. */
    async function confirmOpenDay() {
        if (!dayAction) return;
        const { date } = dayAction;
        try {
            await cal.openDay.mutateAsync(date);
            toast.push(
                "success",
                dayAction.fromHoliday
                    ? `${rangeLabel(date, date)} is open and removed from ${dayAction.reason}. A register can be taken here now.`
                    : `${rangeLabel(date, date)} is open. Every other day still follows the weekly off - and a register can be taken here now.`,
            );
            setDayAction(null);
        } catch (cause) {
            toast.push("error", errorMessage(cause, "Could not open that day"));
        }
    }

    /** "Close this day again": the rule (or the holiday) takes the date back. */
    async function confirmCloseDay() {
        if (!dayAction) return;
        try {
            await cal.closeOpenDay.mutateAsync(dayAction.date);
            toast.push(
                "success",
                `${rangeLabel(dayAction.date, dayAction.date)} follows the school calendar again.`,
            );
            setDayAction(null);
        } catch (cause) {
            toast.push("error", errorMessage(cause, "Could not close that day again"));
        }
    }

    if (cal.loading) return <Spinner />;

    return (
        <div className="space-y-4">
            <div className="flex flex-wrap items-center justify-end gap-3">
                {canEdit && (
                    <Button size="sm" onClick={() => openAdd()}>
                        Add holiday
                    </Button>
                )}
            </div>

            <div className="two-col">
                <div className="two-col-main">
                    <Card
                        title={cal.month.toLocaleDateString("en-IN", {
                            month: "long",
                            year: "numeric",
                        })}
                        action={
                            <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => {
                                    const now = new Date();
                                    cal.setMonth(new Date(now.getFullYear(), now.getMonth(), 1));
                                }}
                            >
                                Today
                            </Button>
                        }
                    >
                        <Calendar
                            month={cal.month}
                            onMonthChange={cal.setMonth}
                            onDayClick={(day) => {
                                if (!canEdit) return;
                                const iso = isoDate(day);

                                // A date already opened on purpose: the only click that can
                                // answer "why is this Sunday open?" is the way back.
                                if (openDayDates.has(iso)) {
                                    setDayAction({
                                        date: iso,
                                        reason: "Opened on purpose",
                                        reopened: true,
                                    });
                                    return;
                                }

                                // A **dated weekly off** opens its own row: the card no longer
                                // lists those dates, so the form (with Delete) is the way back
                                // to one added by mistake.
                                const weekOff = weekOffs.find(
                                    (row) => row.startDate <= iso && row.endDate >= iso,
                                );
                                if (weekOff) {
                                    openEdit(weekOff);
                                    return;
                                }

                                // A holiday: the row stays and is edited from the list; the
                                // grid offers the one thing a day can answer - opening it.
                                const holiday = (cal.calendar?.holidays ?? []).find(
                                    (row) => row.startDate <= iso && row.endDate >= iso,
                                );
                                if (holiday) {
                                    setDayAction({
                                        date: iso,
                                        reason: titleCase(holiday.name),
                                        reopened: false,
                                        fromHoliday: true,
                                    });
                                    return;
                                }

                                // A rule (every Sunday, "the 2nd Saturday"): nothing to edit -
                                // the date can only be opened on its own.
                                const ruleReason = closedReasons.get(iso);
                                if (ruleReason) {
                                    setDayAction({
                                        date: iso,
                                        reason: ruleReason,
                                        reopened: false,
                                    });
                                    return;
                                }

                                openAdd(day);
                            }}
                            modifiers={{
                                holiday: (day: Date) => holidayDays.has(isoDate(day)),
                                weeklyOff: isWeeklyOff,
                                today: new Date(),
                            }}
                            modifiersClassNames={{
                                holiday: "att-day-holiday",
                                weeklyOff: "att-day-off",
                                today: "att-day-today",
                            }}
                            className="mx-auto"
                        />
                        <div className="text-muted-foreground mt-3 flex flex-wrap gap-x-4 gap-y-1 text-[0.72rem]">
                            <span>
                                <span className="att-legend att-legend-holiday" /> Holiday
                            </span>
                            <span>
                                <span className="att-legend att-legend-off" /> Weekly off
                            </span>
                        </div>
                        {canEdit && (
                            <p className="text-muted-foreground mt-2 text-[0.72rem]">
                                Click a day a weekly off closes to open just that date; a holiday or
                                a dated weekly off opens its own form. Click an open day to add a
                                holiday.
                            </p>
                        )}
                        {staleShading && (
                            <p className="mt-2 text-sm text-amber-600" role="status">
                                This calendar needs the current API build to shade weekly offs.
                                Restart the server and reload the page.
                            </p>
                        )}
                    </Card>

                    <Card title="Weekly off">
                        {canEdit ? (
                            <>
                                <WeeklyOffEditor
                                    key={`${weeklyOffDays.join(",")}|${weeklyOffNth.join(",")}`}
                                    initial={{ days: weeklyOffDays, nth: weeklyOffNth }}
                                    saving={cal.saveWeeklyOff.isPending}
                                    onSave={(days, nth) => void commitOffs(days, nth)}
                                />
                                <p className="text-muted-foreground mt-3 text-xs">
                                    Saving never deletes a register. A day that already has one
                                    stays a working day - those marks keep counting - and the rule
                                    takes the days after it.
                                </p>
                            </>
                        ) : (
                            <p className="text-muted-foreground text-sm">
                                {weeklyOffDays.length === 0 && weeklyOffNth.length === 0
                                    ? "The school runs every day of the week."
                                    : `The school is closed: ${[
                                          ...weeklyOffDays.map((day) => WEEKDAY_SHORT[day]),
                                          ...weeklyOffNth.map((token) => nthOffLabel(token)),
                                      ].join(", ")}.`}
                            </p>
                        )}
                    </Card>
                </div>

                <aside className="two-col-side">
                    <Card
                        title="Holidays"
                        action={
                            <div className="flex gap-2">
                                <Select
                                    value={whenFilter}
                                    onChange={(event) => setWhenFilter(event.target.value)}
                                    aria-label="When"
                                >
                                    <option value="upcoming">Upcoming</option>
                                    <option value="month">This month</option>
                                    <option value="past">Past</option>
                                    <option value="all">All</option>
                                </Select>
                                <Select
                                    value={typeFilter}
                                    onChange={(event) => setTypeFilter(event.target.value)}
                                    aria-label="Type"
                                >
                                    <option value="all">All types</option>
                                    {KINDS.map((kind) => (
                                        <option key={kind.value} value={kind.value}>
                                            {kind.label}
                                        </option>
                                    ))}
                                </Select>
                            </div>
                        }
                    >
                        {visible.length === 0 ? (
                            <EmptyState
                                icon="🗓️"
                                title="No holidays here"
                                body={
                                    holidayCount === 0
                                        ? "This calendar has no holidays yet. Add one, or widen the filter."
                                        : `This window has ${holidayCount} ${holidayCount === 1 ? "holiday" : "holidays"}, and this filter hides ${holidayCount === 1 ? "it" : "them"}. Choose "All" to see ${holidayCount === 1 ? "it" : "them"}.`
                                }
                            />
                        ) : (
                            <ul className="feed">
                                {visible.map((holiday) => (
                                    <li key={holiday.id} className="feed-item">
                                        <div className="feed-body">
                                            <span className="feed-title">
                                                {titleCase(holiday.name)}
                                            </span>
                                            <span className="feed-sub">
                                                {rangeText(holiday)} · {holiday.kindLabel}
                                                {holiday.days > 1 ? ` · ${holiday.days} days` : ""}
                                                {holiday.createdBy
                                                    ? ` · added by ${titleCase(holiday.createdBy)}`
                                                    : ""}
                                            </span>
                                        </div>
                                        {canEdit && (
                                            <div className="flex items-center gap-1">
                                                <Button
                                                    size="sm"
                                                    variant="ghost"
                                                    onClick={() => openEdit(holiday)}
                                                >
                                                    Edit
                                                </Button>
                                                <Button
                                                    size="sm"
                                                    variant="ghost"
                                                    onClick={() => void removeHoliday(holiday)}
                                                    disabled={cal.remove.isPending}
                                                >
                                                    Delete
                                                </Button>
                                            </div>
                                        )}
                                    </li>
                                ))}
                            </ul>
                        )}
                    </Card>

                    {(weeklyOffDays.length > 0 || weeklyOffNth.length > 0) && (
                        <Card title="Weekly offs">
                            <p className="text-muted-foreground text-sm">
                                {[
                                    ...weeklyOffDays.map((day) => WEEKDAY_SHORT[day]),
                                    ...weeklyOffNth.map((token) => nthOffLabel(token)),
                                ].join(", ")}{" "}
                                - the register is not taken on these days.
                            </p>
                        </Card>
                    )}
                </aside>
            </div>

            <HolidayFormModal
                key={`${editing?.id ?? "new"}-${formDate ?? ""}-${formOpen}`}
                open={formOpen}
                holiday={editing}
                defaultDate={formDate}
                holidays={[...(cal.calendar?.holidays ?? []), ...weekOffs]}
                saving={cal.create.isPending || cal.update.isPending}
                removing={cal.remove.isPending}
                onClose={() => setFormOpen(false)}
                onDelete={
                    editing
                        ? async () => {
                              if (await removeHoliday(editing)) setFormOpen(false);
                          }
                        : undefined
                }
                onSubmit={async (input) => {
                    try {
                        const impact = editing
                            ? await cal.update.mutateAsync({ id: editing.id, input })
                            : await cal.create.mutateAsync(input);
                        // A weekly off has no name of its own - the type is the name.
                        const label =
                            input.kind === WEEK_OFF_VALUE ? "Weekly off" : titleCase(input.name);
                        toast.push(
                            "success",
                            impact.savedRegisterDays > 0
                                ? `${label} saved. ${impact.savedRegisterDays} saved register day(s) stay in the table and leave every count.`
                                : `${label} saved.`,
                        );
                        setFormOpen(false);
                    } catch (cause) {
                        toast.push("error", errorMessage(cause, "Could not save the holiday"));
                    }
                }}
            />

            {dayAction && (
                <OpenDayDialog
                    open
                    date={dayAction.date}
                    reason={dayAction.reason}
                    reopened={dayAction.reopened}
                    fromHoliday={dayAction.fromHoliday}
                    busy={
                        cal.openDay.isPending || cal.closeOpenDay.isPending || cal.remove.isPending
                    }
                    onCancel={() => setDayAction(null)}
                    onConfirm={() =>
                        dayAction.reopened ? void confirmCloseDay() : void confirmOpenDay()
                    }
                />
            )}
        </div>
    );
}

/**
 * The weekly off toggles.
 *
 * Two rows, because a school expresses "off" two ways: **whole weekdays** (every Sunday)
 * and **the nth Saturday of the month** ("2nd and 4th"). Both are one setting each -
 * never a row per Sunday - and the parent passes the server's values with a `key`, so a
 * saved value hands the editor a fresh starting point without an effect writing state
 * during render.
 */
function WeeklyOffEditor({
    initial,
    saving,
    onSave,
}: {
    initial: { days: number[]; nth: string[] };
    saving: boolean;
    onSave: (days: number[], nth: string[]) => void;
}) {
    const [days, setDays] = useState(initial.days);
    const [nth, setNth] = useState(initial.nth);

    const toggleDay = (index: number) =>
        setDays((current) =>
            current.includes(index)
                ? current.filter((day) => day !== index)
                : [...current, index].sort((a, b) => a - b),
        );

    const toggleNth = (token: string) =>
        setNth((current) =>
            current.includes(token)
                ? current.filter((value) => value !== token)
                : [...current, token].sort(),
        );

    const dirty =
        days.join(",") !== initial.days.join(",") || nth.join(",") !== initial.nth.join(",");

    return (
        <>
            <p className="text-muted-foreground mb-3 text-xs">
                The days this school is closed every week. Holidays are added on top of these.
            </p>
            <div className="flex flex-wrap gap-2">
                {WEEKDAY_SHORT.map((label, index) => {
                    const on = days.includes(index);
                    return (
                        <Button
                            key={label}
                            size="sm"
                            variant={on ? "primary" : "outline"}
                            onClick={() => toggleDay(index)}
                        >
                            {label}
                        </Button>
                    );
                })}
            </div>

            <p className="text-muted-foreground mt-3 mb-2 text-xs">
                A Saturday that is off every month - pick the weeks, not each date.
            </p>
            <div className="flex flex-wrap gap-2">
                {SATURDAY_RULES.map((rule) => {
                    const on = nth.includes(rule.token);
                    return (
                        <Button
                            key={rule.token}
                            size="sm"
                            variant={on ? "primary" : "outline"}
                            onClick={() => toggleNth(rule.token)}
                        >
                            {rule.label}
                        </Button>
                    );
                })}
            </div>

            <Button
                size="sm"
                className="mt-3"
                onClick={() => onSave(days, nth)}
                disabled={saving || !dirty}
            >
                {saving ? "Saving…" : "Save weekly off"}
            </Button>
        </>
    );
}
