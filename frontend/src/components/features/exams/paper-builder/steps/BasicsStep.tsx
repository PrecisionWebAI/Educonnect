"use client";

// ============================================================
// BasicsStep — Step 1 "Basic Detail" (paper details only, §1.1).
// Chapters, sources and the save-a-chapter form live in their own
// Step 2 "Source" (SourceStep.tsx). Keeping this step lean lets the
// teacher set up the paper first, then pick chapter sources in the
// very next step.
// ============================================================

import { Input, Select } from "@/components/ui";
import type { PaperBuilderApi } from "../usePaperBuilder";
import { subjectsFor, useSourceMaster } from "../useSourceMaster";

const CLASSES = ["6", "7", "8", "9", "10", "11", "12"];
const BOARDS = ["CBSE", "State Board", "ICSE"];
const EXAM_TYPES = ["Unit Test", "Half-Yearly", "Weekly Quiz", "Annual"];
const LANGUAGES = ["English", "Hindi", "Bilingual (EN+HI)"];

export default function BasicsStep({ builder }: { builder: PaperBuilderApi }) {
    const b = builder.state.basics;
    const master = useSourceMaster();
    const subjectOptions = subjectsFor(master.entries, b.className);

    return (
        <div className="grid gap-3 rounded-md border p-3">
            <p className="text-sm font-medium">Paper details</p>
            <div className="form-grid">
                <Input
                    label="Paper title"
                    value={b.title}
                    onChange={(e) => builder.setBasics({ title: e.target.value })}
                />
                <Select
                    label="Class"
                    value={b.className}
                    onChange={(e) =>
                        builder.setBasics({
                            className: e.target.value,
                            subject:
                                subjectsFor(master.entries, e.target.value)[0] ?? b.subject,
                            chapters: [],
                        })
                    }
                >
                    {CLASSES.map((c) => (
                        <option key={c} value={c}>
                            Class {c}
                        </option>
                    ))}
                </Select>
                <Select
                    label="Subject"
                    value={b.subject}
                    onChange={(e) =>
                        builder.setBasics({ subject: e.target.value, chapters: [] })
                    }
                >
                    {subjectOptions.length > 0 ? (
                        subjectOptions.map((s) => (
                            <option key={s} value={s}>
                                {s}
                            </option>
                        ))
                    ) : (
                        <option value={b.subject}>{b.subject}</option>
                    )}
                </Select>
                <Select
                    label="Board"
                    value={b.board}
                    onChange={(e) => builder.setBasics({ board: e.target.value })}
                >
                    {BOARDS.map((s) => (
                        <option key={s} value={s}>
                            {s}
                        </option>
                    ))}
                </Select>
                <Select
                    label="Exam type"
                    value={b.examType}
                    onChange={(e) => builder.setBasics({ examType: e.target.value })}
                >
                    {EXAM_TYPES.map((s) => (
                        <option key={s} value={s}>
                            {s}
                        </option>
                    ))}
                </Select>
                <Select
                    label="Language"
                    value={b.language}
                    onChange={(e) => builder.setBasics({ language: e.target.value })}
                >
                    {LANGUAGES.map((s) => (
                        <option key={s} value={s}>
                            {s}
                        </option>
                    ))}
                </Select>
                <Input
                    label="Duration (minutes)"
                    type="number"
                    min={5}
                    value={String(b.durationMinutes)}
                    onChange={(e) =>
                        builder.setBasics({ durationMinutes: Number(e.target.value) })
                    }
                />
                <Input
                    label="Total marks (locks the Marks Contract)"
                    type="number"
                    min={1}
                    max={200}
                    value={String(b.totalMarks)}
                    hint="Everything must add up to this"
                    onChange={(e) => builder.setBasics({ totalMarks: Number(e.target.value) })}
                />
            </div>
            <p className="text-xs text-muted-foreground">
                Next step — <b>Source</b>: choose the chapters this paper covers.
            </p>
        </div>
    );
}