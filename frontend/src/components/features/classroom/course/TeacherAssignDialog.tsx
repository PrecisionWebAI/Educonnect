"use client";

import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
    Button,
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    Input,
    Select,
} from "@/components/ui";
import { DialogFooter } from "@/components/ui/dialog";
import { useToast } from "@/components/ui/toast";
import { errorMessage } from "@/lib/api/client";
import { useApiQuery } from "@/lib/api/use-api-query";
import { assignCourseTeacher, getTeacherOptions } from "@/services";
import type { CourseSubject } from "@/types";

function today(): string {
    return new Date().toISOString().slice(0, 10);
}

/**
 * Assign or change the teacher of one section subject.
 *
 * The date is the **effective** date, not a booking date: the server closes the open
 * assignment the day before and opens a new row. That is why changing a teacher never
 * rewrites the chapters the old teacher finished.
 *
 * The person list is the server's active teachers (a leaver, a deactivated account and a
 * non-teaching role are not options). A workload warning is shown as an `info` toast
 * after saving - it asks the office to review the timetable, it does not undo the save.
 */
export default function TeacherAssignDialog({
    subject,
    open,
    onOpenChange,
}: {
    subject: CourseSubject | null;
    open: boolean;
    onOpenChange: (open: boolean) => void;
}) {
    const queryClient = useQueryClient();
    const toast = useToast();
    const teachers = useApiQuery(["classroom", "teachers"], getTeacherOptions, {
        enabled: open,
    });

    const [teacherId, setTeacherId] = useState("");
    const [effectiveFrom, setEffectiveFrom] = useState(today());
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (!open) return;
        setTeacherId(subject?.currentTeacherId ?? "");
        setEffectiveFrom(today());
        setError(null);
    }, [open, subject]);

    async function submit() {
        if (!subject?.classroomSubjectId) {
            setError("Add this subject to the section before assigning a teacher.");
            return;
        }
        if (!teacherId) {
            setError("Choose a teacher.");
            return;
        }

        setSaving(true);
        setError(null);
        try {
            const result = await assignCourseTeacher(subject.classroomSubjectId, {
                teacherId,
                effectiveFrom: effectiveFrom || null,
            });
            await queryClient.invalidateQueries({ queryKey: ["course"] });
            await queryClient.invalidateQueries({ queryKey: ["classroom"] });
            toast.push("success", `${result.teacher} teaches ${subject.subject}`);
            if (result.warning) toast.push("info", result.warning);
            onOpenChange(false);
        } catch (cause) {
            setError(errorMessage(cause, "Could not assign the teacher."));
        } finally {
            setSaving(false);
        }
    }

    const options = teachers.data ?? [];

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-lg">
                <DialogHeader>
                    <DialogTitle>
                        {subject?.currentTeacher ? "Change teacher" : "Assign teacher"}
                        {subject ? ` · ${subject.subject}` : ""}
                    </DialogTitle>
                </DialogHeader>

                <div className="space-y-3">
                    <Select
                        label="Teacher"
                        value={teacherId}
                        onChange={(event) => setTeacherId(event.target.value)}
                    >
                        <option value="">Select a teacher</option>
                        {options.map((option) => (
                            <option key={option.employeeId} value={option.employeeId}>
                                {option.name}
                            </option>
                        ))}
                    </Select>
                    {options.length === 0 && (
                        <p style={{ color: "var(--muted)", fontSize: "0.8rem" }}>
                            No active teachers in this school yet. Hire or reactivate a teacher
                            first.
                        </p>
                    )}

                    <Input
                        label="Effective from"
                        type="date"
                        value={effectiveFrom}
                        onChange={(event) => setEffectiveFrom(event.target.value)}
                        hint="The previous teacher's assignment closes the day before. Their completed chapters stay theirs."
                    />

                    {subject && subject.teachers.length > 0 && (
                        <p style={{ color: "var(--muted)", fontSize: "0.8rem" }}>
                            Current: {subject.currentTeacher ?? "nobody"} · history of{" "}
                            {subject.teachers.length} assignment
                            {subject.teachers.length === 1 ? "" : "s"} kept.
                        </p>
                    )}

                    {error && (
                        <p className="text-sm text-red-500" role="alert">
                            {error}
                        </p>
                    )}
                </div>

                <DialogFooter>
                    <Button variant="outline" onClick={() => onOpenChange(false)} disabled={saving}>
                        Cancel
                    </Button>
                    <Button onClick={submit} loading={saving} disabled={options.length === 0}>
                        {subject?.currentTeacher ? "Change teacher" : "Assign teacher"}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
