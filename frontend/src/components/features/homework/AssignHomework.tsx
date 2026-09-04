"use client";
import { useState } from "react";
import { Button, Select, Input, Textarea, Card } from "@/components/ui";
import { useToast } from "@/components/ui/toast";

export default function AssignHomework() {
    const [subject, setSubject] = useState("Mathematics");
    const [className, setClassName] = useState("10-A");
    const [title, setTitle] = useState("");
    const [desc, setDesc] = useState("");
    const [due, setDue] = useState("Tomorrow");
    const { push } = useToast();

    function handleSubmit() {
        if (!title) {
            push("error", "Title is required");
            return;
        }
        push("success", `Assigned "${title}" to ${className}`);
        setTitle("");
        setDesc("");
    }

    return (
        <Card title="Assign New Homework">
            <div className="form-grid">
                <Select
                    label="Subject"
                    value={subject}
                    onChange={(e) => setSubject(e.target.value)}
                >
                    {["Mathematics", "Physics", "Chemistry", "English"].map((s) => (
                        <option key={s}>{s}</option>
                    ))}
                </Select>
                <Select
                    label="Class"
                    value={className}
                    onChange={(e) => setClassName(e.target.value)}
                >
                    {["10-A", "10-B", "9-A", "9-B"].map((c) => (
                        <option key={c}>{c}</option>
                    ))}
                </Select>
                <Input
                    label="Title"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="e.g. Trigonometry worksheet"
                />
                <Select label="Due" value={due} onChange={(e) => setDue(e.target.value)}>
                    {["Today", "Tomorrow", "Fri", "Mon"].map((d) => (
                        <option key={d}>{d}</option>
                    ))}
                </Select>
                <div style={{ gridColumn: "1 / -1" }}>
                    <Textarea
                        label="Description"
                        value={desc}
                        onChange={(e) => setDesc(e.target.value)}
                        placeholder="Details of the assignment..."
                    />
                </div>
            </div>
            <div className="modal-actions">
                <Button variant="primary" onClick={handleSubmit}>
                    Assign Homework
                </Button>
            </div>
        </Card>
    );
}
