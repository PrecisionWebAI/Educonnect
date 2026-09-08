"use client";

import Link from "next/link";
import { getAttendance, getDashboard, getMarks } from "@/services";
import { useApiQuery } from "@/lib/api/use-api-query";
import { Badge, Button, Card, PageHeader, Spinner } from "@/components/ui";
import Icon from "@/components/ui/Icon";
import KpiGrid from "./KpiGrid";
import AttendanceChart from "./AttendanceChart";
import { BarChart } from "@/components/tremor/BarChart";
import DashboardFeeds from "./DashboardFeeds";
import AiInsightsCard from "./AiInsightsCard";
import QuickActions from "./QuickActions";
import RecentActivity from "./RecentActivity";

// Tab D.1 — Director Dashboard (purple). Admin overview widgets.
export default function DirectorDashboard() {
    const dashboardQuery = useApiQuery(["dashboard"], getDashboard);
    const attendanceQuery = useApiQuery(["attendance"], () => getAttendance());
    const marksQuery = useApiQuery(["marks"], getMarks);
    const data = dashboardQuery.data ?? null;
    const attendance = attendanceQuery.data ?? [];
    const marks = marksQuery.data ?? [];

    if (!data) return <Spinner />;

    const today = new Date().toLocaleDateString("en-IN", {
        weekday: "long",
        day: "numeric",
        month: "long",
    });
    const absentToday = attendance.filter((a) => a.status === "Absent").length;
    const maxMarks = Math.max(...data.classReport.map((c) => c.marks));

    return (
        <div className="page">
            <PageHeader
                title="Director Overview"
                subtitle={today}
                actions={
                    <>
                        <Button variant="outline" size="sm">
                            <Icon name="download" size={16} /> Export
                        </Button>
                        <Link className="btn btn-gradient btn-sm" href="/dashboard/ai-copilot">
                            <Icon name="ai" size={16} /> Ask EduConnect AI
                        </Link>
                    </>
                }
            />

            <KpiGrid kpis={data.kpis} />

            <div className="dash-grid">
                <Card
                    title="Attendance this week"
                    className="dash-span-2"
                    action={
                        <Badge tone="green">
                            {attendance.length - absentToday}/{attendance.length} present
                        </Badge>
                    }
                >
                    <AttendanceChart trend={data.attendanceTrend} />
                </Card>

                <AiInsightsCard />

                <Card title="Class-wise · attending vs marks">
                    <BarChart
                        data={data.classReport}
                        index="name"
                        categories={["attending", "marks"]}
                        colors={["var(--chart-1)", "var(--chart-2)"]}
                        valueFormatter={(val) => `${val}%`}
                        layout="vertical"
                        yAxisWidth={48}
                        className="h-64 mt-4"
                    />
                </Card>

                <QuickActions />

                <DashboardFeeds upcoming={data.upcoming} marks={marks} notices={data.notices} />

                <RecentActivity />
            </div>
        </div>
    );
}
