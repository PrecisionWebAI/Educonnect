"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Badge, Select, Spinner, Table, Tabs } from "@/components/ui";
import type { Column } from "@/components/ui";
import {
    getSectionDetail,
    getTeacherOptions,
    setClassTeacher,
    setSubjectTeacher,
} from "@/services";
import { useApiQuery } from "@/lib/api/use-api-query";
import type {
    AttendanceDayRow,
    DiaryRowItem,
    ExamRowItem,
    HomeworkRowItem,
    SectionStudentRow,
    SubjectMarkRowItem,
    TimetableSlotRow,
} from "@/types";

// Phase 2 — one class-section in full, in the same glass language as the grid.
// Every panel reads a real table; a tab with no rows says so instead of showing
// an empty shell.

type SectionTab =
    | "Students"
    | "Attendance"
    | "Timetable"
    | "Homework"
    | "Diary"
    | "Academics & Marks"
    | "Subjects & Teachers";

const TABS: SectionTab[] = [
    "Students",
    "Attendance",
    "Timetable",
    "Homework",
    "Diary",
    "Academics & Marks",
    "Subjects & Teachers",
];

const STAGE_LABELS: Record<string, string> = {
    pre_primary: "Pre-primary",
    primary: "Primary",
    middle: "Middle",
    secondary: "Secondary",
    senior_secondary: "Senior secondary",
};

/** `90.5` -> `90.5%`, `null` -> `—`. */
function pct(value: number | null): string {
    return value === null ? "—" : `${value}%`;
}

/** Compact rupees: 425000 -> `₹4.3L`. */
function inr(value: number | null): string {
    if (value === null) return "—";
    if (value >= 100000) return `₹${(value / 100000).toFixed(1)}L`;
    if (value >= 1000) return `₹${Math.round(value / 1000)}K`;
    return `₹${Math.round(value)}`;
}

/** One glass stat in the always-visible header strip. */
function Stat({ label, value }: { label: string; value: string }) {
    return (
        <div className="glass-tile rounded-xl px-3 py-2">
            <div className="text-muted-foreground text-[0.68rem] font-medium tracking-wide uppercase">
                {label}
            </div>
            <div className="truncate text-sm font-semibold">{value}</div>
        </div>
    );
}

/** A glass panel holding one table. */
function Panel<T>({
    columns,
    rows,
    rowKey,
    empty,
}: {
    columns: Column<T>[];
    rows: T[];
    rowKey: (row: T) => string | number;
    empty: string;
}) {
    return (
        <div className="glass-tile overflow-hidden rounded-2xl p-2">
            <Table columns={columns} rows={rows} rowKey={rowKey} empty={empty} />
        </div>
    );
}

const STUDENT_COLUMNS: Column<SectionStudentRow>[] = [
    { key: "name", header: "Student" },
    { key: "admissionNumber", header: "Admission no." },
    { key: "guardian", header: "Guardian", render: (r) => r.guardian ?? "—" },
    { key: "gender", header: "Gender", render: (r) => r.gender ?? "—" },
    {
        key: "attendancePercent",
        header: "Attendance",
        render: (r) => pct(r.attendancePercent),
    },
    {
        key: "feesPaid",
        header: "Fees paid",
        align: "right",
        render: (r) => inr(r.feesPaid),
    },
    { key: "feesDue", header: "Fees due", align: "right", render: (r) => inr(r.feesDue) },
];

const ATTENDANCE_COLUMNS: Column<AttendanceDayRow>[] = [
    { key: "date", header: "Date" },
    { key: "present", header: "Present", align: "right" },
    { key: "absent", header: "Absent", align: "right" },
    { key: "late", header: "Late", align: "right" },
    { key: "leave", header: "Leave", align: "right" },
    { key: "total", header: "Marked", align: "right" },
    { key: "percent", header: "%", align: "right", render: (r) => `${r.percent}%` },
];

const TIMETABLE_COLUMNS: Column<TimetableSlotRow>[] = [
    { key: "day", header: "Day" },
    { key: "startTime", header: "From" },
    { key: "endTime", header: "To" },
    { key: "subject", header: "Subject" },
    { key: "teacher", header: "Teacher", render: (r) => r.teacher ?? "—" },
    { key: "room", header: "Room", render: (r) => r.room ?? "—" },
];

const HOMEWORK_COLUMNS: Column<HomeworkRowItem>[] = [
    { key: "title", header: "Title" },
    { key: "subject", header: "Subject" },
    { key: "teacher", header: "Given by", render: (r) => r.teacher ?? "—" },
    { key: "dueDate", header: "Due" },
    {
        key: "submitted",
        header: "Submitted",
        align: "right",
        render: (r) => `${r.submitted}/${r.total}`,
    },
];

const DIARY_COLUMNS: Column<DiaryRowItem>[] = [
    { key: "date", header: "Date" },
    { key: "teacher", header: "By", render: (r) => r.teacher ?? "—" },
    { key: "note", header: "Note" },
];

const EXAM_COLUMNS: Column<ExamRowItem>[] = [
    { key: "name", header: "Exam" },
    { key: "term", header: "Term", render: (r) => r.term ?? "—" },
    { key: "status", header: "Status" },
    { key: "marksEntered", header: "Marks entered", align: "right" },
    {
        key: "averagePercent",
        header: "Average",
        align: "right",
        render: (r) => pct(r.averagePercent),
    },
];

const MARK_COLUMNS: Column<SubjectMarkRowItem>[] = [
    { key: "subject", header: "Subject" },
    {
        key: "averagePercent",
        header: "Average",
        align: "right",
        render: (r) => pct(r.averagePercent),
    },
    { key: "highest", header: "Highest", align: "right", render: (r) => pct(r.highest) },
    { key: "lowest", header: "Lowest", align: "right", render: (r) => pct(r.lowest) },
    { key: "entries", header: "Marks", align: "right" },
];

export default function SectionDetailPage() {
    const params = useParams<{ sectionId: string }>();
    const sectionId = params?.sectionId ?? "";
    const [tab, setTab] = useState<SectionTab>("Students");
    const query = useApiQuery(
        ["classroom", "section", sectionId],
        () => getSectionDetail(sectionId),
        { enabled: Boolean(sectionId) },
    );
    const teachersQuery = useApiQuery(["classroom", "teachers"], getTeacherOptions);
    const queryClient = useQueryClient();
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const detail = query.data;
    const teachers = teachersQuery.data ?? [];

    /** Run one assignment, then re-read the section and the grid behind it. */
    async function assign(action: () => Promise<void>) {
        setSaving(true);
        setError(null);
        try {
            await action();
            await queryClient.invalidateQueries({ queryKey: ["classroom"] });
        } catch (cause) {
            setError(
                cause instanceof Error ? cause.message : "Could not save the change.",
            );
        } finally {
            setSaving(false);
        }
    }

    return (
        <div className="glass-backdrop min-h-[70vh] rounded-3xl p-4 sm:p-6">
            <Link
                href="/dashboard/classroom"
                className="text-muted-foreground mb-4 inline-block text-sm hover:underline"
            >
                ← All classrooms
            </Link>

            {query.isPending ? (
                <Spinner />
            ) : !detail ? (
                <div className="glass-tile rounded-2xl p-8 text-center">
                    <p className="text-muted-foreground text-sm">
                        This class-section could not be loaded.
                    </p>
                </div>
            ) : (
                <>
                    <header className="mb-5 flex flex-wrap items-center gap-3">
                        <h1 className="text-2xl font-semibold">{detail.classLabel}</h1>
                        <Badge tone="violet">
                            {STAGE_LABELS[detail.stage] ?? detail.stage}
                        </Badge>
                        <span className="text-muted-foreground text-sm">
                            {detail.classTeacher?.name
                                ? `Class teacher: ${detail.classTeacher.name}`
                                : "No class teacher assigned"}
                            {detail.classTeacher?.email
                                ? ` · ${detail.classTeacher.email}`
                                : ""}
                            {detail.classTeacher?.phone
                                ? ` · ${detail.classTeacher.phone}`
                                : ""}
                        </span>
                    </header>

                    <div className="mb-5 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
                        <Stat label="Students" value={String(detail.strength)} />
                        <Stat
                            label="Boys / Girls"
                            value={`${detail.boys} / ${detail.girls}`}
                        />
                        <Stat label="Attendance" value={pct(detail.attendancePercent)} />
                        <Stat label="Course complete" value={pct(detail.syllabusPercent)} />
                        <Stat
                            label="Fees received"
                            value={`${inr(detail.feesCollected)} / ${inr(detail.feesExpected)}`}
                        />
                        <Stat label="Fees %" value={pct(detail.feesPercent)} />
                    </div>

                    <div className="glass-tile mt-4 flex flex-wrap items-center gap-3 rounded-2xl p-3">
                        <div className="text-sm font-semibold">Class teacher</div>
                        <Select
                            value={detail.classTeacher?.employeeId ?? ""}
                            disabled={saving}
                            onChange={(e) =>
                                void assign(() =>
                                    setClassTeacher(sectionId, e.target.value || null),
                                )
                            }
                            aria-label="Class teacher"
                        >
                            <option value="">— nobody yet —</option>
                            {teachers.map((teacher) => (
                                <option key={teacher.employeeId} value={teacher.employeeId}>
                                    {teacher.name}
                                </option>
                            ))}
                        </Select>
                        {saving && <Spinner size="sm" />}
                        {error && <span className="text-sm text-red-500">{error}</span>}
                    </div>

                    <Tabs tabs={TABS} active={tab} onChange={(t) => setTab(t as SectionTab)} />

                    <div className="mt-4">
                        {tab === "Students" && (
                            <Panel
                                columns={STUDENT_COLUMNS}
                                rows={detail.students}
                                rowKey={(r) => r.studentId}
                                empty="No students in this section yet."
                            />
                        )}
                        {tab === "Attendance" && (
                            <Panel
                                columns={ATTENDANCE_COLUMNS}
                                rows={detail.attendance}
                                rowKey={(r) => r.date}
                                empty="No attendance has been marked for this section yet."
                            />
                        )}
                        {tab === "Timetable" && (
                            <Panel
                                columns={TIMETABLE_COLUMNS}
                                rows={detail.timetable}
                                rowKey={(r) => `${r.day}-${r.startTime}-${r.subject}`}
                                empty="No timetable periods for this section yet."
                            />
                        )}
                        {tab === "Homework" && (
                            <Panel
                                columns={HOMEWORK_COLUMNS}
                                rows={detail.homework}
                                rowKey={(r) => r.id}
                                empty="No homework has been given to this section yet."
                            />
                        )}
                        {tab === "Diary" && (
                            <Panel
                                columns={DIARY_COLUMNS}
                                rows={detail.diary}
                                rowKey={(r) => r.id}
                                empty="No diary entries for this section yet."
                            />
                        )}
                        {tab === "Academics & Marks" && (
                            <div className="space-y-4">
                                <Panel
                                    columns={EXAM_COLUMNS}
                                    rows={detail.exams}
                                    rowKey={(r) => r.id}
                                    empty="No marks entered for this section yet."
                                />
                                {detail.marks.length > 0 && (
                                    <Panel
                                        columns={MARK_COLUMNS}
                                        rows={detail.marks}
                                        rowKey={(r) => r.subject}
                                        empty=""
                                    />
                                )}
                            </div>
                        )}
                        {tab === "Subjects & Teachers" && (
                            <div className="glass-tile overflow-hidden rounded-2xl">
                                {detail.subjects.length === 0 ? (
                                    <p className="text-muted-foreground p-4 text-sm">
                                        This school has no subjects yet.
                                    </p>
                                ) : (
                                    <ul className="divide-y divide-white/10">
                                        {detail.subjects.map((subject) => (
                                            <li
                                                key={subject.subjectId}
                                                className="flex flex-wrap items-center gap-3 p-3"
                                            >
                                                <div className="min-w-[9rem] flex-1">
                                                    <div className="text-sm font-semibold">
                                                        {subject.name}
                                                    </div>
                                                    <div className="text-muted-foreground text-xs">
                                                        {subject.code}
                                                    </div>
                                                </div>
                                                <Select
                                                    value={subject.teacherId ?? ""}
                                                    disabled={saving}
                                                    onChange={(e) =>
                                                        void assign(() =>
                                                            setSubjectTeacher(
                                                                sectionId,
                                                                subject.subjectId,
                                                                e.target.value || null,
                                                            ),
                                                        )
                                                    }
                                                    aria-label={`Teacher for ${subject.name}`}
                                                >
                                                    <option value="">— nobody yet —</option>
                                                    {teachers.map((teacher) => (
                                                        <option
                                                            key={teacher.employeeId}
                                                            value={teacher.employeeId}
                                                        >
                                                            {teacher.name}
                                                        </option>
                                                    ))}
                                                </Select>
                                            </li>
                                        ))}
                                    </ul>
                                )}
                            </div>
                        )}
                    </div>
                </>
            )}
        </div>
    );
}

