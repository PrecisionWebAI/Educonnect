"use client";

import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
    Badge,
    Button,
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    Input,
    Spinner,
    Table,
    type Column,
} from "@/components/ui";
import { useToast } from "@/components/ui/toast";
import { errorMessage } from "@/lib/api/client";
import { useApiQuery } from "@/lib/api/use-api-query";
import { titleCase } from "@/lib/format";
import { getSubjects, updateSubject } from "@/services";
import type { SubjectRow } from "@/types";

/**
 * The school's subject master, opened from the Course tab.
 *
 * A rename or a retirement happens here, once for the whole school: every section and
 * every paper reads the same row, so the office does not have to repeat it per class.
 * A retired subject is hidden from the pickers but stays on the rows that already point
 * at it (chapters, papers, homework) - the table says "Retired" rather than deleting it.
 */
export default function SubjectMasterDialog({
    open,
    onOpenChange,
}: {
    open: boolean;
    onOpenChange: (open: boolean) => void;
}) {
    const queryClient = useQueryClient();
    const toast = useToast();
    const subjects = useApiQuery(["academics", "subjects", "all"], () => getSubjects(true), {
        enabled: open,
    });

    const [editingId, setEditingId] = useState<string | null>(null);
    const [draft, setDraft] = useState("");
    const [busyId, setBusyId] = useState<string | null>(null);

    async function refresh() {
        await queryClient.invalidateQueries({ queryKey: ["academics", "subjects"] });
        await queryClient.invalidateQueries({ queryKey: ["course"] });
    }

    async function save(row: SubjectRow) {
        const name = draft.trim();
        if (!name) {
            toast.push("error", "A subject needs a name.");
            return;
        }
        setBusyId(row.id);
        try {
            await updateSubject(row.id, { name });
            await refresh();
            toast.push("success", "Subject renamed");
            setEditingId(null);
        } catch (cause) {
            toast.push("error", errorMessage(cause, "Could not rename the subject."));
        } finally {
            setBusyId(null);
        }
    }

    async function toggle(row: SubjectRow) {
        setBusyId(row.id);
        try {
            await updateSubject(row.id, { isActive: !row.isActive });
            await refresh();
            toast.push(
                "success",
                row.isActive
                    ? `${titleCase(row.name)} retired from the pickers`
                    : `${titleCase(row.name)} is active again`,
            );
        } catch (cause) {
            toast.push("error", errorMessage(cause, "Could not update the subject."));
        } finally {
            setBusyId(null);
        }
    }

    const columns: Column<SubjectRow>[] = [
        {
            key: "name",
            header: "Subject",
            render: (row) =>
                editingId === row.id ? (
                    <Input
                        value={draft}
                        onChange={(event) => setDraft(event.target.value)}
                        className="h-8 max-w-60"
                        aria-label={`Rename ${titleCase(row.name)}`}
                    />
                ) : (
                    <span className="font-medium">{titleCase(row.name)}</span>
                ),
        },
        { key: "code", header: "Code" },
        {
            key: "status",
            header: "Status",
            render: (row) => (
                <Badge tone={row.isActive ? "green" : "muted"}>
                    {row.isActive ? "Active" : "Retired"}
                </Badge>
            ),
        },
        {
            key: "actions",
            header: "",
            align: "right",
            render: (row) => (
                <div className="flex items-center justify-end gap-1">
                    {editingId === row.id ? (
                        <>
                            <Button size="sm" onClick={() => save(row)} loading={busyId === row.id}>
                                Save
                            </Button>
                            <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => setEditingId(null)}
                                disabled={busyId === row.id}
                            >
                                Cancel
                            </Button>
                        </>
                    ) : (
                        <>
                            <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => {
                                    setEditingId(row.id);
                                    setDraft(row.name);
                                }}
                            >
                                Rename
                            </Button>
                            <Button
                                size="sm"
                                variant={row.isActive ? "ghost" : "outline"}
                                onClick={() => toggle(row)}
                                disabled={busyId === row.id}
                            >
                                {row.isActive ? "Retire" : "Activate"}
                            </Button>
                        </>
                    )}
                </div>
            ),
        },
    ];

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-2xl">
                <DialogHeader>
                    <DialogTitle>School Subjects</DialogTitle>
                </DialogHeader>

                <p style={{ color: "var(--muted)", fontSize: "0.82rem" }}>
                    One list for the whole school. A retired subject stays on the plans, papers and
                    homework that already use it; it only leaves the pickers.
                </p>

                {subjects.isPending ? (
                    <Spinner />
                ) : subjects.error ? (
                    <p className="text-sm text-red-500" role="alert">
                        {errorMessage(subjects.error, "Could not load the subject list.")}
                    </p>
                ) : (
                    <Table
                        columns={columns}
                        rows={subjects.data ?? []}
                        rowKey={(row) => row.id}
                        empty="No subjects in this school's list yet."
                    />
                )}
            </DialogContent>
        </Dialog>
    );
}
