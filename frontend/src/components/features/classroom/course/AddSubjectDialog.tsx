"use client";

import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Button, Dialog, DialogContent, DialogHeader, DialogTitle, Input } from "@/components/ui";
import { DialogFooter } from "@/components/ui/dialog";
import { useToast } from "@/components/ui/toast";
import { ApiError, errorMessage } from "@/lib/api/client";
import { addSectionSubject } from "@/services";

/**
 * Add a subject that belongs to this classroom only.
 *
 * There is no school-wide picker. The same name can be added to another section,
 * and renaming this row will never touch that other section.
 */
export default function AddSubjectDialog({
    sectionId,
    open,
    onOpenChange,
}: {
    sectionId: string;
    open: boolean;
    onOpenChange: (open: boolean) => void;
}) {
    const queryClient = useQueryClient();
    const toast = useToast();
    const [name, setName] = useState("");
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);

    async function submit() {
        setError(null);
        const clean = name.trim();
        if (!clean) {
            setError("Type the subject's name.");
            return;
        }

        setSaving(true);
        try {
            await addSectionSubject(sectionId, {
                name: clean,
            });
            await queryClient.invalidateQueries({ queryKey: ["course"] });
            toast.push("success", `${clean} added to this classroom`);
            onOpenChange(false);
        } catch (cause) {
            if (
                cause instanceof ApiError &&
                cause.status === 409 &&
                /academic (year|session)/i.test(cause.message)
            ) {
                setError("No academic year is open. Open it from the top bar, then try again.");
            } else {
                setError(errorMessage(cause, "Could not add the subject."));
            }
        } finally {
            setSaving(false);
        }
    }

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-lg">
                <DialogHeader>
                    <DialogTitle>Add Subject</DialogTitle>
                </DialogHeader>

                <div className="space-y-3">
                    <Input
                        label="Subject name"
                        placeholder="e.g. Computer Science"
                        value={name}
                        onChange={(event) => setName(event.target.value)}
                        hint="This name belongs to this classroom only."
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
                        Add Subject
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
