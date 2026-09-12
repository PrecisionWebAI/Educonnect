"use client";

// ============================================================
// BasicsStep — blueprint §1.1 (Step 1: Basic Details)
// ============================================================

import { Input, Select } from "@/components/ui";
import type { PaperBuilderApi } from "../usePaperBuilder";

const SUBJECTS = ["Science", "Mathematics", "English", "Social Science", "Hindi"];
const BOARDS = ["CBSE", "State Board", "ICSE"];
const EXAM_TYPES = ["Unit Test", "Half-Yearly", "Weekly Quiz", "Annual"];
const LANGUAGES = ["English", "Hindi", "Bilingual (EN+HI)"];

export default function BasicsStep({ builder }: { builder: PaperBuilderApi }) {
    const b = builder.state.basics;
    return (
        <div className="form-grid">
            <Input
                label="Paper title"
                value={b.title}
                onChange={(e) => builder.setBasics({ title: e.target.value })}
            />
            <Select
                label="Class"
                value={b.className}
                onChange={(e) => builder.setBasics({ className: e.target.value })}
            >
                {["6", "7", "8", "9", "10", "11", "12"].map((c) => (
                    <option key={c} value={c}>
                        Class {c}
                    </option>
                ))}
            </Select>
            <Select
                label="Subject"
                value={b.subject}
                onChange={(e) => builder.setBasics({ subject: e.target.value })}
            >
                {SUBJECTS.map((s) => (
                    <option key={s} value={s}>
                        {s}
                    </option>
                ))}
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
                onChange={(e) => builder.setBasics({ durationMinutes: Number(e.target.value) })}
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
            <Input
                label="Chapters (comma separated)"
                value={b.chapters.join(", ")}
                onChange={(e) =>
                    builder.setBasics({
                        chapters: e.target.value.split(",").map((c) => c.trim()).filter(Boolean),
                    })
                }
            />
        </div>
    );
}