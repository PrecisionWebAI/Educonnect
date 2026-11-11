"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Badge, Select, Spinner, Tabs } from "@/components/ui";
import { getSectionDetail, getTeacherOptions, setClassTeacher } from "@/services";
import { useApiQuery } from "@/lib/api/use-api-query";
import { usePermission } from "@/hooks/use-authorization";
import { useAuth } from "@/providers/auth-context";
import { ACADEMIC_STAFF_ROLES, hasAnyRole } from "@/lib/auth/rbac";
import AcademicsPanel from "./academics/AcademicsPanel";
import AttendancePanel from "./attendance/AttendancePanel";
import ExamsPanel from "./exams/ExamsPanel";
import HomeworkPanel from "./homework/HomeworkPanel";
import StudentsPanel from "./students/StudentsPanel";
import TimetablePanel from "./timetable/TimetablePanel";

// One class-section - the card's own page, and the home of the four things that
// belong to a class-section:
//
//   Students   - the student directory, opened on *this* section by default
//   Attendance - this section's register, saved for real
//   Academics  - this section's marks (entry + gradebook), saved for real
//   Homework   - this section's assignments, submissions and class diary
//
// The class-teacher picker is only offered to those who may assign.

const STAGE_LABELS: Record<string, string> = {
    pre_primary: "Pre-primary",
    primary: "Primary",
    middle: "Middle",
    secondary: "Secondary",
    senior_secondary: "Senior secondary",
};

/** The tabs a class-section page shows, in order - Students is the default. */
type SectionTab =
    | "Students"
    | "Attendance"
    | "Academics"
    | "Homework"
    | "Timetable"
    | "Exams & AI Papers";
const ALL_TABS: SectionTab[] = [
    "Students",
    "Attendance",
    "Academics",
    "Homework",
    "Timetable",
    "Exams & AI Papers",
];

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

/** One glass stat in the header strip. */
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

export default function SectionDetailPage() {
    const params = useParams<{ sectionId: string }>();
    const sectionId = params?.sectionId ?? "";
    const query = useApiQuery(
        ["classroom", "section", sectionId],
        () => getSectionDetail(sectionId),
        { enabled: Boolean(sectionId) },
    );
    // The teacher list is only needed to *assign* a class teacher - a teacher who
    // may open their own section cannot assign one, so the request is skipped.
    const canAssign = usePermission("classes.assign_teacher");
    const teachersQuery = useApiQuery(["classroom", "teachers"], getTeacherOptions, {
        enabled: canAssign,
    });
    const queryClient = useQueryClient();
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [tab, setTab] = useState<SectionTab>("Students");
    const detail = query.data;
    const teachers = useMemo(() => teachersQuery.data ?? [], [teachersQuery.data]);

    // The AI paper builder is for academic staff; everyone else who may open the
    // section still gets Students, Attendance, Academics, Homework and Timetable.
    const { user } = useAuth();
    const canSeePapers = hasAnyRole(user?.roles, ACADEMIC_STAFF_ROLES);
    const tabs = useMemo(
        () => (canSeePapers ? ALL_TABS : ALL_TABS.filter((t) => t !== "Exams & AI Papers")),
        [canSeePapers],
    );
    const activeTab = tabs.includes(tab) ? tab : tabs[0];

    // Who can be credited with an assignment: the section's own teachers (class
    // teacher + subject teachers) first - a teacher who may open their section
    // cannot read the school-wide staff list, and does not need to. The full list
    // is merged in for those who can read it.
    const teacherOptions = useMemo(() => {
        const byId = new Map<string, { employeeId: string; name: string }>();
        const classTeacher = detail?.classTeacher;
        if (classTeacher?.employeeId) {
            byId.set(classTeacher.employeeId, {
                employeeId: classTeacher.employeeId,
                name: classTeacher.name ?? classTeacher.employeeId,
            });
        }
        for (const subject of detail?.subjects ?? []) {
            if (subject.teacherId && subject.teacherName) {
                byId.set(subject.teacherId, {
                    employeeId: subject.teacherId,
                    name: subject.teacherName,
                });
            }
        }
        for (const teacher of teachers) {
            byId.set(teacher.employeeId, {
                employeeId: teacher.employeeId,
                name: teacher.name,
            });
        }
        return [...byId.values()].sort((a, b) => a.name.localeCompare(b.name));
    }, [detail, teachers]);

    /** The section's own subjects — the Timetable, Homework and Exams tabs use them. */
    const sectionSubjects = useMemo(
        () =>
            (detail?.subjects ?? []).map((subject) => ({
                id: subject.subjectId,
                name: subject.name,
            })),
        [detail?.subjects],
    );

    /** Run the assignment, then re-read the section and the grid behind it. */
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
                        <Stat
                            label="Course complete"
                            value={pct(detail.syllabusPercent)}
                        />
                        <Stat
                            label="Fees received"
                            value={`${inr(detail.feesCollected)} / ${inr(detail.feesExpected)}`}
                        />
                        <Stat label="Fees %" value={pct(detail.feesPercent)} />
                    </div>

                    {canAssign && (
                        <div className="glass-tile flex flex-wrap items-center gap-3 rounded-2xl p-3">
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
                                    <option
                                        key={teacher.employeeId}
                                        value={teacher.employeeId}
                                    >
                                        {teacher.name}
                                    </option>
                                ))}
                            </Select>
                            {saving && <Spinner size="sm" />}
                            {error && (
                                <span className="text-sm text-red-500">{error}</span>
                            )}
                        </div>
                    )}

                    <Tabs
                        tabs={[...tabs]}
                        active={activeTab}
                        onChange={(next) => setTab(next as SectionTab)}
                    />

                    <div className="mt-4">
                        {activeTab === "Students" ? (
                            <StudentsPanel
                                className={detail.className}
                                section={detail.sectionName}
                            />
                        ) : activeTab === "Attendance" ? (
                            <AttendancePanel
                                sectionId={detail.sectionId}
                                className={detail.className}
                                section={detail.sectionName}
                            />
                        ) : activeTab === "Academics" ? (
                            <AcademicsPanel sectionId={detail.sectionId} />
                        ) : activeTab === "Timetable" ? (
                            <TimetablePanel
                                sectionId={detail.sectionId}
                                classroomId={detail.classroomId}
                                classLabel={detail.classLabel}
                                subjects={sectionSubjects}
                                teachers={teacherOptions}
                            />
                        ) : activeTab === "Exams & AI Papers" ? (
                            <ExamsPanel
                                classroomId={detail.classroomId}
                                sectionId={detail.sectionId}
                                classLabel={detail.classLabel}
                                className={detail.className}
                                subjects={sectionSubjects}
                            />
                        ) : (
                            <HomeworkPanel
                                sectionId={detail.sectionId}
                                className={detail.className}
                                section={detail.sectionName}
                                subjects={sectionSubjects}
                                teachers={teacherOptions}
                                defaultTeacherId={detail.classTeacher?.employeeId ?? null}
                            />
                        )}
                    </div>
                </>
            )}
        </div>
    );
}
