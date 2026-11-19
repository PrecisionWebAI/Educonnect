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
} from "@/components/ui";
import { DialogFooter } from "@/components/ui/dialog";
import { useToast } from "@/components/ui/toast";
import { errorMessage } from "@/lib/api/client";
import { createChapter, updateChapter } from "@/services";
import type { CourseChapter, CourseSubject } from "@/types";

/**
 * Add or edit one chapter of a subject's plan.
 *
 * A chapter is **class-level**: saving it here shows it in every section of the class,
 * and each section keeps its own tick. The date is the plan's target, not a booking; a
 * chapter without one is simply "not planned" and never counts as behind.
 */
export default function ChapterEditorDialog({
    subject,
    chapter,
    open,
    onOpenChange,
}: {
    subject: CourseSubject | null;
    chapter: CourseChapter | null;
    open: boolean;
    onOpenChange: (open: boolean) => void;
}) {
    const queryClient = useQueryClient();
    const toast = useToast();
    const [name, setName] = useState("");
    const [plannedDate, setPlannedDate] = useState("");
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (!open) return;
        setName(chapter?.name ?? "");
        setPlannedDate(chapter?.plannedDate ?? "");
        setError(null);
    }, [open, chapter]);

    async function submit() {
        if (!subject?.classroomSubjectId) {
            setError("Add this subject to the section before planning its chapters.");
            return;
        }
        const trimmed = name.trim();
        if (!trimmed) {
            setError("Type the chapter's name.");
            return;
        }

        setSaving(true);
        setError(null);
        try {
            if (chapter) {
                await updateChapter(chapter.chapterId, {
                    name: trimmed,
                    plannedDate: plannedDate || null,
                });
                toast.push("success", `${trimmed} updated`);
            } else {
                await createChapter(subject.classroomSubjectId, {
                    name: trimmed,
                    plannedDate: plannedDate || null,
                });
                toast.push("success", `${trimmed} added to the plan`);
            }
            await queryClient.invalidateQueries({ queryKey: ["course"] });
            await queryClient.invalidateQueries({ queryKey: ["classroom"] });
            onOpenChange(false);
        } catch (cause) {
            setError(errorMessage(cause, "Could not save the chapter."));
        } finally {
            setSaving(false);
        }
    }

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-lg">
                <DialogHeader>
                    <DialogTitle>
                        {chapter ? "Edit chapter" : "Add chapter"}
                        {subject ? ` · ${subject.subject}` : ""}
                    </DialogTitle>
                </DialogHeader>

                <div className="space-y-3">
                    <Input
                        label="Chapter name"
                        placeholder="e.g. The French Revolution"
                        value={name}
                        onChange={(event) => setName(event.target.value)}
                        hint="Every section of this class reads the same chapter list."
                    />
                    <Input
                        label="Planned date"
                        type="date"
                        value={plannedDate}
                        onChange={(event) => setPlannedDate(event.target.value)}
                        hint="Optional. A past date that is not finished marks the chapter behind plan."
                    />

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
                    <Button onClick={submit} loading={saving}>
                        {chapter ? "Save chapter" : "Add chapter"}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
