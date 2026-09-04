"use client";

import { useEffect, useMemo, useState } from "react";
import { Badge, Button, PageHeader, Select, Spinner, Table, Tabs } from "@/components/ui";
import { useToast } from "@/components/ui/toast";
import { getIrregularStudents, getLeaveSync } from "@/services";
import type { IrregularStudent, LeaveSyncRow } from "@/types";
import { useAttendance } from "./useAttendance";
import MarkAttendanceTab from "./MarkAttendanceTab";
import AttendanceHistoryTab from "./AttendanceHistoryTab";
import { SummaryStrip, WeeklyTrendCard } from "./AttendanceWidgets";
import AttentionList from "./AttentionList";

// PAGE 04 — Attendance. Container: tabs, shared filters, save flow.
export default function AttendancePage() {
    const toast = useToast();
    const att = useAttendance();
    const [tab, setTab] = useState("Mark attendance");
    const [statusFilter, setStatusFilter] = useState("all");
    const [irregular, setIrregular] = useState<IrregularStudent[]>([]);
    const [leaveSync, setLeaveSync] = useState<LeaveSyncRow[]>([]);

    useEffect(() => {
        let alive = true;
        Promise.all([getIrregularStudents(), getLeaveSync()]).then(([ir, ls]) => {
            if (!alive) return;
            setIrregular(ir);
            setLeaveSync(ls);
        });
        return () => {
            alive = false;
        };
    }, []);

    const filteredHistory = useMemo(
        () =>
            att.history.filter((r) => {
                if (statusFilter !== "all" && r.status !== statusFilter) return false;
                if (att.className !== "all" && !r.className.startsWith(att.className)) return false;
                return true;
            }),
        [att.history, statusFilter, att.className],
    );

    function handleSave() {
        const records = att.save();
        if (!records) return;
        const present = records.filter((r) => r.status === "Present").length;
        toast.push("success", `Saved · ${present}/${records.length} present on ${records[0].date}`);
    }

    return (
        <div className="page">
            <PageHeader
                title="Daily Attendance"
                subtitle="Mark and track attendance for your classes"
                actions={
                    tab === "Mark attendance" && (
                        <Button onClick={handleSave} disabled={att.markedCount === 0}>
                            Save ({att.markedCount}/{att.roster.length})
                        </Button>
                    )
                }
            />

            <Tabs
                tabs={["Mark attendance", "History", "Irregularity & Insights", "Leave Sync"]}
                active={tab}
                onChange={setTab}
            />

            <div className="toolbar">
                <Select
                    value={att.className}
                    onChange={(e) => att.setClassName(e.target.value)}
                    aria-label="Class"
                >
                    <option value="all">All classes</option>
                    {att.classes.map((c) => (
                        <option key={c} value={c}>
                            Class {c}
                        </option>
                    ))}
                </Select>

                {tab === "Mark attendance" ? (
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
                        <input
                            className="input"
                            type="date"
                            style={{ width: "auto" }}
                            value={att.date}
                            onChange={(e) => att.setDate(e.target.value)}
                            aria-label="Date"
                        />
                    </>
                ) : (
                    <Select
                        value={statusFilter}
                        onChange={(e) => setStatusFilter(e.target.value)}
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
            ) : tab === "Mark attendance" ? (
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
            ) : tab === "Irregularity & Insights" ? (
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
            ) : tab === "Leave Sync" ? (
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
                <AttendanceHistoryTab rows={filteredHistory} />
            )}
        </div>
    );
}
