"use client";
import { useState } from "react";
import { Button, Input, Label, Modal } from "@/components/ui";
import { errorMessage } from "@/lib/api/client";
import type { WorkloadRuleInput } from "@/services";
import type { WorkloadRuleRow } from "./useWorkload";

/**
 * The school's full week, in periods.
 *
 * Deliberately a **modal, not a form on the page**: this one number is the
 * denominator of every percentage on the tab, so changing it is a decision the
 * office should take deliberately and see the whole of - not something that
 * drifts while somebody edits a nearby field.
 *
 * The component is mounted only while the modal is open, so its state starts from
 * the stored rule each time (no effect syncing a prop into state, which is how a
 * cancelled edit used to leak back in).
 */
export default function WorkloadCapacityModal({
    rule,
    weekSlots,
    busy,
    error,
    onSave,
    onClose,
}: {
    rule: WorkloadRuleRow | null;
    /** What the timetable actually runs - the number the dialog is compared to. */
    weekSlots: number;
    busy: boolean;
    error: unknown;
    onSave: (input: WorkloadRuleInput) => Promise<boolean>;
    onClose: () => void;
}) {
    const [weeklyPeriods, setWeeklyPeriods] = useState(
        String(rule?.weeklyPeriods ?? (weekSlots > 0 ? weekSlots : 24)),
    );
    const [overloadPercent, setOverloadPercent] = useState(String(rule?.overloadPercent ?? 100));
    const [underloadPercent, setUnderloadPercent] = useState(String(rule?.underloadPercent ?? 60));

    async function submit() {
        const saved = await onSave({
            weeklyPeriods: Number(weeklyPeriods),
            overloadPercent: Number(overloadPercent),
            underloadPercent: Number(underloadPercent),
        });
        if (saved) onClose();
    }

    return (
        <Modal open title="Capacity Rule" onClose={onClose}>
            <p className="text-muted-foreground mb-4 text-sm">
                A full week, in teaching periods. Every utilisation figure on this tab is a share of
                this number, and the timetable currently runs{" "}
                {weekSlots > 0 ? `${weekSlots} ${weekSlots === 1 ? "slot" : "slots"}` : "no slots"}{" "}
                a week.
            </p>

            <div className="grid gap-3">
                <div>
                    <Label htmlFor="weekly-periods">Weekly Periods</Label>
                    <Input
                        id="weekly-periods"
                        type="number"
                        min={1}
                        max={100}
                        value={weeklyPeriods}
                        onChange={(event) => setWeeklyPeriods(event.target.value)}
                    />
                </div>
                <div>
                    <Label htmlFor="overload-percent">Overload %</Label>
                    <Input
                        id="overload-percent"
                        type="number"
                        min={50}
                        max={300}
                        value={overloadPercent}
                        onChange={(event) => setOverloadPercent(event.target.value)}
                    />
                    <p className="text-muted-foreground mt-1 text-xs">
                        Above this share of the week a person is marked Overloaded.
                    </p>
                </div>
                <div>
                    <Label htmlFor="underload-percent">Under-Load %</Label>
                    <Input
                        id="underload-percent"
                        type="number"
                        min={0}
                        max={100}
                        value={underloadPercent}
                        onChange={(event) => setUnderloadPercent(event.target.value)}
                    />
                    <p className="text-muted-foreground mt-1 text-xs">
                        Below this share a person is marked Light. It must stay under the overload
                        line.
                    </p>
                </div>
            </div>

            {error !== null && (
                <p className="mt-3 text-sm" style={{ color: "var(--danger, #b42318)" }}>
                    {errorMessage(error, "The capacity rule was not saved.")}
                </p>
            )}

            <div className="mt-5 flex justify-end gap-2">
                <Button variant="ghost" onClick={onClose}>
                    Cancel
                </Button>
                <Button loading={busy} onClick={submit}>
                    Save Capacity
                </Button>
            </div>
        </Modal>
    );
}
