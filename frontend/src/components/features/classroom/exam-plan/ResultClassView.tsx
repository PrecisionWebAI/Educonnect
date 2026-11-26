"use client";

import { useState } from "react";
import { Badge, Button, Modal, Table, type Column } from "@/components/ui";
import {
    groupByExam,
    passFailText,
    percentGradeText,
    statsCells,
    subjectColumns,
    subjectOf,
    testLabel,
} from "@/lib/exams/results";
import { figureText } from "@/lib/exams/view";
import type { OverviewStudent, OverviewTest, ResultOverview } from "@/types";
import StudentResultDetail from "./StudentResultDetail";

// The **class view** of the Exam Result tab - for the teachers and leadership of a section.
//
//   1. each test: the class average, the highest and lowest marks, how many passed and
//      failed, how many were absent (absent children are in none of the figures);
//   2. each child: subject-wise percentage so far, overall percentage, tests passed and
//      failed - and a Details button with their test-by-test result.
//
// A test that is not published yet is listed (so the teacher can see what is still to do)
// but carries no figures and counts nowhere.

export default function ResultClassView({ data }: { data: ResultOverview }) {
    const [open, setOpen] = useState<OverviewStudent | null>(null);
    const subjects = subjectColumns(data.students);
    const mode = data.displayMode;
    const groups = groupByExam(data.tests);

    const testColumns: Column<OverviewTest>[] = [
        {
            key: "test",
            header: "Test",
            render: (test) => (
                <div className="min-w-0">
                    <p className="truncate text-sm font-medium">{testLabel(test)}</p>
                    <p className="text-muted-foreground truncate text-xs">{test.examName}</p>
                </div>
            ),
        },
        {
            key: "total",
            header: "Total",
            align: "right",
            render: (test) => (
                <span className="text-sm tabular-nums">{figureText(test.totalMarks)}</span>
            ),
        },
        {
            key: "average",
            header: "Class average",
            align: "right",
            render: (test) => <Cell test={test} pick="average" />,
        },
        {
            key: "highest",
            header: "Highest",
            align: "right",
            render: (test) => <Cell test={test} pick="highest" />,
        },
        {
            key: "lowest",
            header: "Lowest",
            align: "right",
            render: (test) => <Cell test={test} pick="lowest" />,
        },
        {
            key: "passed",
            header: "Passed",
            align: "right",
            render: (test) => <Cell test={test} pick="passed" />,
        },
        {
            key: "failed",
            header: "Failed",
            align: "right",
            render: (test) => <Cell test={test} pick="failed" />,
        },
        {
            key: "absent",
            header: "Absent",
            align: "right",
            render: (test) => <Cell test={test} pick="absent" />,
        },
    ];

    const studentColumns: Column<OverviewStudent>[] = [
        {
            key: "student",
            header: "Student",
            render: (student) => (
                <div className="min-w-0">
                    <p className="truncate text-sm font-medium">{student.name}</p>
                    <p className="text-muted-foreground text-xs">
                        {student.admissionNumber ?? "—"}
                    </p>
                </div>
            ),
        },
        ...subjects.map((name): Column<OverviewStudent> => ({
            key: `subject-${name}`,
            header: name,
            render: (student) => {
                const line = subjectOf(student, name);
                return (
                    <span className="text-sm tabular-nums">
                        {line ? percentGradeText(line.percentage, line.grade, mode) : "—"}
                    </span>
                );
            },
        })),
        {
            key: "overall",
            header: "Overall",
            render: (student) => (
                <span className="text-sm font-semibold tabular-nums">
                    {percentGradeText(student.overall.percentage, student.overall.grade, mode)}
                </span>
            ),
        },
        {
            key: "passfail",
            header: "Tests",
            render: (student) => (
                <span className="text-muted-foreground text-xs">
                    {passFailText(student.overall.testsPassed, student.overall.testsFailed)}
                </span>
            ),
        },
        {
            key: "details",
            header: "",
            align: "right",
            render: (student) => (
                <Button
                    size="sm"
                    variant="ghost"
                    disabled={student.entries.length === 0}
                    onClick={() => setOpen(student)}
                >
                    Details
                </Button>
            ),
        },
    ];

    return (
        <div className="space-y-5">
            {data.unpublished > 0 && (
                <p className="text-sm text-amber-600" role="status">
                    {data.unpublished} {data.unpublished === 1 ? "test is" : "tests are"} not
                    published yet. {data.unpublished === 1 ? "It" : "They"} count nowhere until the
                    marks are published.
                </p>
            )}

            <section className="space-y-2">
                <h3 className="text-sm font-semibold">
                    Tests · {data.section || "this class-section"}
                </h3>
                {groups.length > 1 && (
                    <p className="text-muted-foreground text-xs">
                        {groups.length} {data.kind === "class_test" ? "class tests" : "exams"}, in
                        the order they were held.
                    </p>
                )}
                <Table
                    columns={testColumns}
                    rows={data.tests}
                    rowKey={(test) => test.paperId}
                    empty="No test has been set for this section yet."
                />
            </section>

            <section className="space-y-2">
                <h3 className="text-sm font-semibold">Students</h3>
                <Table
                    columns={studentColumns}
                    rows={data.students}
                    rowKey={(student) => student.studentId}
                    empty="Nobody is on this section's roll yet."
                />
            </section>

            <Modal
                open={open !== null}
                title={open ? `${open.name} · results so far` : "Results"}
                onClose={() => setOpen(null)}
            >
                {open && <StudentResultDetail student={open} tests={data.tests} mode={mode} />}
            </Modal>
        </div>
    );
}

/** One figure of a test's class view, or the reason it has none. */
function Cell({
    test,
    pick,
}: {
    test: OverviewTest;
    pick: "average" | "highest" | "lowest" | "passed" | "failed" | "absent";
}) {
    if (!test.published) {
        return pick === "average" ? <Badge tone="muted">Not published</Badge> : null;
    }
    return <span className="text-sm tabular-nums">{statsCells(test.stats)[pick]}</span>;
}
