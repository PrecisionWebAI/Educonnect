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
    Spinner,
    Textarea,
} from "@/components/ui";
import { DialogFooter } from "@/components/ui/dialog";
import { useToast } from "@/components/ui/toast";
import { errorMessage } from "@/lib/api/client";
import { useApiQuery } from "@/lib/api/use-api-query";
import { canReject } from "@/lib/course/lesson-plan";
import {
    approveLessonPlan,
    approveManyLessonPlans,
    getReviewCount,
    getReviewQueue,
    rejectLessonPlan,
} from "@/services";
import type { ReviewRow } from "@/types";

/**
 * The principal's review list.
 *
 * Only **submitted** weeks appear; clicking one shows the whole six-field plan so the
 * decision is made on the teacher's words, not on a title. Approve is one click; reject
 * needs a reason. Rows can be selected and approved together - a row that changed in
 * another tab comes back as "skipped" instead of failing the batch.
 */
export default function LessonPlanReviewPanel({
    sectionId,
    open,
    onOpenChange,
}: {
    sectionId?: string | null;
    open: boolean;
    onOpenChange: (open: boolean) => void;
}) {
    const queryClient = useQueryClient();
    const toast = useToast();
    const [selected, setSelected] = useState<Set<string>>(new Set());
    const [viewing, setViewing] = useState<ReviewRow | null>(null);
    const [rejectTarget, setRejectTarget] = useState<ReviewRow | null>(null);
    const [reason, setReason] = useState("");
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const queue = useApiQuery(
        ["course", "reviews", sectionId ?? "all"],
        () => getReviewQueue({ sectionId: sectionId ?? null, limit: 100 }),
        { enabled: open },
    );
    const count = useApiQuery(
        ["course", "reviews", "count", sectionId ?? "all"],
        () => getReviewCount(sectionId ?? null),
        { enabled: open },
    );
    const rows = queue.data ?? [];

    async function refresh() {
        await queryClient.invalidateQueries({ queryKey: ["course"] });
        await queryClient.invalidateQueries({ queryKey: ["classroom"] });
        setSelected(new Set());
    }

    async function approve(row: ReviewRow) {
        setSaving(true);
        try {
            await approveLessonPlan(row.planId, row.expectedVersion);
            await refresh();
            toast.push("success", `${row.subject} · Week ${row.weekNo} approved`);
            if (viewing?.planId === row.planId) setViewing(null);
        } catch (cause) {
            toast.push("error", errorMessage(cause, "Could not approve the week."));
        } finally {
            setSaving(false);
        }
    }

    async function approveSelected() {
        const items = rows
            .filter((row) => selected.has(row.planId))
            .map((row) => ({
                planId: row.planId,
                expectedVersion: row.expectedVersion,
            }));
        if (items.length === 0) return;
        setSaving(true);
        try {
            const result = await approveManyLessonPlans(items);
            await refresh();
            toast.push("success", `${result.approved.length} week(s) approved`);
            if (result.skipped.length > 0) {
                toast.push(
                    "info",
                    `${result.skipped.length} week(s) skipped - they changed in another tab.`,
                );
            }
        } catch (cause) {
            toast.push("error", errorMessage(cause, "Could not approve the selection."));
        } finally {
            setSaving(false);
        }
    }

    async function submitRejection() {
        if (!rejectTarget) return;
        if (!canReject(reason)) {
            setError("Write the reason - the teacher needs to know what to correct.");
            return;
        }
        setSaving(true);
        setError(null);
        try {
            await rejectLessonPlan(
                rejectTarget.planId,
                reason.trim(),
                rejectTarget.expectedVersion,
            );
            await refresh();
            toast.push(
                "success",
                `${rejectTarget.subject} · Week ${rejectTarget.weekNo} rejected`,
            );
            setRejectTarget(null);
            setReason("");
        } catch (cause) {
            setError(errorMessage(cause, "Could not reject the week."));
        } finally {
            setSaving(false);
        }
    }

    function toggle(planId: string) {
        setSelected((current) => {
            const next = new Set(current);
            if (next.has(planId)) next.delete(planId);
            else next.add(planId);
            return next;
        });
    }

    return (
        <>
            <Dialog open={open} onOpenChange={onOpenChange}>
                <DialogContent className="sm:max-w-4xl">
                    <DialogHeader>
                        <div className="flex flex-wrap items-center justify-between gap-2">
                            <DialogTitle>Lesson plan reviews</DialogTitle>
                            <Badge tone="amber">
                                {count.data ?? rows.length} submitted
                            </Badge>
                        </div>
                    </DialogHeader>

                    <div className="flex flex-wrap items-center justify-between gap-2">
                        <Button
                            size="sm"
                            variant="ghost"
                            onClick={() =>
                                setSelected(
                                    selected.size === rows.length
                                        ? new Set()
                                        : new Set(rows.map((row) => row.planId)),
                                )
                            }
                            disabled={rows.length === 0}
                        >
                            {selected.size === rows.length && rows.length > 0
                                ? "Clear selection"
                                : "Select all"}
                        </Button>
                        <Button
                            size="sm"
                            onClick={approveSelected}
                            disabled={selected.size === 0 || saving}
                            loading={saving}
                        >
                            Approve selected ({selected.size})
                        </Button>
                    </div>

                    {queue.isPending ? (
                        <Spinner />
                    ) : rows.length === 0 ? (
                        <p className="text-muted-foreground text-sm">
                            No submitted week is waiting for review.
                        </p>
                    ) : (
                        <div className="max-h-[60vh] space-y-2 overflow-y-auto">
                            {rows.map((row) => (
                                <div key={row.planId} className="rounded-lg border p-3">
                                    <div className="flex flex-wrap items-start justify-between gap-2">
                                        <label className="flex min-w-0 items-start gap-2">
                                            <input
                                                type="checkbox"
                                                checked={selected.has(row.planId)}
                                                onChange={() => toggle(row.planId)}
                                                className="mt-1"
                                            />
                                            <span className="flex flex-col">
                                                <span className="font-semibold">
                                                    {row.subject} · Week {row.weekNo}
                                                </span>
                                                <span className="text-muted-foreground text-xs">
                                                    {row.label} · {row.startDate} to{" "}
                                                    {row.endDate} · version {row.version}
                                                </span>
                                                <span className="text-muted-foreground text-xs">
                                                    {row.submittedBy ?? "A teacher"}
                                                </span>
                                            </span>
                                        </label>
                                        <Badge tone="amber">{row.status}</Badge>
                                    </div>
                                    <div className="mt-2 flex flex-wrap justify-end gap-1">
                                        <Button
                                            size="sm"
                                            variant="ghost"
                                            onClick={() => setViewing(row)}
                                        >
                                            View plan
                                        </Button>
                                        <Button
                                            size="sm"
                                            variant="ghost"
                                            disabled={saving}
                                            onClick={() => approve(row)}
                                        >
                                            Approve
                                        </Button>
                                        <Button
                                            size="sm"
                                            variant="danger"
                                            disabled={saving}
                                            onClick={() => {
                                                setRejectTarget(row);
                                                setReason("");
                                                setError(null);
                                            }}
                                        >
                                            Reject
                                        </Button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </DialogContent>
            </Dialog>

            <Dialog
                open={viewing !== null}
                onOpenChange={(next) => {
                    if (!next) setViewing(null);
                }}
            >
                <DialogContent className="sm:max-w-3xl">
                    <DialogHeader>
                        <DialogTitle>
                            {viewing?.subject} · Week {viewing?.weekNo}
                        </DialogTitle>
                    </DialogHeader>
                    {viewing && (
                        <div className="space-y-3 text-sm">
                            <p className="text-muted-foreground">
                                {viewing.label} · {viewing.startDate} to {viewing.endDate} ·{" "}
                                {viewing.submittedBy ?? "A teacher"}
                            </p>
                            {(
                                [
                                    ["Topics", viewing.topics],
                                    ["Learning objectives", viewing.learningObjectives],
                                    ["Activities", viewing.activities],
                                    ["Homework", viewing.homework],
                                    ["Resources", viewing.resources],
                                    ["Assessment", viewing.assessment],
                                ] as const
                            ).map(([label, value]) => (
                                <div key={label}>
                                    <h4 className="font-semibold">{label}</h4>
                                    <p className="whitespace-pre-wrap">{value || "—"}</p>
                                </div>
                            ))}
                        </div>
                    )}
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setViewing(null)}>
                            Close
                        </Button>
                        <Button
                            variant="danger"
                            disabled={saving}
                            onClick={() => {
                                if (!viewing) return;
                                setRejectTarget(viewing);
                                setViewing(null);
                                setReason("");
                                setError(null);
                            }}
                        >
                            Reject…
                        </Button>
                        <Button
                            disabled={saving}
                            loading={saving}
                            onClick={() => viewing && approve(viewing)}
                        >
                            Approve
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            <Dialog
                open={rejectTarget !== null}
                onOpenChange={(next) => {
                    if (!next) setRejectTarget(null);
                }}
            >
                <DialogContent className="sm:max-w-lg">
                    <DialogHeader>
                        <DialogTitle>
                            Reject · {rejectTarget?.subject} Week {rejectTarget?.weekNo}
                        </DialogTitle>
                    </DialogHeader>
                    <Textarea
                        label="Reason *"
                        rows={4}
                        value={reason}
                        onChange={(event) => setReason(event.target.value)}
                        hint="The teacher sees this reason and can correct the week."
                    />
                    {error && (
                        <p className="text-sm text-red-500" role="alert">
                            {error}
                        </p>
                    )}
                    <DialogFooter>
                        <Button
                            variant="outline"
                            onClick={() => setRejectTarget(null)}
                            disabled={saving}
                        >
                            Cancel
                        </Button>
                        <Button
                            variant="danger"
                            onClick={submitRejection}
                            loading={saving}
                            disabled={!canReject(reason)}
                        >
                            Reject week
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </>
    );
}