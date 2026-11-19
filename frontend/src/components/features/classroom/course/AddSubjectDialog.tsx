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
import { addSectionSubject, getAvailableSubjects } from "@/services";

const CUSTOM = "__custom__";

/**
 * Add Subject: pick one from the school's list, or type a new name.
 *
 * The dropdown is the **server's** answer (`available-subjects`): the master subjects
 * that this section does not have this session. A custom name joins the master list as
 * well, so the next section can pick it from the dropdown instead of typing it again.
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
    const available = useApiQuery(
        ["course", "available", sectionId],
        () => getAvailableSubjects(sectionId),
        { enabled: open },
    );

    const [choice, setChoice] = useState("");
    const [customName, setCustomName] = useState("");
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const options = available.data ?? [];
    const custom = choice === CUSTOM || (options.length === 0 && choice === "");

    useEffect(() => {
        if (!open) {
            setChoice("");
            setCustomName("");
            setError(null);
        }
    }, [open]);

    async function submit() {
        setError(null);
        const name = customName.trim();
        if (custom && !name) {
            setError("Type the subject's name.");
            return;
        }
        if (!custom && !choice) {
            setError("Choose a subject.");
            return;
        }

        setSaving(true);
        try {
            await addSectionSubject(sectionId, custom ? { name } : { subjectId: choice });
            await queryClient.invalidateQueries({ queryKey: ["course"] });
            await queryClient.invalidateQueries({ queryKey: ["academics", "subjects"] });
            toast.push("success", custom ? `${name} added to this section` : "Subject added");
            onOpenChange(false);
        } catch (cause) {
            setError(errorMessage(cause, "Could not add the subject."));
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
                    <Select
                        label="Subject"
                        value={custom ? CUSTOM : choice}
                        onChange={(event) => setChoice(event.target.value)}
                    >
                        <option value="">Select a subject</option>
                        {options.map((subject) => (
                            <option key={subject.id} value={subject.id}>
                                {subject.name}
                            </option>
                        ))}
                        <option value={CUSTOM}>Custom subject…</option>
                    </Select>

                    {custom && (
                        <Input
                            label="Custom subject"
                            placeholder="e.g. English 1"
                            value={customName}
                            onChange={(event) => setCustomName(event.target.value)}
                            hint="A new name joins the school's subject list too."
                        />
                    )}

                    {options.length === 0 && !custom && (
                        <p style={{ color: "var(--muted)", fontSize: "0.8rem" }}>
                            Every active subject is already in this section. Use a custom name if
                            the school needs another one.
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
                    <Button onClick={submit} loading={saving}>
                        Add Subject
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
