"use client";

import { Badge, Table } from "@/components/ui";
import {
    entryFor,
    entryText,
    passFailText,
    percentGradeText,
    resultBadge,
    showsMarks,
    testLabel,
    type DisplayMode,
} from "@/lib/exams/results";
import { figureText } from "@/lib/exams/view";
import type { OverviewSubject, OverviewStudent, OverviewTest } from "@/types";

// One child's results, in full: the overall line, each subject so far, and each test.
//
// The family sees this for its own child; the class teacher opens it from the class table
// (in a pop-up). Both read the same words, so a teacher and a parent never see two
// different answers. "Absent" is shown as Absent and is left out of every percentage - the
// server already did that; this only says so.

export default function StudentResultDetail({
    student,
    tests,
    mode,
}: {
    student: OverviewStudent;
    /** Every test of the overview; only the ones this child has a result for are drawn. */
    tests: OverviewTest[];
    mode: DisplayMode;
}) {
    const sat = tests.filter((test) => entryFor(student, test));
    const overall = student.overall;

    return (
        <div className="space-y-4">
            <div className="glass-tile flex flex-wrap items-center justify-between gap-3 rounded-2xl p-4">
                <div>
                    <p className="text-muted-foreground text-xs">Overall so far</p>
                    <p className="text-2xl font-semibold tracking-tight">
                        {percentGradeText(overall.percentage, overall.grade, mode)}
                    </p>
                    {showsMarks(mode) && overall.percentage !== null && (
                        <p className="text-muted-foreground text-xs">
                            {figureText(overall.obtained)} of {figureText(overall.total)} marks
                        </p>
                    )}
                </div>
                <div className="text-right text-sm">
                    <p>{passFailText(overall.testsPassed, overall.testsFailed)}</p>
                    <p className="text-muted-foreground text-xs">
                        {overall.testsCounted} {overall.testsCounted === 1 ? "test" : "tests"}{" "}
                        counted
                        {overall.testsAbsent > 0 ? ` · ${overall.testsAbsent} absent` : ""}
                    </p>
                </div>
            </div>

            <div className="space-y-2">
                <h4 className="text-sm font-semibold">Subject-wise so far</h4>
                <Table
                    columns={[
                        {
                            key: "subject",
                            header: "Subject",
                            render: (line: OverviewSubject) => (
                                <span className="text-sm font-medium">{line.subject}</span>
                            ),
                        },
                        ...(showsMarks(mode)
                            ? [
                                  {
                                      key: "marks",
                                      header: "Marks",
                                      align: "right" as const,
                                      render: (line: OverviewSubject) => (
                                          <span className="text-sm tabular-nums">
                                              {line.testsCounted === 0
                                                  ? "—"
                                                  : `${figureText(line.obtained)}/${figureText(line.total)}`}
                                          </span>
                                      ),
                                  },
                              ]
                            : []),
                        {
                            key: "result",
                            header: mode === "grades" ? "Grade" : "Percentage",
                            render: (line: OverviewSubject) => (
                                <span className="text-sm">
                                    {percentGradeText(line.percentage, line.grade, mode)}
                                </span>
                            ),
                        },
                        {
                            key: "tests",
                            header: "Tests",
                            align: "right",
                            render: (line: OverviewSubject) => (
                                <span className="text-muted-foreground text-xs">
                                    {line.testsCounted}
                                    {line.testsAbsent > 0 ? ` · ${line.testsAbsent} absent` : ""}
                                </span>
                            ),
                        },
                    ]}
                    rows={student.subjects}
                    rowKey={(line) => line.subject}
                    empty="No test has been marked yet."
                />
            </div>

            <div className="space-y-2">
                <h4 className="text-sm font-semibold">Test by test</h4>
                <Table
                    columns={[
                        {
                            key: "test",
                            header: "Test",
                            render: (test: OverviewTest) => (
                                <div className="min-w-0">
                                    <p className="truncate text-sm font-medium">
                                        {testLabel(test)}
                                    </p>
                                    <p className="text-muted-foreground truncate text-xs">
                                        {test.examName}
                                    </p>
                                </div>
                            ),
                        },
                        {
                            key: "result",
                            header: "Result",
                            render: (test: OverviewTest) => (
                                <span className="text-sm tabular-nums">
                                    {entryText(entryFor(student, test), test.totalMarks, mode)}
                                </span>
                            ),
                        },
                        {
                            key: "badge",
                            header: "",
                            align: "right",
                            render: (test: OverviewTest) => {
                                const badge = resultBadge(entryFor(student, test));
                                return badge ? (
                                    <Badge tone={badge.tone}>{badge.label}</Badge>
                                ) : null;
                            },
                        },
                    ]}
                    rows={sat}
                    rowKey={(test) => test.paperId}
                    empty="No test has been published yet."
                />
            </div>
        </div>
    );
}
