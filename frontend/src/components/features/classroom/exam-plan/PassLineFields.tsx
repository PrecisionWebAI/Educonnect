"use client";

import { useState } from "react";
import { Input, Select } from "@/components/ui";
import {
    choosePassBy,
    cleanGradeInput,
    editPassMarks,
    rungOf,
    passLineIssue,
    passMarksPercentText,
    type GradeMode,
    type LadderRung,
    type PassBy,
    type PassLineDraft,
} from "@/lib/exams/marking";
import { amount } from "@/lib/exams/view";

// The pass line of one paper, inside the date-sheet row or the class-test form:
//
//   Pass by [Marks | Grade]
//     Marks -> [ 33 ]  40%        (33% of the total pre-filled; the small % follows the number)
//     Grade -> [ D ▾ ]            (a grade of the ladder, or a custom one)
//              starts at [ 35 ] % (asked only when the grade is not on the ladder)
//
// It owns no state: the parent holds the `PassLineDraft` and the total, so the rules
// (pre-fill, the small percent, what keeps Save disabled) live in `lib/exams/marking.ts`
// where `node --test` covers them. The parent calls `followTotal` when the total changes
// and `passLineIssue` to decide whether Save is allowed.

const CUSTOM = "__custom__";

export default function PassLineFields({
    total,
    value,
    onChange,
    ladder,
    disabled = false,
    compact = false,
}: {
    /** The paper's total marks as the form holds it (text), or "" while empty. */
    total: string;
    value: PassLineDraft;
    onChange: (next: PassLineDraft) => void;
    /** The school's ladder (`GET /exams/marking-defaults`). */
    ladder: LadderRung[];
    disabled?: boolean;
    /** Tighter spacing for a table row. */
    compact?: boolean;
}) {
    const totalNumber = amount(total);
    const issue =
        value.passBy === "marks" && value.passMarks === ""
            ? null
            : passLineIssue(value, totalNumber, ladder);
    const percent = passMarksPercentText(value, totalNumber);
    // "Custom" is chosen on purpose (or the saved grade is not on the ladder).
    const [customPick, setCustomPick] = useState(false);
    const isCustom =
        customPick ||
        (value.passingGrade.trim() !== "" && rungOf(ladder, value.passingGrade) === undefined);

    return (
        <div className={`flex flex-wrap items-start ${compact ? "gap-2" : "gap-3"}`}>
            <div className="w-32">
                <Select
                    label={compact ? undefined : "Pass by"}
                    aria-label="Pass by"
                    value={value.passBy}
                    disabled={disabled}
                    onChange={(event) =>
                        onChange(choosePassBy(value, event.target.value as PassBy))
                    }
                >
                    <option value="marks">Marks</option>
                    <option value="grade">Grade</option>
                </Select>
            </div>

            {value.passBy === "marks" ? (
                <div className="flex items-end gap-2">
                    <div className="w-28">
                        <Input
                            label={compact ? undefined : "Passing marks"}
                            aria-label="Passing marks"
                            type="number"
                            min={0}
                            step="0.01"
                            inputMode="decimal"
                            value={value.passMarks}
                            disabled={disabled}
                            onChange={(event) => onChange(editPassMarks(value, event.target.value))}
                        />
                    </div>
                    {/* What percentage of the total that number is - follows the number live. */}
                    <span
                        className="text-muted-foreground pb-2 text-xs"
                        aria-live="polite"
                        title="Passing marks as a percentage of the total"
                    >
                        {percent}
                    </span>
                </div>
            ) : (
                <div className="flex items-end gap-2">
                    <div className="w-32">
                        <Select
                            label={compact ? undefined : "Passing grade"}
                            aria-label="Passing grade"
                            value={isCustom ? CUSTOM : value.passingGrade}
                            disabled={disabled}
                            onChange={(event) => {
                                const picked = event.target.value;
                                if (picked === CUSTOM) {
                                    setCustomPick(true);
                                    onChange({ ...value, passingGrade: "" });
                                } else {
                                    setCustomPick(false);
                                    onChange({
                                        ...value,
                                        passingGrade: picked,
                                        customMinPercent: "",
                                    });
                                }
                            }}
                        >
                            <option value="">Select</option>
                            {ladder.map((rung) => (
                                <option key={rung.grade} value={rung.grade}>
                                    {rung.grade}
                                </option>
                            ))}
                            <option value={CUSTOM}>Custom</option>
                        </Select>
                    </div>
                    {isCustom && (
                        <div className="w-20">
                            <Input
                                label={compact ? undefined : "Custom grade"}
                                aria-label="Custom grade"
                                placeholder="e.g. P"
                                maxLength={2}
                                className="uppercase"
                                value={value.passingGrade}
                                disabled={disabled}
                                onChange={(event) =>
                                    onChange({
                                        ...value,
                                        passingGrade: cleanGradeInput(event.target.value),
                                    })
                                }
                            />
                        </div>
                    )}
                </div>
            )}

            <div className="w-28">
                <Select
                    label={compact ? undefined : "Grade"}
                    aria-label="Grade column"
                    value={value.gradeMode}
                    disabled={disabled}
                    onChange={(event) =>
                        onChange({ ...value, gradeMode: event.target.value as GradeMode })
                    }
                >
                    <option value="na">NA</option>
                    <option value="auto">Auto</option>
                    <option value="manual">Manual</option>
                </Select>
            </div>

            {issue && (
                <p className="w-full text-[0.8rem] font-medium text-red-500" role="alert">
                    {issue}
                </p>
            )}
        </div>
    );
}
