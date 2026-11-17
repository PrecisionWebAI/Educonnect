"use client";

import { useMemo, useState } from "react";
import { Button, Card, Select, Spinner, Textarea } from "@/components/ui";
import { DatePicker } from "@/components/ui/date-picker";
import { useToast } from "@/components/ui/toast";
import { useApiQuery } from "@/lib/api/use-api-query";
import { errorMessage } from "@/lib/api/client";
import { createDiaryLog, getSectionTimetable } from "@/services";

// "Write today's log" (Phase 9) - the small form the diary was missing.
//
// A line says **what was done** and, optionally, **which subject** and **which period**.
// The period list is the section's own timetable for the chosen weekday, so a Tuesday
// log offers Tuesday's slots and nothing else - picking "Monday 09:00" for a Tuesday was
// exactly the kind of entry the old free-text box produced.

/** `2026-11-17` -> `tuesday` (the backend's enum spelling). */
function weekdayOf(isoDate: string): string {
    const names = ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"];
    const day = new Date(`${isoDate}T00:00:00`).getDay();
    return names[Number.isNaN(day) ? 0 : day];
}

function today(): string {
    const now = new Date();
    const month = String(now.getMonth() + 1).padStart(2, "0");
    const day = String(now.getDate()).padStart(2, "0");
    return `${now.getFullYear()}-${month}-${day}`;
}

function hhmm(value: string): string {
    return value.slice(0, 5);
}

export default function WriteDailyLog({
    sectionId,
    classroomId,
    subjects,
    teacherId,
    onSaved,
}: {
    sectionId: string;
    /** The class-section's class, needed for `GET /timetable/class/{id}`. */
    classroomId: string;
    subjects: { id: string; name: string }[];
    /** Who is credited with the line - the class teacher when there is one. */
    teacherId: string | null;
    onSaved: () => void;
}) {
    const toast = useToast();
    const [date, setDate] = useState(today);
    const [subjectId, setSubjectId] = useState("");
    const [periodId, setPeriodId] = useState("");
    const [note, setNote] = useState("");
    const [busy, setBusy] = useState(false);

    const week = useApiQuery(
        ["classroom", "section", sectionId, "timetable"],
        () => getSectionTimetable(classroomId, sectionId),
        { enabled: Boolean(sectionId && classroomId) },
    );
    const subjectName = useMemo(
        () => new Map(subjects.map((subject) => [subject.id, subject.name])),
        [subjects],
    );
    const day = weekdayOf(date);
    const slots = useMemo(
        () => (week.data ?? []).filter((period) => period.dayOfWeek === day),
        [week.data, day],
    );

    async function save() {
        if (!note.trim()) {
            toast.push("error", "Say what the class did — the note is the line.");
            return;
        }
        if (!teacherId) {
            toast.push(
                "error",
                "This class-section needs a class teacher before it can keep a log.",
            );
            return;
        }
        setBusy(true);
        try {
            await createDiaryLog({
                sectionId,
                teacherId,
                periodId: periodId || null,
                subjectId: subjectId || null,
                date,
                note: note.trim(),
            });
            toast.push("success", "Log line saved.");
            setNote("");
            onSaved();
        } catch (cause) {
            toast.push("error", errorMessage(cause, "Could not write the log"));
        } finally {
            setBusy(false);
        }
    }

    if (week.isPending) return <Spinner />;

    return (
        <Card title="Write a log line">
            <div className="grid gap-3 sm:grid-cols-2">
                <DatePicker label="Day" value={date} onChange={setDate} />
                <Select
                    label="Subject"
                    value={subjectId}
                    onChange={(event) => setSubjectId(event.target.value)}
                    hint="Leave it empty for a line about the whole day."
                >
                    <option value="">Whole day</option>
                    {subjects.map((subject) => (
                        <option key={subject.id} value={subject.id}>
                            {subject.name}
                        </option>
                    ))}
                </Select>
                <Select
                    label="Period"
                    value={periodId}
                    onChange={(event) => setPeriodId(event.target.value)}
                    hint={`${slots.length} period${slots.length === 1 ? "" : "s"} on ${day}.`}
                >
                    <option value="">No single period</option>
                    {slots.map((period) => (
                        <option key={period.id} value={period.id}>
                            {hhmm(period.startTime)} - {hhmm(period.endTime)} ·{" "}
                            {subjectName.get(period.subjectId) ?? "Subject"}
                        </option>
                    ))}
                </Select>
                <div className="sm:col-span-2">
                    <Textarea
                        label="What was done"
                        rows={2}
                        value={note}
                        onChange={(event) => setNote(event.target.value)}
                        placeholder="Trigonometric ratios — exercise 8.2, doubts cleared."
                    />
                </div>
            </div>
            <div className="mt-3 flex justify-end">
                <Button onClick={save} loading={busy} disabled={busy}>
                    Save the line
                </Button>
            </div>
        </Card>
    );
}
