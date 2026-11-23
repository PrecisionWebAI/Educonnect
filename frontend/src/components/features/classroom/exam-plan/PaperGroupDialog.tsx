"use client";

import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Button, Dialog, DialogContent, DialogHeader, DialogTitle, Input } from "@/components/ui";
import { DialogFooter } from "@/components/ui/dialog";
import { useToast } from "@/components/ui/toast";
import { errorMessage } from "@/lib/api/client";
import { amount, chapterNameList, figureText } from "@/lib/exams/view";
import { updatePaperGroup } from "@/services";
import type { ExamPaperGroup, ExamPaperPlan } from "@/types";
import { EXAM_LIST_KEY } from "./useExamPlan";

/**
 * Edit what every section of a shared question paper has in common: its title, its
 * chapters (by name) and what it is out of.
 *
 * Once any section has marks, or a paper is published, the shared paper is frozen -
 * the question paper has been sat, so changing its title, chapters or maximum would
 * change what the results mean. The dialog says so and offers the way out: a section
 * can still be given a paper of its own from the date sheet.
 */
export default function PaperGroupDialog({
    group,
    papers,
    open,
    onOpenChange,
}: {
    group: ExamPaperGroup | null;
    /** The papers of this group, for the sections line and the current maximum. */
    papers: ExamPaperPlan[];
    open: boolean;
    onOpenChange: (open: boolean) => void;
}) {
    if (!group) return null;
    // Remount per group so the fields start from the saved values, not the last edit.
    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-lg">
                <PaperGroupForm
                    key={group.id}
                    group={group}
                    papers={papers}
                    onClose={() => onOpenChange(false)}
                />
            </DialogContent>
        </Dialog>
    );
}

function PaperGroupForm({
    group,
    papers,
    onClose,
}: {
    group: ExamPaperGroup;
    papers: ExamPaperPlan[];
    onClose: () => void;
}) {
    const queryClient = useQueryClient();
    const toast = useToast();
    const [title, setTitle] = useState(group.displayTitle ?? "");
    const [chapters, setChapters] = useState(group.chapters.join(", "));
    const [maxMarks, setMaxMarks] = useState(papers[0] ? figureText(papers[0].maxMarks) : "");
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);

    async function save() {
        const maximum = amount(maxMarks);
        if (maximum === null || maximum <= 0) {
            setError("The paper must be out of more than zero.");
            return;
        }
        setSaving(true);
        setError(null);
        try {
            await updatePaperGroup(group.id, {
                displayTitle: title.trim() === "" ? null : title.trim(),
                chapters: chapterNameList(chapters),
                maxMarks: maximum,
            });
            await queryClient.invalidateQueries({ queryKey: EXAM_LIST_KEY });
            toast.push("success", "The shared paper was updated for every section.");
            onClose();
        } catch (cause) {
            setError(errorMessage(cause, "Could not update the shared paper."));
        } finally {
            setSaving(false);
        }
    }

    return (
        <>
            <DialogHeader>
                <DialogTitle>Shared paper</DialogTitle>
            </DialogHeader>

            <p className="text-muted-foreground text-sm">
                Sat by {papers.map((paper) => paper.section).join(", ")}. Dates and rooms stay per
                section.
            </p>

            {group.locked && (
                <p className="rounded-xl border border-amber-500/40 bg-amber-500/5 p-3 text-sm">
                    Marks are entered or published, so this shared paper can no longer be edited. To
                    change one section&apos;s paper, give that section its own from the date sheet.
                </p>
            )}

            <div className="space-y-3">
                <Input
                    label="Title on the date sheet"
                    value={title}
                    onChange={(event) => setTitle(event.target.value)}
                    placeholder="Leave empty to show each section's own subject name"
                    disabled={group.locked}
                />
                <Input
                    label="Chapters (names, comma separated)"
                    value={chapters}
                    onChange={(event) => setChapters(event.target.value)}
                    disabled={group.locked}
                />
                <Input
                    label="Out of"
                    type="number"
                    min="0"
                    step="0.5"
                    value={maxMarks}
                    onChange={(event) => setMaxMarks(event.target.value)}
                    disabled={group.locked}
                />
            </div>

            {error && (
                <p className="text-sm text-red-500" role="alert">
                    {error}
                </p>
            )}

            <DialogFooter>
                <Button variant="outline" onClick={onClose} disabled={saving}>
                    Close
                </Button>
                <Button onClick={save} loading={saving} disabled={group.locked}>
                    Save for every section
                </Button>
            </DialogFooter>
        </>
    );
}
