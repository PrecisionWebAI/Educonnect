"use client";

import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Button, Modal, Spinner, Textarea } from "@/components/ui";
import { useToast } from "@/components/ui/toast";
import { errorMessage } from "@/lib/api/client";
import { useApiQuery } from "@/lib/api/use-api-query";
import { getSyllabus, setSyllabus } from "@/services";
import { EXAM_LIST_KEY } from "./useExamPlan";

// One subject's syllabus, in a pop-up.
//
// The syllabus is **free text** - what will come in that subject's exam, in the subject
// teacher's own words. A reader sees it as written; a writer (the subject teacher, the
// class teacher, leadership) edits it here. The server decides who may write; `editable`
// only decides whether this pop-up offers the box.

export default function SyllabusDialog({
    paperId,
    subject,
    editable,
    onClose,
}: {
    /** The paper whose syllabus to show, or `null` while the pop-up is closed. */
    paperId: string | null;
    subject: string;
    /** Offer the writing box (the caller's own right to write, from the paper). */
    editable: boolean;
    onClose: () => void;
}) {
    return (
        <Modal open={paperId !== null} title={`Syllabus — ${subject}`} onClose={onClose}>
            {paperId !== null && (
                <SyllabusBody paperId={paperId} editable={editable} onClose={onClose} />
            )}
        </Modal>
    );
}

function SyllabusBody({
    paperId,
    editable,
    onClose,
}: {
    paperId: string;
    editable: boolean;
    onClose: () => void;
}) {
    const query = useApiQuery(["exams", "syllabus", paperId], () => getSyllabus(paperId));
    if (query.isPending) return <Spinner />;
    if (query.isError || !query.data) {
        return (
            <p className="text-sm text-red-500" role="alert">
                {errorMessage(query.error, "Could not read the syllabus.")}
            </p>
        );
    }
    const data = query.data;
    return data.canEdit && editable ? (
        <Editor
            key={data.paperId}
            paperId={paperId}
            initial={data.syllabusText ?? ""}
            subtitle={`${data.examName} · ${data.section}`}
            onClose={onClose}
        />
    ) : (
        <div className="space-y-3 text-sm">
            <p className="text-muted-foreground text-xs">
                {data.examName} · {data.section}
            </p>
            {data.syllabusText ? (
                <p className="whitespace-pre-wrap">{data.syllabusText}</p>
            ) : (
                <p className="text-muted-foreground">The syllabus has not been added yet.</p>
            )}
            <div className="modal-actions">
                <Button variant="ghost" onClick={onClose}>
                    Close
                </Button>
            </div>
        </div>
    );
}

function Editor({
    paperId,
    initial,
    subtitle,
    onClose,
}: {
    paperId: string;
    initial: string;
    subtitle: string;
    onClose: () => void;
}) {
    const queryClient = useQueryClient();
    const toast = useToast();
    const [text, setText] = useState(initial);
    const [saving, setSaving] = useState(false);

    async function save() {
        setSaving(true);
        try {
            await setSyllabus(paperId, text);
            await Promise.all([
                queryClient.invalidateQueries({ queryKey: ["exams", "syllabus", paperId] }),
                queryClient.invalidateQueries({ queryKey: EXAM_LIST_KEY }),
            ]);
            toast.push("success", "Syllabus saved.");
            onClose();
        } catch (cause) {
            toast.push("error", errorMessage(cause, "Could not save the syllabus"));
        } finally {
            setSaving(false);
        }
    }

    return (
        <div className="space-y-3">
            <p className="text-muted-foreground text-xs">{subtitle}</p>
            <Textarea
                label="What will come in this exam"
                value={text}
                onChange={(event) => setText(event.target.value)}
                rows={8}
                maxLength={5000}
                placeholder="Chapters, topics, or anything the students should prepare."
            />
            <div className="modal-actions">
                <Button variant="ghost" onClick={onClose} disabled={saving}>
                    Cancel
                </Button>
                <Button variant="primary" onClick={save} disabled={saving}>
                    {saving ? "Saving…" : "Save syllabus"}
                </Button>
            </div>
        </div>
    );
}
