"use client";

import Link from "next/link";
import { getAttendance, getDashboard, getMarks, getStudents } from "@/services";
import { useApiQuery } from "@/lib/api/use-api-query";
import { Badge, Button, Card, Spinner, Table, type Column } from "@/components/ui";
import Icon from "@/components/ui/Icon";
import { useAuth } from "@/providers/auth-context";
import { hasAnyRole, hasPermission, LEADERSHIP_ROLES } from "@/lib/auth/rbac";
import type { Student } from "@/types";
import KpiGrid from "./KpiGrid";
import AttendanceChart from "./AttendanceChart";
import { BarChart } from "@/components/tremor/BarChart";
import DashboardFeeds from "./DashboardFeeds";
import AiInsightsCard from "./AiInsightsCard";
import QuickActions from "./QuickActions";
import RecentActivity from "./RecentActivity";

const STUDENT_COLUMNS: Column<Student>[] = [
    {
        key: "student",
        header: "Student",
        render: (student) => (
            <div className="flex min-w-0 flex-col">
                <span className="text-foreground truncate font-medium">{student.name}</span>
                <span className="text-muted-foreground text-xs">{student.admissionNo}</span>
            </div>
        ),
    },
    {
        key: "class",
        header: "Class",
        render: (student) =>
            student.className
                ? `${student.className}${student.section ? `-${student.section}` : ""}`
                : "Not placed",
    },
    {
        key: "status",
        header: "Status",
        render: (student) => (
            <Badge tone={student.status === "Active" ? "green" : "muted"}>{student.status}</Badge>
        ),
    },
];

// Director dashboard: school-wide metrics, trends, and operational updates.
export default function DirectorDashboard() {
    const { user } = useAuth();
    const dashboardQuery = useApiQuery(["dashboard"], getDashboard);
    const attendanceQuery = useApiQuery(["attendance"], () => getAttendance());
    const marksQuery = useApiQuery(["marks"], getMarks);
    const canViewStudents =
        (user?.role?.toUpperCase() === "DIRECTOR" || hasAnyRole(user?.roles, LEADERSHIP_ROLES)) &&
        hasPermission(user?.permissions, "students.read");
    const studentsQuery = useApiQuery(
        ["dashboard", "students", user?.id, user?.schoolId, user?.impersonatedBy?.id],
        () => getStudents(0, 5),
        { enabled: canViewStudents },
    );
    const data = dashboardQuery.data ?? null;
    const attendance = attendanceQuery.data ?? [];
    const marks = marksQuery.data ?? [];

    if (!data) return <Spinner />;

    const now = new Date();
    const today = now.toLocaleDateString(undefined, {
        weekday: "long",
        day: "numeric",
        month: "long",
    });
    const firstName = user?.fullName.trim().split(/\s+/)[0] || "there";
    const absentToday = attendance.filter((a) => a.status === "Absent").length;

    return (
        <div className="dashboard-page mx-auto w-full max-w-[1440px] space-y-6">
            <section className="dashboard-hero">
                <div className="dashboard-hero-content">
                    <div className="relative z-10 max-w-2xl">
                        <p className="dashboard-hero-eyebrow">
                            YOUR SCHOOL · {today.toUpperCase()}
                        </p>
                        <h1 className="mt-3 text-3xl font-semibold tracking-tight sm:text-4xl">
                            Welcome back, {firstName}
                        </h1>
                        <p className="mt-3 max-w-xl text-sm leading-6 sm:text-base">
                            A quick look at how your school is doing — and what needs attention
                            next.
                        </p>
                        <div className="mt-6 flex flex-wrap items-center gap-2.5">
                            <Link href="/dashboard/attendance" className="dashboard-hero-action">
                                <Icon name="attendance" size={17} />
                                Review attendance
                            </Link>
                            <Button variant="outline" size="sm">
                                <Icon name="download" size={16} /> Export
                            </Button>
                            <Button
                                size="sm"
                                onClick={() => window.dispatchEvent(new Event("open-copilot"))}
                            >
                                <Icon name="ai" size={16} /> Ask EduConnect AI
                            </Button>
                        </div>
                    </div>

                    <div className="dashboard-hero-panel">
                        <div className="flex items-center gap-3">
                            <span className="dashboard-hero-school-icon">
                                <Icon name="school" size={21} />
                            </span>
                            <div>
                                <p className="text-sm font-semibold">School snapshot</p>
                                <p className="text-xs opacity-70">A little look at what’s ahead</p>
                            </div>
                        </div>
                        <div className="mt-5 grid grid-cols-2 gap-3">
                            <div className="dashboard-hero-stat dashboard-hero-stat--teal">
                                <Icon name="calendar" size={17} />
                                <span className="text-2xl font-semibold">
                                    {data.upcoming.length}
                                </span>
                                <span className="text-xs">upcoming events</span>
                            </div>
                            <div className="dashboard-hero-stat dashboard-hero-stat--coral">
                                <Icon name="book" size={17} />
                                <span className="text-2xl font-semibold">
                                    {data.notices.length}
                                </span>
                                <span className="text-xs">school notices</span>
                            </div>
                        </div>
                    </div>
                </div>
                <span className="dashboard-hero-orb dashboard-hero-orb--teal" aria-hidden="true" />
                <span className="dashboard-hero-orb dashboard-hero-orb--coral" aria-hidden="true" />
            </section>

            <KpiGrid kpis={data.kpis} />

            <div className="grid grid-cols-1 gap-5 xl:grid-cols-12">
                <Card
                    title="Attendance this week"
                    className="dashboard-card xl:col-span-8"
                    action={
                        <Badge tone="green">
                            {attendance.length - absentToday}/{attendance.length} present
                        </Badge>
                    }
                >
                    <AttendanceChart trend={data.attendanceTrend} />
                </Card>

                <div className="flex flex-col gap-5 xl:col-span-4">
                    <AiInsightsCard />
                    <QuickActions />
                </div>

                {canViewStudents && (
                    <Card
                        title="Student overview"
                        className="dashboard-card xl:col-span-12"
                        action={
                            <Link
                                href="/dashboard/classroom"
                                className="text-primary inline-flex items-center gap-1 text-sm font-medium hover:underline"
                            >
                                View classroom
                                <Icon name="students" size={15} />
                            </Link>
                        }
                    >
                        {studentsQuery.isPending ? (
                            <Spinner size="sm" />
                        ) : studentsQuery.isError ? (
                            <div
                                className="border-border bg-background/70 flex flex-wrap items-center justify-between gap-3 rounded-lg border p-4"
                                role="alert"
                            >
                                <div>
                                    <p className="text-foreground text-sm font-medium">
                                        Student list could not be loaded.
                                    </p>
                                    <p className="text-muted-foreground mt-1 text-xs">
                                        {studentsQuery.error.message}
                                    </p>
                                </div>
                                <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => void studentsQuery.refetch()}
                                >
                                    Retry
                                </Button>
                            </div>
                        ) : (
                            <Table
                                columns={STUDENT_COLUMNS}
                                rows={studentsQuery.data ?? []}
                                rowKey={(student) => student.id}
                                empty="No students found."
                            />
                        )}
                    </Card>
                )}

                <Card
                    title="Class performance"
                    className="dashboard-card xl:col-span-8"
                    action={
                        <span className="text-muted-foreground text-xs">Attendance and marks</span>
                    }
                >
                    <BarChart
                        data={data.classReport}
                        index="name"
                        categories={["attending", "marks"]}
                        colors={["var(--chart-1)", "var(--chart-2)"]}
                        valueFormatter={(val) => `${val}%`}
                        layout="vertical"
                        yAxisWidth={48}
                        className="mt-4 h-64"
                    />
                </Card>

                <RecentActivity />

                <DashboardFeeds upcoming={data.upcoming} marks={marks} notices={data.notices} />
            </div>
        </div>
    );
}
