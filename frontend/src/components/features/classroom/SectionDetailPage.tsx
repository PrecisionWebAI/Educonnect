"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
    ArrowLeft,
    BookOpen,
    GraduationCap,
    TrendingUp,
    UserRound,
    UsersRound,
    Wallet,
} from "lucide-react";
import type { ReactNode } from "react";
import { Select, Spinner, Tabs } from "@/components/ui";
import { getSectionDetail, getTeacherOptions, setClassTeacher } from "@/services";
import { useApiQuery } from "@/lib/api/use-api-query";
import { inrCompact as inr, pct } from "@/lib/format";
import { usePermission } from "@/hooks/use-authorization";
import { useAuth } from "@/providers/auth-context";
import { ACADEMIC_STAFF_ROLES, hasAnyRole } from "@/lib/auth/rbac";
import ExamsPlanPanel from "./exam-plan/ExamsPlanPanel";
import AttendancePanel from "./attendance/AttendancePanel";
import CoursePanel from "./course/CoursePanel";
import ExamsPanel from "./exams/ExamsPanel";
import HomeworkPanel from "./homework/HomeworkPanel";
import StudentsPanel from "./students/StudentsPanel";
import TimetablePanel from "./timetable/TimetablePanel";

// One class-section - the card's own page, and the home of the things that belong
// to a class-section:
//
//   Students   - the student directory, opened on *this* section by default
//   Attendance - this section's register, saved for real
//   Course     - the syllabus plan, who teaches it and how far it has got
//   Exams      - the date sheet, the marks sheet, publication and results
//   Homework   - this section's assignments, submissions and class diary
//   Timetable  - this section's week
//   AI Papers  - the question-paper builder (academic staff only)
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
    "Students" | "Attendance" | "Course" | "Exams" | "Homework" | "Timetable" | "AI Papers";
const ALL_TABS: SectionTab[] = [
    "Students",
    "Attendance",
    "Course",
    "Exams",
    "Homework",
    "Timetable",
    "AI Papers",
];

const TAB_DESCRIPTIONS: Record<SectionTab, string> = {
    Students: "Browse the roster, manage student records, and open individual profiles.",
    Attendance: "Record the register for a date and review attendance history.",
    Course: "Follow subject plans, teacher assignments, and chapter completion.",
    Exams: "Plan the date sheet, enter marks, publish them and read the results.",
    Homework: "Assign work, review submissions, and keep the class diary.",
    Timetable: "View and manage this section's weekly schedule.",
    "AI Papers": "Generate a question paper for this section with AI.",
};

function Stat({
    label,
    value,
    detail,
    progress,
    icon,
}: {
    label: string;
    value: string;
    detail: string;
    progress: number | null;
    icon: ReactNode;
}) {
    const percentage = progress === null ? null : Math.max(0, Math.min(100, progress));

    return (
        <article className="glass-tile classroom-stat classroom-detail-stat rounded-2xl p-4">
            <div className="flex items-start gap-3">
                <span className="bg-primary/10 text-primary grid size-10 shrink-0 place-items-center rounded-xl">
                    {icon}
                </span>
                <div className="min-w-0">
                    <p className="text-muted-foreground truncate text-xs font-medium">{label}</p>
                    <p className="truncate text-xl leading-tight font-semibold tracking-tight">
                        {value}
                    </p>
                    <p className="text-muted-foreground mt-1 truncate text-[0.68rem]">{detail}</p>
                </div>
            </div>
            {percentage === null ? (
                <div
                    className="classroom-detail-progress classroom-detail-progress-empty"
                    aria-hidden="true"
                />
            ) : (
                <div
                    className="classroom-detail-progress"
                    role="progressbar"
                    aria-label={label}
                    aria-valuemin={0}
                    aria-valuemax={100}
                    aria-valuenow={percentage}
                    aria-valuetext={pct(progress)}
                >
                    <span style={{ width: `${percentage}%` }} />
                </div>
            )}
        </article>
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
    // section still gets Students, Attendance, Course, Exams, Homework and Timetable.
    const { user } = useAuth();
    const canSeePapers = hasAnyRole(user?.roles, ACADEMIC_STAFF_ROLES);
    const tabs = useMemo(
        () => (canSeePapers ? ALL_TABS : ALL_TABS.filter((t) => t !== "AI Papers")),
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
            setError(cause instanceof Error ? cause.message : "Could not save the change.");
        } finally {
            setSaving(false);
        }
    }

    return (
        <div className="classroom-page classroom-detail-page min-h-[70vh] space-y-5 sm:space-y-6">
            <Link href="/dashboard/classroom" className="classroom-back-link">
                <ArrowLeft aria-hidden="true" className="size-4" />
                All classrooms
            </Link>

            {query.isPending ? (
                <div
                    className="glass-tile flex min-h-52 items-center justify-center rounded-3xl"
                    role="status"
                >
                    <Spinner />
                    <span className="sr-only">Loading class section</span>
                </div>
            ) : !detail ? (
                <div role="alert" className="glass-tile rounded-3xl p-6 sm:p-8">
                    <h1 className="text-lg font-semibold">Class section could not be loaded</h1>
                    <p className="text-muted-foreground mt-1 text-sm">
                        {query.error instanceof Error
                            ? query.error.message
                            : "Please return to all classrooms and try again."}
                    </p>
                </div>
            ) : (
                <>
                    <header className="classroom-hero relative overflow-hidden rounded-3xl p-5 sm:p-7">
                        <div className="relative flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between">
                            <div className="max-w-3xl min-w-0">
                                <div className="classroom-hero-kicker mb-3">
                                    <GraduationCap aria-hidden="true" className="size-3.5" />
                                    {STAGE_LABELS[detail.stage] ?? detail.stage}
                                </div>
                                <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
                                    {detail.classLabel}
                                </h1>
                                <p className="mt-2 text-sm leading-relaxed sm:text-base">
                                    {detail.classTeacher?.name
                                        ? `Class teacher · ${detail.classTeacher.name}`
                                        : "No class teacher assigned"}
                                    {detail.classTeacher?.email
                                        ? ` · ${detail.classTeacher.email}`
                                        : ""}
                                    {detail.classTeacher?.phone
                                        ? ` · ${detail.classTeacher.phone}`
                                        : ""}
                                </p>
                            </div>
                            <div className="classroom-hero-highlight">
                                <span className="classroom-hero-highlight-icon">
                                    <UsersRound aria-hidden="true" className="size-5" />
                                </span>
                                <div>
                                    <p className="text-xs font-medium">Students in this section</p>
                                    <div className="flex items-baseline gap-1.5">
                                        <span className="text-2xl leading-tight font-semibold">
                                            {detail.strength.toLocaleString()}
                                        </span>
                                        <span className="text-xs">students</span>
                                    </div>
                                    <p className="text-xs">
                                        {detail.boys} boys · {detail.girls} girls
                                    </p>
                                </div>
                            </div>
                        </div>
                    </header>

                    <section
                        aria-label="Section overview metrics"
                        className="grid gap-3 sm:grid-cols-2 2xl:grid-cols-3"
                    >
                        <Stat
                            label="Attendance"
                            value={pct(detail.attendancePercent)}
                            detail={
                                detail.attendance.length > 0
                                    ? `${detail.attendance.length} register entries`
                                    : "No attendance recorded yet"
                            }
                            progress={detail.attendancePercent}
                            icon={<TrendingUp aria-hidden="true" className="size-5" />}
                        />
                        <Stat
                            label="Course completion"
                            value={pct(detail.syllabusPercent)}
                            detail={
                                detail.subjects.length > 0
                                    ? `${detail.subjects.length} subjects in this section`
                                    : "No subjects configured yet"
                            }
                            progress={detail.syllabusPercent}
                            icon={<BookOpen aria-hidden="true" className="size-5" />}
                        />
                        <Stat
                            label="Fees received"
                            value={pct(detail.feesPercent)}
                            detail={`Collected ${inr(detail.feesCollected)} of ${inr(detail.feesExpected)}`}
                            progress={detail.feesPercent}
                            icon={<Wallet aria-hidden="true" className="size-5" />}
                        />
                    </section>

                    {canAssign && (
                        <section
                            aria-labelledby="class-teacher-title"
                            className="glass-tile classroom-assignment-card rounded-2xl p-4 sm:p-5"
                        >
                            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                                <div className="flex min-w-0 items-center gap-3">
                                    <span className="bg-primary/10 text-primary grid size-10 shrink-0 place-items-center rounded-xl">
                                        <UserRound aria-hidden="true" className="size-5" />
                                    </span>
                                    <div className="min-w-0">
                                        <h2 id="class-teacher-title" className="font-semibold">
                                            Class teacher
                                        </h2>
                                        <p className="text-muted-foreground truncate text-sm">
                                            {detail.classTeacher?.name ?? "No teacher assigned"}
                                        </p>
                                    </div>
                                </div>
                                <div className="w-full sm:max-w-sm">
                                    <Select
                                        value={detail.classTeacher?.employeeId ?? ""}
                                        disabled={
                                            saving ||
                                            teachersQuery.isPending ||
                                            teachersQuery.isError
                                        }
                                        onChange={(event) =>
                                            void assign(() =>
                                                setClassTeacher(
                                                    sectionId,
                                                    event.target.value || null,
                                                ),
                                            )
                                        }
                                        aria-label="Assign class teacher"
                                    >
                                        <option value="">Unassigned</option>
                                        {teachers.map((teacher) => (
                                            <option
                                                key={teacher.employeeId}
                                                value={teacher.employeeId}
                                            >
                                                {teacher.name}
                                            </option>
                                        ))}
                                    </Select>
                                </div>
                            </div>
                            {(saving ||
                                teachersQuery.isPending ||
                                teachersQuery.isError ||
                                error) && (
                                <div className="border-border/70 mt-3 border-t pt-3">
                                    {saving && (
                                        <p
                                            className="text-muted-foreground flex items-center gap-2 text-xs"
                                            role="status"
                                        >
                                            <Spinner size="sm" />
                                            Saving teacher assignment…
                                        </p>
                                    )}
                                    {teachersQuery.isError && (
                                        <p className="text-sm text-red-500" role="alert">
                                            Could not load the teacher list. Please try again later.
                                        </p>
                                    )}
                                    {error && (
                                        <p className="text-sm text-red-500" role="alert">
                                            {error}
                                        </p>
                                    )}
                                </div>
                            )}
                        </section>
                    )}

                    <section className="classroom-detail-workspace">
                        <header className="mb-4 flex flex-wrap items-end justify-between gap-3">
                            <div>
                                <p className="classroom-detail-eyebrow">Section workspace</p>
                                <h2 className="text-xl font-semibold tracking-tight">
                                    Manage this class
                                </h2>
                            </div>
                            <p className="text-muted-foreground text-xs">
                                {tabs.length} tools for {detail.className}-{detail.sectionName}
                            </p>
                        </header>
                        <div className="classroom-detail-tabs">
                            <Tabs
                                tabs={[...tabs]}
                                active={activeTab}
                                onChange={(next) => setTab(next as SectionTab)}
                                className="!mb-0"
                            />
                        </div>
                        <div className="classroom-detail-tab-intro" aria-live="polite">
                            <h3>{activeTab}</h3>
                            <p>{TAB_DESCRIPTIONS[activeTab]}</p>
                        </div>
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
                            ) : activeTab === "Course" ? (
                                <CoursePanel sectionId={detail.sectionId} />
                            ) : activeTab === "Exams" ? (
                                <ExamsPlanPanel
                                    sectionId={detail.sectionId}
                                    classroomId={detail.classroomId}
                                    classId={null}
                                    classLabel={detail.classLabel}
                                    className={detail.className}
                                    subjects={sectionSubjects}
                                />
                            ) : activeTab === "Timetable" ? (
                                <TimetablePanel
                                    sectionId={detail.sectionId}
                                    classroomId={detail.classroomId}
                                    classLabel={detail.classLabel}
                                    subjects={sectionSubjects}
                                    teachers={teacherOptions}
                                />
                            ) : activeTab === "AI Papers" ? (
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
                                    classroomId={detail.classroomId}
                                    className={detail.className}
                                    section={detail.sectionName}
                                    subjects={sectionSubjects}
                                    teachers={teacherOptions}
                                    defaultTeacherId={detail.classTeacher?.employeeId ?? null}
                                />
                            )}
                        </div>
                    </section>
                </>
            )}
        </div>
    );
}
