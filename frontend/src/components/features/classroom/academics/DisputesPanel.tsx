"use client";

import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Badge, Button, Card, Select, Spinner, Table, Textarea } from "@/components/ui";
import { useToast } from "@/components/ui/toast";
import { errorMessage } from "@/lib/api/client";
import {
    getExams,
    getSchoolDisputes,
    getStudents,
    getSubjects,
    raiseDispute,
    setDisputeStatus,
} from "@/services";
import { useApiQuery } from "@/lib/api/use-api-query";
import type { DisputeRow } from "@/types";

// Mark disputes, school-wide: a family challenges a score, the office answers it.
// A dispute names the exam and subject rather than a `marks` row, so a challenge
// can be raised even before the mark is entered.

const STATUSES = ["Open", "Under Review", "Resolved"] as const;

export default function DisputesPanel() {
    const toast = useToast();
    const queryClient = useQueryClient();
    const disputesQuery = useApiQuery(["classroom", "disputes"], getSchoolDisputes);
    const studentsQuery = useApiQuery(["students"], () => getStudents());
    const examsQuery = useApiQuery(["classroom", "exams"], getExams);
    const subjectsQuery = useApiQuery(["academics", "subjects"], getSubjects);

    const [studentId, setStudentId] = useState("");
    const [examId, setExamId] = useState("");
    const [subjectId, setSubjectId] = useState("");
    const [reason, setReason] = useState("");
    const [busy, setBusy] = useState(false);

    const rows: DisputeRow[] = disputesQuery.data ?? [];
    const students = studentsQuery.data ?? [];
    const exams = examsQuery.data ?? [];
    const subjects = subjectsQuery.data ?? [];

    async function submit() {
        if (!studentId || !examId || !subjectId || !reason.trim()) {
            toast.push("error", "Student, exam, subject and reason are all required");
            return;
        }
        setBusy(true);
        try {
            await raiseDispute({ studentId, examId, subjectId, reason });
            await queryClient.invalidateQueries({ queryKey: ["classroom", "disputes"] });
            toast.push("success", "Dispute logged — it now shows as Open");
            setReason("");
        } catch (error) {
            toast.push("error", errorMessage(error, "Could not log the dispute"));
        } finally {
            setBusy(false);
        }
    }

    async function move(row: DisputeRow, status: string) {
        try {
            await setDisputeStatus(row.id, status);
            await queryClient.invalidateQueries({ queryKey: ["classroom", "disputes"] });
            toast.push("info", `${row.student}'s dispute marked ${status}`);
        } catch (error) {
            toast.push("error", errorMessage(error, "Could not change the dispute"));
        }
    }

    if (disputesQuery.isPending) return <Spinner />;

    return (
        <div className="space-y-6">
            <Card title="Raise a dispute">
                <div className="form-grid">
                    <Select
                        label="Student"
                        value={studentId}
                        onChange={(e) => setStudentId(e.target.value)}
                    >
                        <option value="">Select a student…</option>
                        {students.map((student) => (
                            <option key={student.id} value={student.id}>
                                {student.name} ({student.admissionNo})
                            </option>
                        ))}
                    </Select>
                    <Select label="Exam" value={examId} onChange={(e) => setExamId(e.target.value)}>
                        <option value="">Select an exam…</option>
                        {exams.map((exam) => (
                            <option key={exam.id} value={exam.id}>
                                {exam.name}
                            </option>
                        ))}
                    </Select>
                    <Select
                        label="Subject"
                        value={subjectId}
                        onChange={(e) => setSubjectId(e.target.value)}
                    >
                        <option value="">Select a subject…</option>
                        {subjects.map((subject) => (
                            <option key={subject.id} value={subject.id}>
                                {subject.name}
                            </option>
                        ))}
                    </Select>
                    <div style={{ gridColumn: "1 / -1" }}>
                        <Textarea
                            label="Reason"
                            rows={2}
                            value={reason}
                            onChange={(e) => setReason(e.target.value)}
                            placeholder="What is being questioned?"
                        />
                    </div>
                </div>
                <div className="modal-actions">
                    <Button variant="primary" onClick={submit} disabled={busy}>
                        {busy ? "Logging…" : "Log dispute"}
                    </Button>
                </div>
            </Card>

            <Table
                columns={[
                    {
                        key: "student",
                        header: "Student",
                        render: (r: DisputeRow) => <b>{r.student}</b>,
                    },
                    { key: "exam", header: "Exam" },
                    { key: "subject", header: "Subject" },
                    { key: "reason", header: "Reason" },
                    {
                        key: "status",
                        header: "Status",
                        render: (r: DisputeRow) => (
                            <Badge
                                tone={
                                    r.status === "Resolved"
                                        ? "green"
                                        : r.status === "Open"
                                          ? "red"
                                          : "amber"
                                }
                            >
                                {r.status}
                            </Badge>
                        ),
                    },
                    {
                        key: "action",
                        header: "Move to",
                        render: (r: DisputeRow) => (
                            <Select
                                value={r.status}
                                onChange={(e) => void move(r, e.target.value)}
                                aria-label={`Status for ${r.student}`}
                            >
                                {STATUSES.map((status) => (
                                    <option key={status} value={status}>
                                        {status}
                                    </option>
                                ))}
                            </Select>
                        ),
                    },
                ]}
                rows={rows}
                rowKey={(r) => r.id}
                empty="No mark disputes."
            />
        </div>
    );
}
