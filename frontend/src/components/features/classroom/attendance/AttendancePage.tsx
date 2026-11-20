"use client";

import { useEffect, useMemo, useState } from "react";
import { Badge, Button, PageHeader, Select, Spinner, Table, Tabs } from "@/components/ui";
import AcademicYearRequiredBanner from "@/components/layout/AcademicYearRequiredBanner";
import { DatePicker } from "@/components/ui/date-picker";
import { useToast } from "@/components/ui/toast";
import { useAuth } from "@/providers/auth-context";
import { hasAnyRole, isStudent, isParent, ACADEMIC_STAFF_ROLES } from "@/lib/auth/rbac";
import { errorMessage } from "@/lib/api/client";
import { getAttendance, getIrregularStudents, getLeaveSync } from "@/services";
import { useApiQuery } from "@/lib/api/use-api-query";
import { isClosedDay, isoDate } from "@/lib/attendance/view";
import type { IrregularStudent, LeaveSyncRow } from "@/types";
import { useAttendance } from "./useAttendance";
import MarkAttendanceTab from "./MarkAttendanceTab";
import AttendanceHistoryTab from "./AttendanceHistoryTab";
import { SummaryStrip, TrendCard } from "./AttendanceWidgets";
import AttentionList from "./AttentionList";
import StudentHistoryDialog from "./StudentHistoryDialog";

// PAGE 04 — Attendance (the school-wide screen).
//
// Phase 4: the class/section pickers now name a **real class-section** through the
// class catalogue, so "Mark attendance" here writes the same register the Classroom
// tab does - it is no longer a cache-only screen. The widgets beside the grid are the
// section's own numbers (`/summary`, `/trend`, `/attention`), and a closed day is
// shown with its reason instead of failing on Save.
export default function AttendancePage() {
    const toast = useToast();
    const { user } = useAuth();
    const att = useAttendance();

    const isStudentUser = isStudent(user?.roles);
    const isParentUser = isParent(user?.roles);
    const canMarkAttendance = hasAnyRole(user?.roles, ACADEMIC_STAFF_ROLES);
    const canViewInsights = hasAnyRole(user?.roles, [
        "SCHOOL_ADMIN",
        "SYSTEM_ADMIN",
        "PRINCIPAL",
        "HOD",
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
    /** The child whose register history is open, if any. (`history` below is the list.) */
    const [historyStudent, setHistoryStudent] = useState<{ id: string; name: string } | null>(null);
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

    // The school-wide register list behind the History tab (one page of it).
    const historyQuery = useApiQuery(["attendance", "list"], () => getAttendance());
    const history = useMemo(() => historyQuery.data ?? [], [historyQuery.data]);

    const [historyPage, setHistoryPage] = useState(1);
    const historyPageSize = 5;

    // Pick a real class-section as soon as the catalogue arrives, so "Mark attendance"
    // has somewhere to write instead of showing an empty register.
    useEffect(() => {
        if (att.sectionId || att.className) return;
        const firstClass = att.classNames[0];
        if (!firstClass) return;
        att.setClassName(firstClass);
        const firstSection = att.sectionsOf(firstClass)[0];
        if (firstSection) att.setSection(firstSection.name);
    }, [att]);

    function handleClassChange(newClass: string) {
        att.setClassName(newClass);
        const firstSection = att.sectionsOf(newClass)[0];
        if (firstSection) att.setSection(firstSection.name);
        setHistoryPage(1);
    }

    function handleStatusFilterChange(newStatus: string) {
        setStatusFilter(newStatus);
        setHistoryPage(1);
    }

    const userFullName = user?.fullName?.toLowerCase() ?? "";

    const filteredHistory = useMemo(
        () =>
            history.filter((r) => {
                if (isStudentUser && userFullName) {
                    const rowName = r.studentName.toLowerCase();
                    if (!rowName.includes(userFullName) && !userFullName.includes(rowName)) {
                        return false;
                    }
                } else if (att.className) {
                    if (!r.className.startsWith(att.className)) return false;
                }

                if (statusFilter !== "all" && r.status !== statusFilter) return false;
                return true;
            }),
        [history, statusFilter, att.className, isStudentUser, userFullName],
    );

    const paginatedHistory = useMemo(() => {
        const start = (historyPage - 1) * historyPageSize;
        return filteredHistory.slice(start, start + historyPageSize);
    }, [filteredHistory, historyPage, historyPageSize]);

    async function handleSave() {
        try {
            const result = await att.save();
            if (!result) return;
            toast.push(
                "success",
                `Saved · ${result.present}/${result.total} present on ${att.date}`,
            );
        } catch (cause) {
            toast.push("error", errorMessage(cause, "Could not save the register"));
        }
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

    const closedNote = att.isClosed
        ? `School closed — ${att.closedReason}. The register cannot be saved.`
        : null;
    /** A day in the future has no register: the server refuses the save with `422`. */
    const futureNote = att.isFuture
        ? "A future day cannot be marked - pick today or an earlier date."
        : null;

    // The same words the class-section page uses: "Saved" only while the day in front of
    // the teacher still matches the database.
    const saveLabel = att.hasSaved && !att.isDirty ? "Saved" : "Save";

    return (
        <div className="page">
            <PageHeader
                title={pageTitle}
                subtitle={pageSubtitle}
                actions={
                    activeTab === "Mark attendance" &&
                    canMarkAttendance && (
                        <Button
                            onClick={handleSave}
                            disabled={att.saving || !att.isDirty || att.isClosed || att.isFuture}
                            title={futureNote ?? closedNote ?? undefined}
                        >
                            {att.saving ? "Saving…" : saveLabel}
                        </Button>
                    )
                }
            />
            <AcademicYearRequiredBanner className="mb-4" />

            <Tabs tabs={allowedTabs} active={activeTab} onChange={setTab} />

            <div className="toolbar">
                {!isStudentUser && !isParentUser && (
                    <Select
                        value={att.className}
                        onChange={(e) => handleClassChange(e.target.value)}
                        aria-label="Class"
                    >
                        <option value="">Select a class</option>
                        {att.classNames.map((name) => (
                            <option key={name} value={name}>
                                {name}
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
                            <option value="">Select a section</option>
                            {att.sectionsOf(att.className).map((item) => (
                                <option key={item.name} value={item.name}>
                                    Section {item.name}
                                </option>
                            ))}
                        </Select>
                        <DatePicker
                            className="w-auto"
                            value={att.date}
                            onChange={att.setDate}
                            isClosedDay={(day) =>
                                isClosedDay(att.closedDays, day) ||
                                isoDate(day) > isoDate(new Date())
                            }
                        />
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

            {(closedNote || futureNote) && (
                <p className="text-sm text-amber-600" role="status">
                    {futureNote ?? closedNote}
                </p>
            )}

            {activeTab === "Mark attendance" && !att.sectionId ? (
                <p style={{ color: "var(--muted)" }}>
                    Choose a class and section to open its register.
                </p>
            ) : att.loading ? (
                <Spinner />
            ) : activeTab === "Mark attendance" ? (
                <div className="two-col">
                    <div className="two-col-main">
                        {!att.loadingWidgets && (
                            <p className="roster-caption">
                                {att.workingDays} open days
                                {att.attention.length > 0
                                    ? ` · ${att.attention.length} below ${att.threshold}%`
                                    : ""}
                            </p>
                        )}
                        <SummaryStrip counts={att.counts} />
                        <MarkAttendanceTab
                            rows={att.rosterRows}
                            onSetMark={att.setMark}
                            onSetAll={att.setAll}
                            onReset={att.reset}
                            disabled={att.isClosed || att.isFuture}
                        />
                    </div>

                    <aside className="two-col-side">
                        <TrendCard
                            bars={att.trendValues}
                            range={att.trendRange}
                            onRangeChange={att.setTrendRange}
                        />
                        <AttentionList
                            rows={att.attention}
                            threshold={att.threshold}
                            onOpen={(row) =>
                                setHistoryStudent({ id: row.studentId, name: row.name })
                            }
                        />
                    </aside>
                </div>
            ) : activeTab === "Irregularity & Insights" ? (
                insightsLoading ? (
                    <Spinner />
                ) : (
                    <Table
                        columns={[
                            {
                                key: "name",
                                header: "Student",
                                render: (r: IrregularStudent) => <b>{r.name}</b>,
                            },
                            { key: "className", header: "Class" },
                            { key: "absences", header: "Absences (term)" },
                            { key: "pattern", header: "Pattern" },
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
                )
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

            <StudentHistoryDialog
                open={Boolean(historyStudent)}
                student={historyStudent}
                onClose={() => setHistoryStudent(null)}
            />
        </div>
    );
}
