"use client";

import { useParams } from "next/navigation";
import { useMemo, useState } from "react";
import { BookOpen, GraduationCap, TrendingUp, UsersRound, Wallet } from "lucide-react";
import type { ChangeEvent, ReactNode } from "react";
import { Button, Modal, Select, Spinner, Tabs } from "@/components/ui";
import { getSectionDetail, getTeacherOptions, setClassTeacher } from "@/services";
import { useQueryClient } from "@tanstack/react-query";
import { useApiQuery } from "@/lib/api/use-api-query";
import { inrCompact as inr, pct, titleCase } from "@/lib/format";
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

//: The one line under a tab's title. Attendance has none on purpose: the register's
//: own date bar and roster already say what the tab is for.
const TAB_DESCRIPTIONS: Partial<Record<SectionTab, string>> = {
    Course: "Follow subject plans, teacher assignments, and chapter completion.",
    Exams: "Plan the date sheet, enter marks, publish them and read the results.",
    Homework: "Assign work, review submissions, and keep the class diary.",
    Timetable: "View and manage this section's weekly schedule.",
    "AI Papers": "Generate a question paper for this section with AI.",
};

/**
 * The one line under the section title: who teaches this section, and the number the
 * office rings them on.
 *
 * The email is not printed - a third value turned the line into a paragraph, and the
 * phone is what the office and a parent actually use. The name is set in Title Case
 * because the database stores canonical lower-case text, and the separator is spelled
 * out here once so a missing phone never leaves a dangling dot behind.
 */
function teacherLine(
    teacher: { name?: string | null; phone?: string | null } | null | undefined,
): string {
    const name = titleCase(teacher?.name);
    if (!name) return "No class teacher assigned";
    const phone = (teacher?.phone ?? "").trim();
    return phone ? `Class teacher: ${name} · ${phone}` : `Class teacher: ${name}`;
}

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

    const queryClient = useQueryClient();
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [pendingTeacher, setPendingTeacher] = useState<{
        teacherId: string | null;
        oldName: string;
        newName: string;
    } | null>(null);

    function askClassTeacherChange(event: ChangeEvent<HTMLSelectElement>) {
        const teacherId = event.target.value || null;
        const oldName = titleCase(detail?.classTeacher?.name) || "Unassigned";
        const newName = teacherId
            ? titleCase(teacherOptions.find((teacher) => teacher.employeeId === teacherId)?.name) ||
              "the selected teacher"
            : "Unassigned";
        setPendingTeacher({ teacherId, oldName, newName });
    }

    /** The section's own subjects — the Timetable, Homework and Exams tabs use them. */
    const sectionSubjects = useMemo(
        () =>
            (detail?.subjects ?? []).map((subject) => ({
                id: subject.classroomSubjectId,
                name: subject.name,
            })),
        [detail?.subjects],
    );

    /**
     * Change the section's class teacher, then re-read the section and every panel
     * behind it - the teacher's name is printed in the header, so it cannot lag.
     */
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
                            : "Please reload the page and try again."}
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
                                    {teacherLine(detail.classTeacher)}
                                </p>
                            </div>
                            <div className="classroom-hero-highlight">
                                <span className="classroom-hero-highlight-icon">
                                    <UsersRound aria-hidden="true" className="size-5" />
                                </span>
                                <div>
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
                                detail.attendancePercent === null
                                    ? "No attendance recorded yet"
                                    : `${detail.attendanceOpenDays} open day${
                                          detail.attendanceOpenDays === 1 ? "" : "s"
                                      } this month`
                            }
                            progress={detail.attendancePercent}
                            icon={<TrendingUp aria-hidden="true" className="size-5" />}
                        />
                        <Stat
                            label="Course completion"
                            value={pct(detail.syllabusPercent)}
                            detail={
                                detail.syllabusPercent === null
                                    ? "No chapters planned yet"
                                    : `${detail.subjectsTracked} subject${
                                          detail.subjectsTracked === 1 ? "" : "s"
                                      } with a chapter plan`
                            }
                            progress={detail.syllabusPercent}
                            icon={<BookOpen aria-hidden="true" className="size-5" />}
                        />
                        <Stat
                            label="Fees received"
                            value={pct(detail.feesPercent)}
                            detail={
                                detail.feesPercent === null
                                    ? "No data yet"
                                    : `Collected ${inr(detail.feesCollected)} of ${inr(
                                          detail.feesExpected,
                                      )}`
                            }
                            progress={detail.feesPercent}
                            icon={<Wallet aria-hidden="true" className="size-5" />}
                        />
                    </section>

                    <section className="classroom-detail-workspace">
                        <div className="classroom-detail-toolbar">
                            <div className="classroom-detail-tabs">
                                <Tabs
                                    tabs={[...tabs]}
                                    active={activeTab}
                                    onChange={(next) => setTab(next as SectionTab)}
                                    className="!mb-0"
                                />
                            </div>
                            {canAssign && (
                                <div className="classroom-detail-teacher">
                                    <label
                                        htmlFor="section-class-teacher"
                                        className="text-muted-foreground text-xs font-semibold whitespace-nowrap"
                                    >
                                        Class teacher
                                    </label>
                                    <Select
                                        id="section-class-teacher"
                                        value={detail.classTeacher?.employeeId ?? ""}
                                        disabled={saving || teachersQuery.isPending}
                                        onChange={askClassTeacherChange}
                                        aria-label="Class teacher"
                                        title="Class teacher for this section"
                                    >
                                        <option value="">Unassigned</option>
                                        {teacherOptions.map((teacher) => (
                                            <option
                                                key={teacher.employeeId}
                                                value={teacher.employeeId}
                                            >
                                                {titleCase(teacher.name)}
                                            </option>
                                        ))}
                                    </Select>
                                    {saving && (
                                        <span className="text-muted-foreground text-xs">
                                            Saving…
                                        </span>
                                    )}
                                    {!saving && teachersQuery.isError && (
                                        <span className="text-xs text-red-500">
                                            Teacher list unavailable
                                        </span>
                                    )}
                                    {error && (
                                        <span className="text-xs text-red-500" role="alert">
                                            {error}
                                        </span>
                                    )}
                                </div>
                            )}
                        </div>
                        <div className="classroom-detail-tab-intro" aria-live="polite">
                            <h3>{activeTab}</h3>
                            {TAB_DESCRIPTIONS[activeTab] && <p>{TAB_DESCRIPTIONS[activeTab]}</p>}
                        </div>
                        <div className="mt-4">
                            {activeTab === "Students" ? (
                                <StudentsPanel
                                    className={detail.className}
                                    section={detail.sectionName}
                                    sectionId={detail.sectionId}
                                />
                            ) : activeTab === "Attendance" ? (
                                <AttendancePanel sectionId={detail.sectionId} />
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

            <Modal
                open={pendingTeacher !== null}
                title="Change class teacher?"
                onClose={() => {
                    if (!saving) setPendingTeacher(null);
                }}
            >
                <div className="space-y-4">
                    <p className="text-muted-foreground text-sm">
                        Do you want to change the class teacher from{" "}
                        <strong>{pendingTeacher?.oldName}</strong> to{" "}
                        <strong>{pendingTeacher?.newName}</strong>?
                    </p>
                    <p className="text-muted-foreground text-xs">
                        The current year&apos;s assignment will be closed and the new teacher will
                        take over this class-section.
                    </p>
                    <div className="flex justify-end gap-2">
                        <Button
                            variant="outline"
                            disabled={saving}
                            onClick={() => setPendingTeacher(null)}
                        >
                            Cancel
                        </Button>
                        <Button
                            loading={saving}
                            disabled={saving}
                            onClick={() => {
                                if (pendingTeacher === null) return;
                                void assign(async () => {
                                    await setClassTeacher(sectionId, pendingTeacher.teacherId);
                                    setPendingTeacher(null);
                                });
                            }}
                        >
                            Change class teacher
                        </Button>
                    </div>
                </div>
            </Modal>
        </div>
    );
}
