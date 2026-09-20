"use client";

// ============================================================
// BasicsStep — Step 1 "Basic Details". Paper identity fields,
// clean 2-col aligned grid. Board hata diya — uski jagah Exam
// Date. Chapters/sources Step 2 "Source" me hain.
// ============================================================

import { Input, Select } from "@/components/ui";
import type { PaperBuilderApi } from "../usePaperBuilder";
import { subjectsFor, useSourceMaster } from "../useSourceMaster";

const CLASSES = ["6", "7", "8", "9", "10", "11", "12"];
const EXAM_TYPES = ["Unit Test", "Half-Yearly", "Weekly Quiz", "Annual"];
const LANGUAGES = ["English", "Hindi", "Bilingual (EN+HI)"];
/** Standard subject options (domain enum — demo data nahi). Library me
 *  jo subjects saved hain woh inke saath merge ho jaate hain. */
const SUBJECTS = [
    "Science",
    "Mathematics",
    "English",
    "Hindi",
    "Social Science",
    "Computer Science",
    "Physics",
    "Chemistry",
    "Biology",
    "Environmental Studies",
];

function Field({
    label,
    children,
}: {
    label: string;
    children: React.ReactNode;
}) {
    return (
        <label className="flex min-w-0 flex-col gap-1">
            <span className="text-xs font-medium text-muted-foreground">{label}</span>
            {children}
        </label>
    );
}

export default function BasicsStep({ builder }: { builder: PaperBuilderApi }) {
    const b = builder.state.basics;
    const master = useSourceMaster();
    /** Library ke subjects + standard list ka union (duplicates hatakar). */
    const librarySubjects = subjectsFor(master.entries, b.className);
    const subjectOptions = Array.from(
        new Set([...librarySubjects, b.subject, ...SUBJECTS].filter(Boolean)),
    );

    return (
        <div className="grid gap-4">
            <div className="grid gap-4 sm:grid-cols-2">
                <Field label="Paper title">
                    <Input
                        value={b.title}
                        onChange={(e) => builder.setBasics({ title: e.target.value })}
                    />
                </Field>

                <Field label="Class">
                    <Select
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
                </Field>

                <Field label="Subject">
                    <Select
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
                </Field>

                <Field label="Exam type">
                    <Select
                        value={b.examType}
                        onChange={(e) => builder.setBasics({ examType: e.target.value })}
                    >
                        {EXAM_TYPES.map((s) => (
                            <option key={s} value={s}>
                                {s}
                            </option>
                        ))}
                    </Select>
                </Field>

                <Field label="Exam date">
                    <Input
                        type="date"
                        value={b.examDate}
                        onChange={(e) => builder.setBasics({ examDate: e.target.value })}
                    />
                </Field>

                <Field label="Language">
                    <Select
                        value={b.language}
                        onChange={(e) => builder.setBasics({ language: e.target.value })}
                    >
                        {LANGUAGES.map((s) => (
                            <option key={s} value={s}>
                                {s}
                            </option>
                        ))}
                    </Select>
                </Field>

                <Field label="Duration (minutes)">
                    <Input
                        type="number"
                        min={5}
                        value={String(b.durationMinutes)}
                        onChange={(e) =>
                            builder.setBasics({ durationMinutes: Number(e.target.value) })
                        }
                    />
                </Field>

                <Field label="Total marks">
                    <Input
                        type="number"
                        min={1}
                        max={200}
                        value={String(b.totalMarks)}
                        onChange={(e) => builder.setBasics({ totalMarks: Number(e.target.value) })}
                    />
                </Field>
            </div>
        </div>
    );
}