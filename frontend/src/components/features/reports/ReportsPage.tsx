"use client";
import { useState } from "react";
import {
    PageHeader,
    Card,
    Badge,
    Spinner,
    Table,
    Tabs,
    Button,
    Select,
    type BadgeTone,
} from "@/components/ui";
import RoleGuard from "@/components/auth/RoleGuard";
import { getEducationReports } from "@/services";
import { useApiQuery } from "@/lib/api/use-api-query";
import { DatePicker } from "@/components/ui/date-picker";
import type { DataQualityRow, EducationReportRow } from "@/types";
import { useReports } from "./useReports";

type ReportTab = "Report Builder" | "Director Center" | "Education" | "Data Quality";
const TABS: ReportTab[] = ["Report Builder", "Director Center", "Education", "Data Quality"];

const qTone: Record<DataQualityRow["status"], BadgeTone> = {
    Healthy: "green",
    Attention: "amber",
    Critical: "red",
};

export default function ReportsPage() {
    const r = useReports();
    const [tab, setTab] = useState<ReportTab>("Director Center");
    const eduQuery = useApiQuery(["reports", "education"], getEducationReports);
    const edu = eduQuery.data ?? [];
    const [fromDate, setFromDate] = useState("");
    const [toDate, setToDate] = useState("");

    const qualityCols = [
        { key: "area", header: "Data area", render: (row: DataQualityRow) => <b>{row.area}</b> },
        { key: "score", header: "Quality score", render: (row: DataQualityRow) => `${row.score}%` },
        { key: "issue", header: "Open issue" },
        {
            key: "status",
            header: "Status",
            render: (row: DataQualityRow) => <Badge tone={qTone[row.status]}>{row.status}</Badge>,
        },
    ];

    return (
        <RoleGuard
            allowedRoles={["SCHOOL_ADMIN", "PRINCIPAL", "HOD", "ACCOUNTANT", "SYSTEM_ADMIN"]}
        >
            <div>
                <PageHeader
                    title="Reports & Analytics"
                    subtitle="School-wide health metrics, report builder and data quality monitoring."
                />

                {r.loading ? (
                    <Spinner />
                ) : (
                    <>
                        <Tabs tabs={TABS} active={tab} onChange={(t) => setTab(t as ReportTab)} />

                        {tab === "Director Center" && (
                            <>
                                <div className="stat-tiles">
                                    <div className="stat-tile">
                                        {/* "No number prints —, not 0": the three seeded
                                            report tables have no writer yet, and 0% would
                                            read as a measured score. */}
                                        <b>{r.quality.length === 0 ? "—" : `${r.avgScore}%`}</b>
                                        <span>Avg data quality</span>
                                    </div>
                                    <div className="stat-tile">
                                        <b>{r.quality.length === 0 ? "—" : r.attentionCount}</b>
                                        <span>Needs attention</span>
                                    </div>
                                    <div className="stat-tile">
                                        <b>{r.quality.length === 0 ? "—" : r.criticalCount}</b>
                                        <span>Critical</span>
                                    </div>
                                </div>
                                {r.quality.length === 0 && (
                                    <p className="text-muted-foreground mb-2 text-xs">
                                        Nothing is stored in the data-quality table for this school
                                        yet, so these three read “—”. The staff figures below are
                                        read live from the register, the timetable and the current
                                        season.
                                    </p>
                                )}
                                <Card title="Staff — this term">
                                    {r.staffLoading && <Spinner />}
                                    {r.staffError !== null && (
                                        <p className="text-muted-foreground text-sm">
                                            The staff figures could not be loaded.
                                        </p>
                                    )}
                                    {r.staff !== null && (
                                        <div className="grid gap-2 text-sm">
                                            <div>
                                                <b>{r.staff.attendance.percent}%</b> staff
                                                attendance · {r.staff.attendance.marked} days marked
                                                of a month, {r.staff.attendance.present} present /{" "}
                                                {r.staff.attendance.absent} absent (
                                                {r.staff.attendance.windowStart} —{" "}
                                                {r.staff.attendance.windowEnd})
                                            </div>
                                            <div>
                                                <b>{r.staff.workload.periods}</b> periods across{" "}
                                                {r.staff.workload.teachers} teachers ·{" "}
                                                {r.staff.workload.under} under,{" "}
                                                {r.staff.workload.normal} normal,{" "}
                                                {r.staff.workload.over} over a{" "}
                                                {r.staff.workload.capacity}-period week (
                                                {r.staff.workload.capacitySource === "rule"
                                                    ? "the school's rule"
                                                    : "the heaviest timetable"}
                                                )
                                            </div>
                                            <div>
                                                <b>{r.staff.appraisals.finalized}</b> of{" "}
                                                {r.staff.appraisals.total} appraisals finalised
                                                {r.staff.appraisals.cycle
                                                    ? ` in ${r.staff.appraisals.cycle}`
                                                    : ""}
                                                {r.staff.appraisals.averageReviewerRating !== null
                                                    ? ` · reviewers average ${r.staff.appraisals.averageReviewerRating}/5`
                                                    : ""}
                                            </div>
                                            <p className="text-muted-foreground text-xs">
                                                Read from the register, the timetable and the
                                                current season — nothing here is a stored snapshot,
                                                so it includes this morning. Scope: {r.staff.scope}{" "}
                                                ({r.staff.people} people).
                                            </p>
                                        </div>
                                    )}
                                </Card>
                                <div className="kpi-grid" style={{ marginTop: 16 }}>
                                    {r.cards.map((c) => (
                                        <Card key={c.id} title={c.title}>
                                            <p className="muted">{c.metric}</p>
                                            <h3>{c.value}</h3>
                                            <Badge tone={c.tone}>{c.trend}</Badge>
                                        </Card>
                                    ))}
                                </div>
                            </>
                        )}

                        {tab === "Report Builder" && (
                            <Card title="Build a custom report">
                                <div className="form-grid">
                                    <Select label="Dataset">
                                        <option>Fee collection</option>
                                        <option>Attendance</option>
                                        <option>Exam results</option>
                                        <option>Payroll</option>
                                    </Select>
                                    <Select label="Group by">
                                        <option>Class</option>
                                        <option>Fee head</option>
                                        <option>Month</option>
                                    </Select>
                                    <DatePicker
                                        label="From date"
                                        value={fromDate}
                                        onChange={setFromDate}
                                    />
                                    <DatePicker
                                        label="To date"
                                        value={toDate}
                                        onChange={setToDate}
                                    />
                                </div>
                                <div className="modal-actions">
                                    {/* The export job does not exist yet, and a button
                                        that raises `alert("… (mock)")` is a promise the
                                        product cannot keep. The form stays (it is the
                                        shape the job will take) and says so. */}
                                    <Button variant="primary" disabled>
                                        Generate
                                    </Button>
                                    <Button variant="outline" disabled>
                                        Schedule weekly
                                    </Button>
                                </div>
                                <p className="text-muted-foreground mt-2 text-xs">
                                    Export is not built yet — nothing here is sent, stored or
                                    emailed. When it is, it will stream the dataset above as
                                    Excel/PDF from the same tables the rest of the screen reads.
                                </p>
                            </Card>
                        )}

                        {tab === "Education" && (
                            <Table
                                columns={[
                                    {
                                        key: "metric",
                                        header: "Metric",
                                        render: (row: EducationReportRow) => <b>{row.metric}</b>,
                                    },
                                    { key: "className", header: "Scope" },
                                    { key: "value", header: "Value" },
                                    {
                                        key: "trend",
                                        header: "Trend",
                                        render: (row: EducationReportRow) => (
                                            <Badge
                                                tone={row.trend.includes("-") ? "amber" : "green"}
                                            >
                                                {row.trend}
                                            </Badge>
                                        ),
                                    },
                                ]}
                                rows={edu}
                                rowKey={(row) => row.id}
                                empty="No education reports yet."
                            />
                        )}

                        {tab === "Data Quality" && (
                            <Table
                                columns={qualityCols}
                                rows={r.quality}
                                rowKey={(row) => row.id}
                                empty="No data quality issues found."
                            />
                        )}
                    </>
                )}
            </div>
        </RoleGuard>
    );
}
