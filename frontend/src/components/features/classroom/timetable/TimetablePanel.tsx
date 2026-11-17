"use client";

import { useMemo, useState } from "react";
import { Button, Card, Input, Select, Spinner } from "@/components/ui";
import { useToast } from "@/components/ui/toast";
import { errorMessage } from "@/lib/api/client";
import { usePermission } from "@/hooks/use-authorization";
import { getBellSchedule, getTimetable } from "@/services";
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
const DAYS: { value: string; label: string }[] = [
    { value: "monday", label: "Mon" },
    { value: "tuesday", label: "Tue" },
    { value: "wednesday", label: "Wed" },
    { value: "thursday", label: "Thu" },
    { value: "friday", label: "Fri" },
    { value: "saturday", label: "Sat" },
];

/** Subject colours, picked from the name so a subject keeps its colour. */
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
    subjects: { id: string; name: string }[];
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
    const [draft, setDraft] = useState({ subjectId: "", teacherId: "", room: "" });
    const [busy, setBusy] = useState(false);

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
                slot.teacher === name &&
                slot.className !== classLabel,
        );
        return other
            ? `${name} is already teaching ${other.className} at ${selected.start}.`
            : null;
    }, [selected, draft.teacherId, teacherName, allSlots.data, classLabel]);

    function openCell(day: string, start: string, end: string) {
        const existing = findPeriod(day, start);
        setSelected({ day, start, end });
        setDraft({
            subjectId: existing?.subjectId ?? subjects[0]?.id ?? "",
            teacherId: existing?.teacherId ?? "",
            room: existing?.room ?? "",
        });
    }

    async function saveSlot() {
        if (!selected || !draft.subjectId || !draft.teacherId) {
            toast.push("error", "Pick a subject and a teacher first");
            return;
        }
        setBusy(true);
        try {
            const existing = findPeriod(selected.day, selected.start);
            await save(
                {
                    sectionId,
                    subjectId: draft.subjectId,
                    teacherId: draft.teacherId,
                    dayOfWeek: selected.day,
                    startTime: selected.start,
                    endTime: selected.end,
                    room: draft.room || null,
                },
                existing?.id,
            );
            toast.push("success", `${existing ? "Updated" : "Added"} the ${selected.start} slot`);
            setSelected(null);
        } catch (error) {
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
            <p className="text-muted-foreground mb-3 text-xs">
                {classLabel}&rsquo;s week · {periods.length} period(s) scheduled · {rows.length}{" "}
                row(s) in the school day
                {canEdit ? " · click a cell to add or change it" : " · read only"}
            </p>

            <div className="table-wrap">
                <table className="tt-table">
                    <thead>
                        <tr>
                            <th>Period</th>
                            {DAYS.map((day) => (
                                <th key={day.value}>{day.label}</th>
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
                                        const slot = findPeriod(day.value, row.start);
                                        const name = slot
                                            ? subjectName.get(slot.subjectId)
                                            : undefined;
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
                <Card title={`Edit · ${selected.day} ${selected.start}-${selected.end}`}>
                    {clash && <p className="auth-error">⚠️ {clash}</p>}
                    <div className="form-grid">
                        <Select
                            label="Subject"
                            value={draft.subjectId}
                            onChange={(e) => setDraft({ ...draft, subjectId: e.target.value })}
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
                            value={draft.teacherId}
                            onChange={(e) => setDraft({ ...draft, teacherId: e.target.value })}
                        >
                            <option value="">— select —</option>
                            {teachers.map((teacher) => (
                                <option key={teacher.employeeId} value={teacher.employeeId}>
                                    {teacher.name}
                                </option>
                            ))}
                        </Select>
                        <Input
                            label="Room"
                            value={draft.room}
                            onChange={(e) => setDraft({ ...draft, room: e.target.value })}
                            placeholder="e.g. Room 12"
                        />
                    </div>
                    <div className="modal-actions">
                        <Button variant="ghost" onClick={() => setSelected(null)} disabled={busy}>
                            Cancel
                        </Button>
                        {canClear && (
                            <Button variant="danger" size="sm" onClick={clearSlot} disabled={busy}>
                                Clear slot
                            </Button>
                        )}
                        <Button variant="primary" onClick={saveSlot} disabled={busy}>
                            {busy ? "Saving…" : "Save slot"}
                        </Button>
                    </div>
                </Card>
            )}
        </div>
    );
}
