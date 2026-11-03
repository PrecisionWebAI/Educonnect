"use client";

import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Button, Card, Input, Select, Textarea } from "@/components/ui";
import { useToast } from "@/components/ui/toast";
import { errorMessage } from "@/lib/api/client";
import { createHomework } from "@/services";

// Assign homework to **the class-section the page is showing**.
//
// The class is not a picker any more: it is the section you are in, and the
// subject/teacher come from that section, so the assignment can never be filed
// against a class the page is not about. Saving writes to `homeworkassignment`.

/** Tomorrow, as `YYYY-MM-DD` - the usual due date. */
function tomorrow(): string {
    const day = new Date();
    day.setDate(day.getDate() + 1);
    return day.toISOString().slice(0, 10);
}

export default function AssignHomework({
    sectionId,
    sectionLabel,
    subjects,
    teachers,
    defaultTeacherId,
}: {
    sectionId: string;
    sectionLabel: string;
    /** The subjects this school offers (id + name). */
    subjects: { id: string; name: string }[];
    /** Teachers who can be credited with the assignment. */
    teachers: { employeeId: string; name: string }[];
    /** The section's class teacher, preselected when there is one. */
    defaultTeacherId: string | null;
}) {
    const toast = useToast();
    const queryClient = useQueryClient();
    const [subjectId, setSubjectId] = useState(subjects[0]?.id ?? "");
    const [teacherId, setTeacherId] = useState(defaultTeacherId ?? teachers[0]?.employeeId ?? "");
    const [title, setTitle] = useState("");
    const [description, setDescription] = useState("");
    const [dueDate, setDueDate] = useState(tomorrow);
    const [busy, setBusy] = useState(false);

    const canAssign = Boolean(sectionId && subjectId && teacherId);

    async function handleSubmit() {
        if (!title.trim()) {
            toast.push("error", "Title is required");
            return;
        }
        if (!canAssign) {
            toast.push("error", "This class-section needs a subject and a teacher first");
            return;
        }
        setBusy(true);
        try {
            await createHomework({
                title: title.trim(),
                description: description.trim(),
                sectionId,
                subjectId,
                teacherId,
                dueDate,
            });
            await queryClient.invalidateQueries({ queryKey: ["homework"] });
            toast.push("success", `Assigned "${title.trim()}" to ${sectionLabel}`);
            setTitle("");
            setDescription("");
        } catch (error) {
            toast.push("error", errorMessage(error, "Could not assign the homework"));
        } finally {
            setBusy(false);
        }
    }

    return (
        <Card title={`Assign New Homework · ${sectionLabel}`}>
            <div className="form-grid">
                <Select
                    label="Subject"
                    value={subjectId}
                    onChange={(e) => setSubjectId(e.target.value)}
                >
                    {subjects.length === 0 && <option value="">No subjects yet</option>}
                    {subjects.map((subject) => (
                        <option key={subject.id} value={subject.id}>
                            {subject.name}
                        </option>
                    ))}
                </Select>
                <Select
                    label="Teacher"
                    value={teacherId}
                    onChange={(e) => setTeacherId(e.target.value)}
                >
                    {teachers.length === 0 && <option value="">No teachers yet</option>}
                    {teachers.map((teacher) => (
                        <option key={teacher.employeeId} value={teacher.employeeId}>
                            {teacher.name}
                        </option>
                    ))}
                </Select>
                <Input
                    label="Title"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="e.g. Trigonometry worksheet"
                />
                <Input
                    label="Due date"
                    type="date"
                    value={dueDate}
                    onChange={(e) => setDueDate(e.target.value)}
                />
                <div style={{ gridColumn: "1 / -1" }}>
                    <Textarea
                        label="Description"
                        rows={2}
                        value={description}
                        onChange={(e) => setDescription(e.target.value)}
                        placeholder="Details of the assignment..."
                    />
                </div>
            </div>
            <div className="modal-actions">
                <Button variant="primary" onClick={handleSubmit} disabled={busy}>
                    {busy ? "Assigning…" : "Assign Homework"}
                </Button>
            </div>
        </Card>
    );
}

