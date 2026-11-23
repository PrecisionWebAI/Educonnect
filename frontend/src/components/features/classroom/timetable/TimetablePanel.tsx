"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Button, Card, Input, Modal, Select, Spinner } from "@/components/ui";
import { useToast } from "@/components/ui/toast";
import { ApiError, errorMessage } from "@/lib/api/client";
import { usePermission } from "@/hooks/use-authorization";
import type { BellSlot } from "@/types";
import { useQueryClient } from "@tanstack/react-query";
import {
    assignCourseTeacher,
    getBellSchedule,
    getTimetable,
    getWeekOff,
    setBellSchedule,
} from "@/services";
import { useApiQuery } from "@/lib/api/use-api-query";
import { gridRows } from "@/lib/timetable/view";
import { useSectionTimetable } from "./useSectionTimetable";

// Timetable **inside one class-section**.
//
// The week belongs to the room you opened: a period names its section, so this grid is
// this class-section's week and nothing else's. Editing is real - the slot is written to
// `timetableperiod` (create / move) or deleted - so the school-wide Timetable and this
// page can never disagree.
//
// The **shape of the day** comes from the school (`GET /timetable/bell-schedule`): six
// periods and two breaks by default, whatever the school actually runs. Phase 9 removed
// the hardcoded array this file used to carry, so a school with eight periods or a long
// lunch is described by its own rows - and a break is drawn as a break, not as an empty
// teaching period.

/** Monday to Saturday, with the backend's enum values. */
const DAYS: { value: string; label: string; weekday: number }[] = [
    { value: "monday", label: "Mon", weekday: 0 },
    { value: "tuesday", label: "Tue", weekday: 1 },
    { value: "wednesday", label: "Wed", weekday: 2 },
    { value: "thursday", label: "Thu", weekday: 3 },
    { value: "friday", label: "Fri", weekday: 4 },
    { value: "saturday", label: "Sat", weekday: 5 },
    { value: "sunday", label: "Sun", weekday: 6 },
];

interface SetupDraft {
    periods: number;
    breaks: { afterPeriod: number; minutes: number }[];
    startTime: string;
    periodMinutes: number;
    /** Extra classes only: before or after the regular periods, never between them. */
    position?: "before" | "after";
}

/** Minutes between two `HH:MM` times. */
function minutesBetween(start: string, end: string): number {
    const [sh, sm] = start.split(":").map(Number);
    const [eh, em] = end.split(":").map(Number);
    return eh * 60 + em - (sh * 60 + sm);
}

/** Read the school's slots back into "N periods, breaks after which" (regular or extra). */
function parseSetup(slots: BellSlot[], extra: boolean): SetupDraft {
    const part = slots
        .filter((s) => Boolean(s.extra) === extra)
        .sort((a, b) => a.periodNo - b.periodNo);
    const lessons = part.filter((s) => !s.isBreak);
    const breaks: SetupDraft["breaks"] = [];
    let lesson = 0;
    for (const slot of part) {
        if (!slot.isBreak) lesson += 1;
        else if (lesson >= 1)
            breaks.push({
                afterPeriod: lesson,
                minutes: minutesBetween(slot.startTime.slice(0, 5), slot.endTime.slice(0, 5)),
            });
    }
    const regularStart = slots.find((s) => !s.extra)?.startTime ?? "";
    return {
        position: extra && part[0] && part[0].startTime < regularStart ? "before" : "after",
        periods: extra ? lessons.length : Math.max(lessons.length, 1),
        breaks,
        startTime: part[0]?.startTime.slice(0, 5) ?? (extra ? "15:00" : "08:00"),
        periodMinutes: lessons[0]
            ? minutesBetween(lessons[0].startTime.slice(0, 5), lessons[0].endTime.slice(0, 5))
            : extra
              ? 40
              : 45,
    };
}

/** The count / breaks / start / length / break-after fields, for either part of the day. */
function SetupFields({
    draft,
    onChange,
    countLabel,
    startLabel,
    minCount,
    maxCount,
    prefix,
    showPosition = false,
}: {
    showPosition?: boolean;
    draft: SetupDraft;
    onChange: (next: SetupDraft) => void;
    countLabel: string;
    startLabel: string;
    minCount: number;
    maxCount: number;
    prefix: string;
}) {
    function changeCount(periods: number) {
        // A break cannot follow a period that no longer exists.
        const breaks = draft.breaks
            .filter((b) => b.afterPeriod <= periods)
            .slice(0, Math.max(periods - 1, 0));
        onChange({ ...draft, periods, breaks });
    }
    function changeBreakCount(count: number) {
        const breaks = draft.breaks.slice(0, count);
        while (breaks.length < count) {
            const taken = new Set(breaks.map((b) => b.afterPeriod));
            let next = 1;
            while (taken.has(next)) next += 1;
            breaks.push({ afterPeriod: Math.min(next, draft.periods), minutes: 20 });
        }
        onChange({ ...draft, breaks });
    }
    function updateBreak(index: number, patch: Partial<SetupDraft["breaks"][number]>) {
        onChange({
            ...draft,
            breaks: draft.breaks.map((b, i) => (i === index ? { ...b, ...patch } : b)),
        });
    }
    return (
        <>
            <div className="form-grid">
                <Select
                    label={countLabel}
                    value={String(draft.periods)}
                    onChange={(e) => changeCount(Number(e.target.value))}
                >
                    {Array.from({ length: maxCount - minCount + 1 }, (_, i) => i + minCount).map(
                        (n) => (
                            <option key={n} value={n}>
                                {n}
                            </option>
                        ),
                    )}
                </Select>
                {showPosition && (
                    <Select
                        label="Runs"
                        value={draft.position ?? "after"}
                        onChange={(e) =>
                            onChange({ ...draft, position: e.target.value as "before" | "after" })
                        }
                    >
                        <option value="after">After the regular periods</option>
                        <option value="before">Before the regular periods</option>
                    </Select>
                )}
                <Select
                    label="Number of breaks"
                    value={String(draft.breaks.length)}
                    onChange={(e) => changeBreakCount(Number(e.target.value))}
                >
                    {Array.from({ length: Math.max(draft.periods, 1) }, (_, i) => i).map((n) => (
                        <option key={n} value={n}>
                            {n}
                        </option>
                    ))}
                </Select>
                <Input
                    label={startLabel}
                    type="time"
                    value={draft.startTime}
                    onChange={(e) => onChange({ ...draft, startTime: e.target.value })}
                />
                <Input
                    label="Period length (min)"
                    type="number"
                    min={10}
                    max={120}
                    value={draft.periodMinutes}
                    onChange={(e) => onChange({ ...draft, periodMinutes: Number(e.target.value) })}
                />
            </div>
            {draft.breaks.length > 0 && (
                <div className="form-grid">
                    {draft.breaks.map((brk, index) => (
                        <div key={index} className="form-grid">
                            <Select
                                label={`Break ${index + 1} after`}
                                value={String(brk.afterPeriod)}
                                onChange={(e) =>
                                    updateBreak(index, { afterPeriod: Number(e.target.value) })
                                }
                            >
                                {Array.from({ length: draft.periods }, (_, i) => i + 1).map((n) => (
                                    <option key={n} value={n}>
                                        {prefix}
                                        {n}
                                    </option>
                                ))}
                            </Select>
                            <Input
                                label="Minutes"
                                type="number"
                                min={5}
                                max={120}
                                value={brk.minutes}
                                onChange={(e) =>
                                    updateBreak(index, { minutes: Number(e.target.value) })
                                }
                            />
                        </div>
                    ))}
                </div>
            )}
        </>
    );
}

/** Subject colours, picked from the name so a subject keeps its colour. */
/** How the edit card names each kind of class. */
const KIND_LABEL = { regular: "Regular", extra: "Extra classes" } as const;

const COLORS = ["tt-c0", "tt-c1", "tt-c2", "tt-c3", "tt-c4", "tt-c5", "tt-c6"];

function colorFor(subject: string): string {
    let hash = 0;
    for (let i = 0; i < subject.length; i++) hash = (hash * 31 + subject.charCodeAt(i)) >>> 0;
    return COLORS[hash % COLORS.length];
}

export default function TimetablePanel({
    sectionId,
    classroomId,
    classLabel,
    subjects,
    teachers,
}: {
    sectionId: string;
    classroomId: string;
    /** "Class 10-A" - what the header and the clash check call this room. */
    classLabel: string;
    /** The section's own subjects. */
    subjects: { id: string; name: string; teacherId?: string | null }[];
    /** Teachers who can be put in a slot. */
    teachers: { employeeId: string; name: string }[];
}) {
    const toast = useToast();
    const canEdit = usePermission("timetable.create");
    const canClear = usePermission("timetable.delete");
    const { periods, loading, save, clear } = useSectionTimetable({ sectionId, classroomId });
    // The school-wide grid, read only to warn when a teacher is booked elsewhere.
    const allSlots = useApiQuery(["timetable"], getTimetable, { enabled: canEdit });
    // The school's own day shape - periods and breaks, seeded on first read.
    const bell = useApiQuery(["timetable", "bell"], getBellSchedule);
    const [selected, setSelected] = useState<{ day: string; start: string; end: string } | null>(
        null,
    );
    const [draft, setDraft] = useState({ classroomSubjectId: "", teacherId: "", room: "" });
    const [busy, setBusy] = useState(false);
    const queryClient = useQueryClient();
    // Weekly offs block whole day rows. A failed read just means nothing is blocked.
    const weekOff = useApiQuery(["timetable", "week-off"], getWeekOff, { retry: false });
    const offDays = useMemo(() => new Set(weekOff.data?.days ?? []), [weekOff.data]);
    // "1st Saturday off" style rules: the day is open most weeks, so it is only flagged.
    const partialOff = useMemo(
        () => new Set((weekOff.data?.nth ?? []).map((token) => Number(token.split("#")[0]))),
        [weekOff.data],
    );

    const [setupOpen, setSetupOpen] = useState(false);
    const [setupMode, setSetupMode] = useState<"period" | "extra">("period");
    const [setupEdit, setSetupEdit] = useState<SetupDraft | null>(null);
    const [extraEdit, setExtraEdit] = useState<SetupDraft | null>(null);
    /** The school's current shape, read back into the "periods / breaks" words. */
    const currentSetup = useMemo(() => parseSetup(bell.data ?? [], false), [bell.data]);
    const currentExtra = useMemo(() => parseSetup(bell.data ?? [], true), [bell.data]);
    const setup = setupEdit ?? currentSetup;
    const extra = extraEdit ?? currentExtra;

    async function saveSetup() {
        for (const draft of [setup, extra]) {
            const afters = draft.breaks.map((b) => b.afterPeriod);
            if (new Set(afters).size !== afters.length) {
                toast.push("error", "Two breaks are set after the same period");
                return;
            }
        }
        // Extra classes are only sent once they have been touched.
        const input = {
            ...setup,
            extra: extraEdit
                ? {
                      count: extraEdit.periods,
                      breaks: extraEdit.breaks,
                      startTime: extraEdit.startTime,
                      periodMinutes: extraEdit.periodMinutes,
                      position: extraEdit.position ?? "after",
                  }
                : undefined,
        };
        setBusy(true);
        try {
            try {
                await setBellSchedule(input);
            } catch (error) {
                // 409: some placed periods fall after the new last period.
                if (
                    error instanceof ApiError &&
                    error.status === 409 &&
                    window.confirm(`${error.message}\n\nSave anyway?`)
                ) {
                    await setBellSchedule({ ...input, force: true });
                } else {
                    throw error;
                }
            }
            await queryClient.invalidateQueries({ queryKey: ["timetable"] });
            toast.push("success", "Period setup saved");
            setSetupEdit(null);
            setExtraEdit(null);
            setSetupOpen(false);
        } catch (error) {
            toast.push("error", errorMessage(error, "Could not save the period setup"));
        } finally {
            setBusy(false);
        }
    }

    /** Subject and teacher names, for the grid's cells. */
    const subjectName = useMemo(() => new Map(subjects.map((s) => [s.id, s.name])), [subjects]);
    const teacherName = useMemo(
        () => new Map(teachers.map((t) => [t.employeeId, t.name])),
        [teachers],
    );

    /** The period sitting in a grid cell, if the week has one. */
    function findPeriod(day: string, start: string) {
        return periods.find((p) => p.dayOfWeek === day && p.startTime === start);
    }

    /** The rows the table draws: the school's bell slots, plus any stray period. */
    const rows = useMemo(() => gridRows(bell.data ?? [], periods), [bell.data, periods]);

    /** Is this teacher already teaching another class at that time? */
    const clash = useMemo(() => {
        if (!selected || !draft.teacherId) return null;
        const name = teacherName.get(draft.teacherId);
        if (!name) return null;
        const day = selected.day.charAt(0).toUpperCase() + selected.day.slice(1);
        const other = (allSlots.data ?? []).find(
            (slot) =>
                slot.day === day &&
                slot.period.startsWith(selected.start) &&
                slot.teacherId === draft.teacherId &&
                slot.sectionId !== sectionId,
        );
        return other
            ? `${name} is already teaching ${other.className} at ${selected.start}.`
            : null;
    }, [selected, draft.teacherId, teacherName, allSlots.data, sectionId]);

    function openCell(day: string, start: string, end: string) {
        const existing = findPeriod(day, start);
        setSelected({ day, start, end });
        const subjectId = existing?.classroomSubjectId ?? subjects[0]?.id ?? "";
        setDraft({
            classroomSubjectId: subjectId,
            // The teacher who holds the subject in the course is the default.
            teacherId: existing?.teacherId ?? courseTeacherOf(subjectId),
            room: existing?.room ?? "",
        });
    }

    /** The teacher the Course tab has given this subject ("" when nobody holds it yet). */
    function courseTeacherOf(subjectId: string): string {
        return subjects.find((subject) => subject.id === subjectId)?.teacherId ?? "";
    }

    // Clicking a cell opens the edit card below the grid: bring it into view.
    const editRef = useRef<HTMLDivElement>(null);
    useEffect(() => {
        if (selected) editRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, [selected]);

    const [confirmTeacher, setConfirmTeacher] = useState(false);
    const canAssignTeacher = usePermission("course.assign_teacher");

    /** What the pop-up tells the office before a subject changes hands. */
    const handover = useMemo(() => {
        if (!selected || !draft.teacherId) return null;
        const name = teacherName.get(draft.teacherId) ?? "This teacher";
        const day = selected.day.charAt(0).toUpperCase() + selected.day.slice(1);
        const already = (allSlots.data ?? []).filter(
            (slot) =>
                slot.teacherId === draft.teacherId &&
                !(
                    slot.day === day &&
                    slot.period.startsWith(selected.start) &&
                    slot.sectionId === sectionId
                ),
        ).length;
        return {
            name,
            already,
            subject: subjectName.get(draft.classroomSubjectId) ?? "this subject",
        };
    }, [selected, draft, teacherName, allSlots.data, sectionId, subjectName]);

    /**
     * The chosen teacher's load across **every** class, counting this period: how many
     * that day and how many in the week (the principal's "day 6, wk 17").
     */
    /**
     * Regular classes and extra classes are counted apart: a teacher turns red when they
     * hold every regular period of a day, or every extra class of a day.
     */
    const extraStarts = useMemo(
        () =>
            new Set(
                (bell.data ?? [])
                    .filter((slot) => slot.extra && !slot.isBreak)
                    .map((slot) => slot.startTime.slice(0, 5)),
            ),
        [bell.data],
    );
    const dayTotals = useMemo(
        () => ({
            regular: (bell.data ?? []).filter((slot) => !slot.extra && !slot.isBreak).length,
            extra: extraStarts.size,
        }),
        [bell.data, extraStarts],
    );
    const kindOf = useCallback(
        (start: string): "regular" | "extra" => (extraStarts.has(start) ? "extra" : "regular"),
        [extraStarts],
    );

    // An older server sends names only; counts by id would silently read as "1".
    const slotsMissingIds =
        (allSlots.data?.length ?? 0) > 0 && (allSlots.data ?? []).every((slot) => !slot.teacherId);

    const load = useMemo(() => {
        if (!selected || !draft.teacherId) return null;
        const name = teacherName.get(draft.teacherId);
        if (!name) return null;
        const day = selected.day.charAt(0).toUpperCase() + selected.day.slice(1);
        const others = (allSlots.data ?? []).filter(
            (slot) =>
                slot.teacherId === draft.teacherId &&
                !(
                    slot.day === day &&
                    slot.period.startsWith(selected.start) &&
                    slot.sectionId === sectionId
                ),
        );
        // Regular and extra classes are counted apart, and a kind is only shown when
        // the teacher holds at least one class of it (this period included).
        const thisKind = kindOf(selected.start);
        const dayLabel = DAYS.find((x) => x.value === selected.day)?.label ?? "";
        const kindLoads = (["regular", "extra"] as const)
            .map((kind) => {
                const perDay = DAYS.map((d) => {
                    const full = d.value.charAt(0).toUpperCase() + d.value.slice(1);
                    const count =
                        others.filter(
                            (slot) => slot.day === full && kindOf(slot.period.slice(0, 5)) === kind,
                        ).length + (kind === thisKind && d.value === selected.day ? 1 : 0);
                    return { label: d.label, count };
                });
                const week = perDay.reduce((sum, d) => sum + d.count, 0);
                const dayCount = perDay.find((d) => d.label === dayLabel)?.count ?? 0;
                const limit = dayTotals[kind];
                return {
                    kind,
                    perDay,
                    week,
                    dayCount,
                    limit,
                    // One short of the day's total already counts (regular and extra alike).
                    over: limit > 0 && dayCount >= Math.max(limit - 1, 1),
                };
            })
            .filter((item) => item.week > 0);
        return { name, dayLabel, kindLoads };
    }, [selected, draft.teacherId, teacherName, allSlots.data, sectionId, kindOf, dayTotals]);

    /** Save the slot; a different teacher than the course's must be confirmed first. */
    function requestSave() {
        if (!selected || !draft.classroomSubjectId || !draft.teacherId) {
            toast.push("error", "Pick a subject and a teacher first");
            return;
        }
        // No Course teacher yet: the pick is only for this slot, nothing changes hands.
        const courseTeacher = courseTeacherOf(draft.classroomSubjectId);
        if (courseTeacher && draft.teacherId !== courseTeacher) {
            if (!canAssignTeacher) {
                toast.push(
                    "error",
                    "Only someone who can assign course teachers may put a different teacher on this subject",
                );
                return;
            }
            setConfirmTeacher(true);
            return;
        }
        void saveSlot(false);
    }

    async function saveSlot(changeTeacher: boolean) {
        if (!selected || !draft.classroomSubjectId || !draft.teacherId) {
            toast.push("error", "Pick a subject and a teacher first");
            return;
        }
        setBusy(true);
        try {
            const existing = findPeriod(selected.day, selected.start);
            await save(
                {
                    sectionId,
                    classroomSubjectId: draft.classroomSubjectId,
                    teacherId: draft.teacherId,
                    dayOfWeek: selected.day,
                    startTime: selected.start,
                    endTime: selected.end,
                    room: draft.room || null,
                },
                existing?.id,
            );
            if (changeTeacher) {
                // The slot is saved first (a clash is the likely failure); then the
                // subject itself changes hands, so the Course tab agrees.
                await assignCourseTeacher(draft.classroomSubjectId, {
                    teacherId: draft.teacherId,
                });
                await Promise.all([
                    queryClient.invalidateQueries({ queryKey: ["classroom"] }),
                    queryClient.invalidateQueries({ queryKey: ["teachers"] }),
                    queryClient.invalidateQueries({ queryKey: ["course"] }),
                ]);
            }
            toast.push("success", `${existing ? "Updated" : "Added"} the ${selected.start} slot`);
            setSelected(null);
            setConfirmTeacher(false);
        } catch (error) {
            setConfirmTeacher(false);
            // A clash answers 409 with the teacher or the class already there - shown as
            // it arrived, because the server's sentence is the useful one.
            toast.push("error", errorMessage(error, "Could not save the slot"));
        } finally {
            setBusy(false);
        }
    }

    async function clearSlot() {
        if (!selected) return;
        const existing = findPeriod(selected.day, selected.start);
        if (!existing) {
            setSelected(null);
            return;
        }
        setBusy(true);
        try {
            await clear(existing.id);
            toast.push("info", "Slot cleared");
            setSelected(null);
        } catch (error) {
            toast.push("error", errorMessage(error, "Could not clear the slot"));
        } finally {
            setBusy(false);
        }
    }

    if (loading || bell.isPending) return <Spinner />;

    return (
        <div>
            <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                <div className="text-muted-foreground flex items-center gap-4 text-xs">
                    <span className="flex items-center gap-1.5">
                        <i className="tt-badge tt-badge-s tt-badge-static">S</i> Subject teacher
                    </span>
                    <span className="flex items-center gap-1.5">
                        <i className="tt-badge tt-badge-t tt-badge-static">T</i> Temporary teacher
                    </span>
                </div>
                {canEdit && (
                    <Button variant="primary" size="sm" onClick={() => setSetupOpen((v) => !v)}>
                        {setupOpen ? "Close period setup" : "Set up periods & breaks"}
                    </Button>
                )}
            </div>

            {canEdit && setupOpen && (
                <Card
                    title={setupMode === "period" ? "Period setup" : "Extra classes setup"}
                    action={
                        <select
                            aria-label="Choose setup"
                            className="border-input bg-background text-foreground h-9 rounded-md border px-3 text-sm shadow-sm"
                            value={setupMode}
                            onChange={(e) => setSetupMode(e.target.value as "period" | "extra")}
                        >
                            <option value="period">Period setup</option>
                            <option value="extra">Extra classes setup</option>
                        </select>
                    }
                >
                    {setupMode === "period" ? (
                        <SetupFields
                            draft={setup}
                            onChange={setSetupEdit}
                            countLabel="Number of periods"
                            startLabel="Day starts at"
                            minCount={1}
                            maxCount={12}
                            prefix="P"
                        />
                    ) : (
                        <SetupFields
                            draft={extra}
                            onChange={setExtraEdit}
                            countLabel="Number of extra classes (E1, E2…)"
                            startLabel="Extra classes start at"
                            minCount={0}
                            maxCount={8}
                            prefix="E"
                            showPosition
                        />
                    )}
                    <p className="text-muted-foreground mb-2 text-xs">
                        This is the school-wide day: saving applies the same period timings to every
                        class, and periods already placed move to the new times.
                    </p>
                    <div className="modal-actions">
                        <Button variant="ghost" onClick={() => setSetupOpen(false)} disabled={busy}>
                            Cancel
                        </Button>
                        <Button variant="primary" onClick={saveSetup} disabled={busy}>
                            {busy ? "Saving…" : "Save period setup"}
                        </Button>
                    </div>
                </Card>
            )}

            <div className="table-wrap">
                <table className="tt-table tt-week">
                    <thead>
                        <tr>
                            <th className="tt-day">Period</th>
                            {DAYS.map((day) => (
                                <th key={day.value} className="tt-dayhead">
                                    {day.label}
                                    {partialOff.has(day.weekday) && !offDays.has(day.weekday) && (
                                        <span>some weeks off</span>
                                    )}
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
                                    <td colSpan={DAYS.length} className="tt-cell tt-break">
                                        Break
                                    </td>
                                ) : (
                                    DAYS.map((day) => {
                                        if (offDays.has(day.weekday)) {
                                            return (
                                                <td
                                                    key={`${day.value}-${row.key}`}
                                                    className="tt-off"
                                                >
                                                    Week off
                                                </td>
                                            );
                                        }
                                        const slot = findPeriod(day.value, row.start);
                                        const name = slot
                                            ? subjectName.get(slot.classroomSubjectId)
                                            : undefined;
                                        const courseTeacher = slot
                                            ? courseTeacherOf(slot.classroomSubjectId)
                                            : "";
                                        // S: the Course's subject teacher. T: someone else, for now.
                                        const isSubjectTeacher = Boolean(
                                            slot &&
                                            courseTeacher &&
                                            slot.teacherId === courseTeacher,
                                        );
                                        return (
                                            <td key={`${day.value}-${row.key}`}>
                                                {slot && name ? (
                                                    <button
                                                        type="button"
                                                        className={`tt-cell ${colorFor(name)}`}
                                                        disabled={!canEdit}
                                                        onClick={() =>
                                                            openCell(day.value, row.start, row.end)
                                                        }
                                                    >
                                                        <i
                                                            className={`tt-badge ${isSubjectTeacher ? "tt-badge-s" : "tt-badge-t"}`}
                                                            title={
                                                                isSubjectTeacher
                                                                    ? "Subject teacher"
                                                                    : "Temporary teacher"
                                                            }
                                                        >
                                                            {isSubjectTeacher ? "S" : "T"}
                                                        </i>
                                                        <b>{name}</b>
                                                        <span>
                                                            {teacherName.get(slot.teacherId) ??
                                                                "Unassigned"}
                                                        </span>
                                                        {slot.room && <span>{slot.room}</span>}
                                                    </button>
                                                ) : canEdit ? (
                                                    <button
                                                        type="button"
                                                        className="tt-cell tt-empty"
                                                        onClick={() =>
                                                            openCell(day.value, row.start, row.end)
                                                        }
                                                    >
                                                        +
                                                    </button>
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

            {canEdit && selected && (
                <div ref={editRef} className="scroll-mt-4">
                    <Card title={`Edit · ${selected.day} ${selected.start}-${selected.end}`}>
                        {clash && <p className="auth-error">⚠️ {clash}</p>}
                        <div className="form-grid">
                            <Select
                                label="Subject"
                                value={draft.classroomSubjectId}
                                onChange={(e) =>
                                    setDraft({
                                        ...draft,
                                        classroomSubjectId: e.target.value,
                                        teacherId: courseTeacherOf(e.target.value),
                                    })
                                }
                            >
                                {subjects.length === 0 && <option value="">No subjects yet</option>}
                                {subjects.map((subject) => (
                                    <option key={subject.id} value={subject.id}>
                                        {subject.name}
                                    </option>
                                ))}
                            </Select>
                            <Select
                                label="Teacher"
                                hint={
                                    courseTeacherOf(draft.classroomSubjectId)
                                        ? undefined
                                        : "No teacher assigned for this subject in Course - pick any teacher to temporarily assign."
                                }
                                value={draft.teacherId}
                                onChange={(e) => setDraft({ ...draft, teacherId: e.target.value })}
                            >
                                <option value="">Select</option>
                                {teachers.map((teacher) => (
                                    <option key={teacher.employeeId} value={teacher.employeeId}>
                                        {teacher.name}
                                    </option>
                                ))}
                            </Select>
                        </div>
                        {draft.teacherId && (
                            <p className="mb-2 text-xs">
                                <span
                                    className={`tt-badge-inline ${
                                        draft.teacherId ===
                                        courseTeacherOf(draft.classroomSubjectId)
                                            ? "tt-badge-s"
                                            : "tt-badge-t"
                                    }`}
                                >
                                    {draft.teacherId === courseTeacherOf(draft.classroomSubjectId)
                                        ? "Subject teacher"
                                        : "Temporary teacher"}
                                </span>
                            </p>
                        )}
                        {allSlots.isError && (
                            <p className="auth-error mb-2 text-xs">
                                Could not read the school-wide timetable, so the counts below only
                                include this period.
                            </p>
                        )}
                        {slotsMissingIds && (
                            <p className="auth-error mb-2 text-xs">
                                The server is an older version (no teacher ids in the timetable), so
                                the counts are wrong. Restart the backend and reload this page.
                            </p>
                        )}
                        {load && (
                            <div className="text-muted-foreground mb-3 text-xs">
                                <p>
                                    <b className="text-foreground">{load.name}</b>:{" "}
                                    {load.kindLoads
                                        .map(
                                            (item) =>
                                                `${KIND_LABEL[item.kind]}: ${load.dayLabel} ${item.dayCount} of ${item.limit} · week ${item.week}`,
                                        )
                                        .join(", ")}
                                </p>
                                {load.kindLoads
                                    .filter((item) => item.over)
                                    .map((item) => (
                                        <p
                                            key={item.kind}
                                            className="tt-over-note mt-1 font-semibold"
                                        >
                                            Overloaded: {load.dayLabel} {item.dayCount} of{" "}
                                            {item.limit} {item.kind} class(es) that day,{" "}
                                            {item.limit - item.dayCount > 0
                                                ? `only ${item.limit - item.dayCount} free period left.`
                                                : "no free period left."}
                                        </p>
                                    ))}
                                {load.kindLoads.map((item) => (
                                    <p key={item.kind} className="mt-1">
                                        {KIND_LABEL[item.kind]}:{" "}
                                        {item.perDay
                                            .map((d) => `${d.label} ${d.count}`)
                                            .join(" · ")}
                                    </p>
                                ))}
                            </div>
                        )}
                        <div className="modal-actions">
                            <Button
                                variant="ghost"
                                onClick={() => setSelected(null)}
                                disabled={busy}
                            >
                                Cancel
                            </Button>
                            {canClear && (
                                <Button
                                    variant="danger"
                                    size="sm"
                                    onClick={clearSlot}
                                    disabled={busy}
                                >
                                    Clear slot
                                </Button>
                            )}
                            <Button variant="primary" onClick={requestSave} disabled={busy}>
                                {busy ? "Saving…" : "Save slot"}
                            </Button>
                        </div>
                    </Card>
                </div>
            )}

            <Modal
                open={confirmTeacher && Boolean(handover)}
                title={
                    courseTeacherOf(draft.classroomSubjectId)
                        ? "Change the subject teacher?"
                        : "Assign the subject teacher?"
                }
                onClose={() => setConfirmTeacher(false)}
            >
                {handover && (
                    <div className="space-y-3 text-sm">
                        <p>
                            <b>{handover.name}</b> already has <b>{handover.already}</b> period(s) a
                            week. With this one that becomes <b>{handover.already + 1}</b>.
                        </p>
                        <p>
                            {handover.name} will now be the teacher of <b>{handover.subject}</b> for{" "}
                            {classLabel}, so this class&rsquo;s other {handover.subject} periods and
                            its course are taken by them too.
                        </p>
                        <div className="modal-actions">
                            <Button
                                variant="ghost"
                                onClick={() => setConfirmTeacher(false)}
                                disabled={busy}
                            >
                                Cancel
                            </Button>
                            <Button
                                variant="primary"
                                onClick={() => void saveSlot(true)}
                                disabled={busy}
                            >
                                {busy ? "Saving…" : "Yes, change teacher"}
                            </Button>
                        </div>
                    </div>
                )}
            </Modal>
        </div>
    );
}
