"use client";

import { Button, Input, Modal, Select } from "@/components/ui";
import { CLASS_NAMES } from "@/lib/constants/classes";
import { FREQUENCIES } from "@/services";
import type { FeeFrequency } from "@/types";
import type { FeeHeadDraft } from "./useFeesStructure";

// Create / edit a fee head in the `feestructure` master.

export default function FeeHeadModal({
    open,
    editing,
    draft,
    onChange,
    onClose,
    onSubmit,
}: {
    open: boolean;
    editing: boolean;
    draft: FeeHeadDraft;
    onChange: (draft: FeeHeadDraft) => void;
    onClose: () => void;
    onSubmit: () => void;
}) {
    return (
        <Modal
            open={open}
            title={editing ? "Edit Fee Head" : "New Fee Head"}
            onClose={onClose}
        >
            <div className="space-y-4">
                <Input
                    label="Fee head"
                    placeholder="e.g. Tuition Fee"
                    value={draft.head}
                    onChange={(e) => onChange({ ...draft, head: e.target.value })}
                />
                <Select
                    label="Applies to"
                    value={draft.className}
                    onChange={(e) => onChange({ ...draft, className: e.target.value })}
                >
                    {CLASS_NAMES.map((c) => (
                        <option key={c} value={c}>
                            {c}
                        </option>
                    ))}
                </Select>
                <Select
                    label="Frequency"
                    value={draft.frequency}
                    onChange={(e) =>
                        onChange({ ...draft, frequency: e.target.value as FeeFrequency })
                    }
                >
                    {FREQUENCIES.map((f) => (
                        <option key={f} value={f}>
                            {f}
                        </option>
                    ))}
                </Select>
                <Input
                    label="Amount (₹)"
                    type="number"
                    min={0}
                    value={String(draft.amount)}
                    onChange={(e) => onChange({ ...draft, amount: Number(e.target.value) || 0 })}
                />
                <Input
                    label="Due on"
                    placeholder="e.g. 10th of month"
                    value={draft.dueDay}
                    onChange={(e) => onChange({ ...draft, dueDay: e.target.value })}
                />
                <div className="flex justify-end gap-2">
                    <Button variant="outline" onClick={onClose}>
                        Cancel
                    </Button>
                    <Button variant="primary" onClick={onSubmit}>
                        {editing ? "Save changes" : "Add Fee Head"}
                    </Button>
                </div>
            </div>
        </Modal>
    );
}
