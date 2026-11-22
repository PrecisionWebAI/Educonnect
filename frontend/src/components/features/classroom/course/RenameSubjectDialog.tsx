"use client";

import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Button, Dialog, DialogContent, DialogHeader, DialogTitle, Input } from "@/components/ui";
import { DialogFooter } from "@/components/ui/dialog";
import { useToast } from "@/components/ui/toast";
import { ApiError, errorMessage } from "@/lib/api/client";
import { titleCase } from "@/lib/format";
import { renameCourseSubject } from "@/services";
import type { CourseSubject } from "@/types";

/**
 * Rename one classroom subject.
 *
 * The server checks duplicates inside this classroom and academic year only. A
 * successful save invalidates the Course read; no other section is refetched or
 * changed.
 */
export default function RenameSubjectDialog({
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
    const [name, setName] = useState(titleCase(subject?.name));
    const [code, setCode] = useState(subject?.code ?? "");
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);

    async function submit() {
        if (!subject?.classroomSubjectId) return;
        const clean = name.trim();
        if (!clean) {
            setError("Type the subject's name.");
            return;
        }

        setSaving(true);
        setError(null);
        try {
            await renameCourseSubject(subject.classroomSubjectId, {
                name: clean,
                code: code.trim() || null,
            });
            await queryClient.invalidateQueries({ queryKey: ["course"] });
            toast.push("success", `${clean} renamed in this classroom`);
            onOpenChange(false);
        } catch (cause) {
            if (cause instanceof ApiError && cause.status === 409) {
                setError("Another active subject in this classroom already has that name.");
            } else {
                setError(errorMessage(cause, "Could not rename the subject."));
            }
        } finally {
            setSaving(false);
        }
    }

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-lg">
                <DialogHeader>
                    <DialogTitle>Edit Subject</DialogTitle>
                </DialogHeader>

                <div className="space-y-3">
                    <Input
                        label="Subject name"
                        value={name}
                        onChange={(event) => setName(event.target.value)}
                        hint="Changing this name affects this classroom only."
                        autoFocus
                    />
                    <Input
                        label="Code (optional)"
                        value={code}
                        onChange={(event) => setCode(event.target.value)}
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
                        Save
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
