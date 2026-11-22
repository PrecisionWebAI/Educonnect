"use client";

import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Button, Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui";
import { DialogFooter } from "@/components/ui/dialog";
import { useToast } from "@/components/ui/toast";
import { errorMessage } from "@/lib/api/client";
import { titleCase } from "@/lib/format";
import { copyChapters, getChapterSources } from "@/services";
import type { CourseChapterSource, CourseSubject } from "@/types";

/**
 * Copy the chapter list of another section of this class into this section.
 *
 * The server offers only sections of the same class and academic year. New chapters
 * are appended after the last one; a chapter whose name is already here is skipped and
 * reported. After the copy the two sections are independent.
 */
export default function CopyChaptersDialog({
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
    const [sources, setSources] = useState<CourseChapterSource[]>([]);
    const [sourceId, setSourceId] = useState("");
    const [loading, setLoading] = useState(false);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (!open || !subject?.classroomSubjectId) return;
        let alive = true;
        setLoading(true);
        setError(null);
        getChapterSources(subject.classroomSubjectId)
            .then((rows) => {
                if (!alive) return;
                setSources(rows);
                setSourceId(rows[0]?.classroomSubjectId ?? "");
            })
            .catch((cause) => {
                if (alive) setError(errorMessage(cause, "Could not load other sections."));
            })
            .finally(() => {
                if (alive) setLoading(false);
            });
        return () => {
            alive = false;
        };
    }, [open, subject?.classroomSubjectId]);

    async function submit() {
        if (!subject?.classroomSubjectId || !sourceId) return;
        setSaving(true);
        setError(null);
        try {
            const result = await copyChapters(subject.classroomSubjectId, {
                sourceClassroomSubjectId: sourceId,
            });
            await queryClient.invalidateQueries({ queryKey: ["course"] });
            const skipped =
                result.skipped.length > 0
                    ? ` · ${result.skipped.length} already here: ${result.skipped.join(", ")}`
                    : "";
            toast.push("success", `${result.copied} chapters copied${skipped}`);
            onOpenChange(false);
        } catch (cause) {
            setError(errorMessage(cause, "Could not copy the chapters."));
        } finally {
            setSaving(false);
        }
    }

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-lg">
                <DialogHeader>
                    <DialogTitle>Copy chapters · {titleCase(subject?.name)}</DialogTitle>
                </DialogHeader>

                {loading ? (
                    <p className="text-sm text-slate-500">Looking for another section…</p>
                ) : sources.length === 0 ? (
                    <p className="text-sm text-slate-500">
                        No other section of this class has chapters for this year yet. Add chapters
                        here instead.
                    </p>
                ) : (
                    <div className="space-y-3">
                        <label className="block text-sm font-medium">
                            Copy from
                            <select
                                className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm"
                                value={sourceId}
                                onChange={(event) => setSourceId(event.target.value)}
                            >
                                {sources.map((source) => (
                                    <option
                                        key={source.classroomSubjectId}
                                        value={source.classroomSubjectId}
                                    >
                                        {source.label} · {source.chapterCount} chapters
                                    </option>
                                ))}
                            </select>
                        </label>
                        <p className="text-xs text-slate-500">
                            Chapters are added after the last one here. Names already in this
                            section are skipped. Progress is not copied.
                        </p>
                    </div>
                )}

                {error && (
                    <p className="text-sm text-red-500" role="alert">
                        {error}
                    </p>
                )}

                <DialogFooter>
                    <Button variant="outline" onClick={() => onOpenChange(false)} disabled={saving}>
                        Cancel
                    </Button>
                    <Button onClick={submit} loading={saving} disabled={loading || !sourceId}>
                        Copy chapters
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
