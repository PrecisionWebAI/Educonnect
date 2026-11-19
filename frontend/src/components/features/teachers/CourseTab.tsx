"use client";

import { useMemo, useState } from "react";
import {
    Badge,
    Button,
    Input,
    Pagination,
    Spinner,
    Table,
    type Column,
} from "@/components/ui";
import { errorMessage } from "@/lib/api/client";
import { useApiQuery } from "@/lib/api/use-api-query";
import { getCourseSummary, getCourseTeachers } from "@/services";
import type { CourseTeacherRow } from "@/types";

import TeacherCourseDetail from "./TeacherCourseDetail";

/**
 * People -> Teachers -> Course.
 *
 * The list is the server's aggregate: subjects, sections, pending approvals and how many
 * subjects are behind their planned date. Clicking a name opens the same detail the teacher
 * sees on their own "My course", so the office and the teacher read one shape.
 */
export default function CourseTab() {
    const [query, setQuery] = useState("");
    const [page, setPage] = useState(1);
    const [pageSize] = useState(10);
    const [selected, setSelected] = useState<string | null>(null);

    const teachers = useApiQuery(["course", "teachers", query], () =>
        getCourseTeachers({ q: query, limit: 200 }),
    );
    const summary = useApiQuery(["course", "summary"], getCourseSummary);

    const rows = teachers.data ?? [];
    const paginated = useMemo(() => {
        const start = (page - 1) * pageSize;
        return rows.slice(start, start + pageSize);
    }, [rows, page, pageSize]);

    if (selected) {
        return (
            <TeacherCourseDetail
                employeeId={selected}
                onBack={() => setSelected(null)}
            />
        );
    }

    const columns: Column<CourseTeacherRow>[] = [
        {
            key: "name",
            header: "Teacher",
            render: (row) => (
                <div className="flex flex-col">
                    <Button
                        size="sm"
                        variant="ghost"
                        className="h-auto justify-start px-0 font-semibold"
                        onClick={() => setSelected(row.employeeId)}
                    >
                        {row.name}
                    </Button>
                    <span className="text-muted-foreground text-xs">
                        {row.employeeCode ?? "—"}
                        {row.department ? ` · ${row.department}` : ""}
                    </span>
                </div>
            ),
        },
        {
            key: "subjects",
            header: "Subjects",
            align: "right",
            render: (row) => (
                <span>
                    {row.subjectsCount}
                    <span className="text-muted-foreground text-xs">
                        {" "}
                        / {row.sectionsCount} section{row.sectionsCount === 1 ? "" : "s"}
                    </span>
                </span>
            ),
        },
        {
            key: "pending",
            header: "Pending approvals",
            align: "right",
            render: (row) => (
                <Badge tone={row.pendingApprovals > 0 ? "amber" : "muted"}>
                    {row.pendingApprovals}
                </Badge>
            ),
        },
        {
            key: "behind",
            header: "Behind",
            align: "right",
            render: (row) => (
                <Badge tone={row.behindSubjects > 0 ? "red" : "muted"}>
                    {row.behindSubjects}
                </Badge>
            ),
        },
        {
            key: "completion",
            header: "Completion",
            align: "right",
            render: (row) =>
                row.completionPercent === null ? "—" : `${row.completionPercent}%`,
        },
    ];

    return (
        <div className="space-y-3">
            <div className="stat-tiles">
                <div className="stat-tile">
                    <b>{summary.data?.subjectCount ?? "—"}</b>
                    <span>Subjects</span>
                </div>
                <div className="stat-tile">
                    <b>{summary.data?.pendingApprovals ?? "—"}</b>
                    <span>Pending approvals</span>
                </div>
                <div className="stat-tile">
                    <b>
                        {summary.data?.completionPercent === null ||
                        summary.data?.completionPercent === undefined
                            ? "—"
                            : `${summary.data.completionPercent}%`}
                    </b>
                    <span>Course completion</span>
                </div>
            </div>

            <div className="toolbar">
                <div className="toolbar-search">
                    <Input
                        placeholder="Search name, code or department…"
                        value={query}
                        onChange={(event) => {
                            setQuery(event.target.value);
                            setPage(1);
                        }}
                    />
                </div>
            </div>

            {teachers.isPending ? (
                <Spinner />
            ) : teachers.error ? (
                <p className="text-sm text-red-500">
                    {errorMessage(
                        teachers.error,
                        "The teachers' course list could not be loaded.",
                    )}
                </p>
            ) : (
                <Table
                    columns={columns}
                    rows={paginated}
                    rowKey={(row) => row.employeeId}
                    empty="No teacher has a course assignment yet."
                />
            )}

            <Pagination
                currentPage={page}
                totalItems={rows.length}
                pageSize={pageSize}
                onPageChange={setPage}
            />
        </div>
    );
}
