"use client";

import { useEffect, useMemo, useState } from "react";
import { Badge, Button, PageHeader, Select, Spinner, Table, Tabs } from "@/components/ui";
import { DatePicker } from "@/components/ui/date-picker";
import { useToast } from "@/components/ui/toast";
import { useAuth } from "@/providers/auth-context";
import { hasAnyRole, isStudent, isParent, ACADEMIC_STAFF_ROLES } from "@/lib/auth/rbac";
import { getIrregularStudents, getLeaveSync } from "@/services";
import { useApiQuery } from "@/lib/api/use-api-query";
import type { IrregularStudent, LeaveSyncRow } from "@/types";
import { useAttendance } from "./useAttendance";
import MarkAttendanceTab from "./MarkAttendanceTab";
import AttendanceHistoryTab from "./AttendanceHistoryTab";
import { SummaryStrip, WeeklyTrendCard } from "./AttendanceWidgets";
import AttentionList from "./AttentionList";

// PAGE 04 — Attendance. Container: tabs, shared filters, save flow.
export default function AttendancePage() {
    const toast = useToast();
    const { user } = useAuth();
    const att = useAttendance();

    const isStudentUser = isStudent(user?.roles);
    const isParentUser = isParent(user?.roles);
    const canMarkAttendance = hasAnyRole(user?.roles, ACADEMIC_STAFF_ROLES);
    const canViewInsights = hasAnyRole(user?.roles, [
        "DIRECTOR",
        "ADMIN",
        "PRINCIPAL",
        "HOD",
        "CLASS_TEACHER",
    ]);
    const canViewLeaveSync = hasAnyRole(user?.roles, ACADEMIC_STAFF_ROLES);

    const allowedTabs = useMemo(() => {
        if (isStudentUser) return ["My Attendance"];
        if (isParentUser) return ["Child's Attendance"];
        const tabs = ["Mark attendance", "History"];
        if (canViewInsights) tabs.push("Irregularity & Insights");
        if (canViewLeaveSync) tabs.push("Leave Sync");
        return tabs;
    }, [isStudentUser, isParentUser, canViewInsights, canViewLeaveSync]);

    const [tab, setTab] = useState(() => (canMarkAttendance ? "Mark attendance" : "History"));
    const activeTab = allowedTabs.includes(tab) ? tab : allowedTabs[0];

    const [statusFilter, setStatusFilter] = useState("all");
    const insightsEnabled = canViewInsights || canViewLeaveSync;
    const irregularQuery = useApiQuery(["attendance", "irregular"], getIrregularStudents, {
        enabled: canViewInsights,
    });
    const leaveSyncQuery = useApiQuery(["attendance", "leave-sync"], getLeaveSync, {
        enabled: canViewLeaveSync,
    });
    const irregular = irregularQuery.data ?? [];
    const leaveSync = leaveSyncQuery.data ?? [];
    const insightsLoading =
        insightsEnabled && (irregularQuery.isPending || leaveSyncQuery.isPending);

    const [historyPage, setHistoryPage] = useState(1);
    const historyPageSize = 5;

    function handleClassChange(newClass: string) {
        att.setClassName(newClass);
        setHistoryPage(1);
    }

    function handleStatusFilterChange(newStatus: string) {
        setStatusFilter(newStatus);
        setHistoryPage(1);
    }

    const userFullName = user?.fullName?.toLowerCase() ?? "";

    const filteredHistory = useMemo(
        () =>
            att.history.filter((r) => {
                if (isStudentUser && userFullName) {
                    const rowName = r.studentName.toLowerCase();
                    if (!rowName.includes(userFullName) && !userFullName.includes(rowName)) {
                        return false;
                    }
                } else if (isParentUser) {
                    // For demo parent Homer Simpson, child is Bart Simpson
                    const targetChild = "Bart";
                    if (!r.studentName.includes(targetChild)) {
                        return false;
                    }
                } else if (att.className !== "all") {
                    const normFilter = att.className.replace(/Grade\s*/i, "").trim();
                    const normRow = r.className.replace(/Grade\s*/i, "").trim();
                    if (!normRow.startsWith(normFilter)) return false;
                }

                if (statusFilter !== "all" && r.status !== statusFilter) return false;
                return true;
            }),
        [att.history, statusFilter, att.className, isStudentUser, isParentUser, userFullName],
    );

    const paginatedHistory = useMemo(() => {
        const start = (historyPage - 1) * historyPageSize;
        return filteredHistory.slice(start, start + historyPageSize);
    }, [filteredHistory, historyPage, historyPageSize]);

    function handleSave() {
        const records = att.save();
        if (!records) return;
        const present = records.filter((r) => r.status === "Present").length;
        toast.push("success", `Saved · ${present}/${records.length} present on ${records[0].date}`);
    }

    const pageTitle = isStudentUser
        ? "My Attendance"
        : isParentUser
          ? "Child Attendance"
          : "Daily Attendance";

    const pageSubtitle = isStudentUser
        ? "View your personal daily and monthly attendance record"
        : isParentUser
          ? "Track your child's attendance and absence records"
          : "Mark and track attendance for your classes";

    return (
        <div className="page">
            <PageHeader
                title={pageTitle}
                subtitle={pageSubtitle}
                actions={
                    activeTab === "Mark attendance" &&
                    canMarkAttendance && (
                        <Button onClick={handleSave} disabled={att.markedCount === 0}>
                            Save ({att.markedCount}/{att.roster.length})
                        </Button>
                    )
                }
            />

            <Tabs tabs={allowedTabs} active={activeTab} onChange={setTab} />

            <div className="toolbar">
                {!isStudentUser && !isParentUser && (
                    <Select
                        value={att.className}
                        onChange={(e) => handleClassChange(e.target.value)}
                        aria-label="Class"
                    >
                        <option value="all">All classes</option>
                        {att.classes.map((c) => (
                            <option key={c} value={c}>
                                Class {c}
                            </option>
                        ))}
                    </Select>
                )}

                {activeTab === "Mark attendance" && canMarkAttendance ? (
                    <>
                        <Select
                            value={att.section}
                            onChange={(e) => att.setSection(e.target.value)}
                            aria-label="Section"
                        >
                            {["A", "B", "C", "D"].map((sec) => (
                                <option key={sec} value={sec}>
                                    Section {sec}
                                </option>
                            ))}
                        </Select>
                        <DatePicker className="w-auto" value={att.date} onChange={att.setDate} />
                    </>
                ) : (
                    <Select
                        value={statusFilter}
                        onChange={(e) => handleStatusFilterChange(e.target.value)}
                        aria-label="Status"
                    >
                        <option value="all">All statuses</option>
                        <option>Present</option>
                        <option>Absent</option>
                        <option>Late</option>
                        <option>Leave</option>
                    </Select>
                )}
            </div>

            {att.loading ? (
                <Spinner />
            ) : activeTab === "Mark attendance" ? (
                <div className="two-col">
                    {/* left: summary strip + roster */}
                    <div className="two-col-main">
                        <SummaryStrip counts={att.counts} />
                        <MarkAttendanceTab
                            roster={att.roster}
                            marks={att.marks}
                            onSetMark={att.setMark}
                            onSetAll={att.setAll}
                            onReset={att.reset}
                        />
                    </div>

                    {/* right column: Weekly Trend + Attention Required (stitch) */}
                    <aside className="two-col-side">
                        <WeeklyTrendCard trend={att.weeklyTrend} />
                        <AttentionList alerts={att.alerts} />
                    </aside>
                </div>
            ) : activeTab === "Irregularity & Insights" ? (
                <Table
                    columns={[
                        {
                            key: "name",
                            header: "Student",
                            render: (r: IrregularStudent) => <b>{r.name}</b>,
                        },
                        { key: "className", header: "Class" },
                        { key: "absences", header: "Absences (term)" },
                        { key: "pattern", header: "AI pattern insight" },
                        {
                            key: "risk",
                            header: "Risk",
                            render: (r: IrregularStudent) => (
                                <Badge
                                    tone={
                                        r.risk === "High"
                                            ? "red"
                                            : r.risk === "Medium"
                                              ? "amber"
                                              : "green"
                                    }
                                >
                                    {r.risk}
                                </Badge>
                            ),
                        },
                    ]}
                    rows={irregular}
                    rowKey={(r) => r.id}
                    empty="No irregular attendance patterns detected."
                />
            ) : activeTab === "Leave Sync" ? (
                <Table
                    columns={[
                        {
                            key: "student",
                            header: "Student",
                            render: (r: LeaveSyncRow) => <b>{r.student}</b>,
                        },
                        { key: "className", header: "Class" },
                        { key: "from", header: "From" },
                        { key: "days", header: "Days" },
                        { key: "autoMarked", header: "Attendance auto-marked as" },
                        {
                            key: "status",
                            header: "Sync status",
                            render: (r: LeaveSyncRow) => (
                                <Badge
                                    tone={
                                        r.status === "Synced"
                                            ? "green"
                                            : r.status === "Pending"
                                              ? "amber"
                                              : "muted"
                                    }
                                >
                                    {r.status}
                                </Badge>
                            ),
                        },
                    ]}
                    rows={leaveSync}
                    rowKey={(r) => r.id}
                    empty="No leave-attendance sync records."
                />
            ) : (
                <AttendanceHistoryTab
                    rows={paginatedHistory}
                    totalItems={filteredHistory.length}
                    page={historyPage}
                    pageSize={historyPageSize}
                    onPageChange={setHistoryPage}
                />
            )}
        </div>
    );
}
