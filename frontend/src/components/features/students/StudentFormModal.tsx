"use client";

import { useState, type FormEvent } from "react";
import type { Student } from "@/types";
import { Button, Input, Modal, Select } from "@/components/ui";
import { EMPTY_FORM, type StudentFormValues } from "./useStudents";

// Add / Edit student modal. Form state lives here; parent only
// receives validated values on submit.
export default function StudentFormModal({
    open,
    editing,
    defaultAdmissionNo,
    onClose,
    onSubmit,
}: {
    open: boolean;
    editing: Student | null;
    defaultAdmissionNo: string;
    onClose: () => void;
    onSubmit: (values: StudentFormValues) => void;
}) {
    const [form, setForm] = useState<StudentFormValues>(EMPTY_FORM);

    const [prevOpen, setPrevOpen] = useState(open);
    const [prevEditing, setPrevEditing] = useState<Student | null>(editing);

    if (open && (!prevOpen || prevEditing !== editing)) {
        setPrevOpen(open);
        setPrevEditing(editing);
        setForm(
            editing
                ? {
                      name: editing.name,
                      admissionNo: editing.admissionNo,
                      className: editing.className,
                      section: editing.section,
                      gender: editing.gender,
                      guardian: editing.guardian,
                      phone: editing.phone,
                      email: editing.email,
                  }
                : { ...EMPTY_FORM, admissionNo: defaultAdmissionNo },
        );
    } else if (!open && prevOpen) {
        setPrevOpen(false);
    }

    function handleSubmit(e: FormEvent<HTMLFormElement>) {
        e.preventDefault();
        onSubmit(form);
    }

    return (
        <Modal
            open={open}
            title={editing ? `Edit — ${editing.name}` : "Add new student"}
            onClose={onClose}
        >
            <form onSubmit={handleSubmit}>
                <div className="form-grid">
                    <Input
                        label="Full name"
                        id="f-name"
                        value={form.name}
                        required
                        onChange={(e) => setForm({ ...form, name: e.target.value })}
                    />
                    <Input
                        label="Admission no"
                        id="f-adm"
                        value={form.admissionNo}
                        disabled
                        hint="Auto-generated"
                    />
                    <Select
                        label="Class"
                        id="f-class"
                        value={form.className}
                        onChange={(e) => setForm({ ...form, className: e.target.value })}
                    >
                        {["6", "7", "8", "9", "10", "11", "12"].map((c) => (
                            <option key={c} value={c}>
                                {c}
                            </option>
                        ))}
                    </Select>
                    <Select
                        label="Section"
                        id="f-sec"
                        value={form.section}
                        onChange={(e) => setForm({ ...form, section: e.target.value })}
                    >
                        {["A", "B", "C", "D"].map((sec) => (
                            <option key={sec} value={sec}>
                                {sec}
                            </option>
                        ))}
                    </Select>
                    <Select
                        label="Gender"
                        id="f-gen"
                        value={form.gender}
                        onChange={(e) =>
                            setForm({ ...form, gender: e.target.value as Student["gender"] })
                        }
                    >
                        <option>Male</option>
                        <option>Female</option>
                    </Select>
                    <Input
                        label="Guardian"
                        id="f-guard"
                        value={form.guardian}
                        required
                        onChange={(e) => setForm({ ...form, guardian: e.target.value })}
                    />
                    <Input
                        label="Phone"
                        id="f-phone"
                        value={form.phone}
                        required
                        onChange={(e) => setForm({ ...form, phone: e.target.value })}
                    />
                    <Input
                        label="Email"
                        id="f-email"
                        type="email"
                        value={form.email}
                        onChange={(e) => setForm({ ...form, email: e.target.value })}
                    />
                </div>
                <div className="modal-actions">
                    <Button type="button" variant="ghost" onClick={onClose}>
                        Cancel
                    </Button>
                    <Button type="submit">{editing ? "Save changes" : "Add student"}</Button>
                </div>
            </form>
        </Modal>
    );
}
