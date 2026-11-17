"use client";

import { ArrowLeft } from "lucide-react";
import { Badge, Spinner, Table } from "@/components/ui";
import { useApiQuery } from "@/lib/api/use-api-query";
import {
    dayText,
    figureText,
    gradeTone,
    markCellText,
    passText,
    percentText,
    rankText,
    unpublishedSubjects,
} from "@/lib/exams/view";
import { getExamResults } from "@/services";
import type { ExamResultPaper, ExamResultRow } from "@/types";

// Results for one exam (Phase 8).
//
// What a report card shows, and who may see it, both come from the server:
// `rows` is already narrowed to the caller's own children for a student or a
// guardian (`ownOnly`), and `rank` is `null` whenever the school has ranks off,
// so this screen never invents a position. The grade is the school's own ladder
// (`grade_scale`), and an absence prints as **Absent** - never as a zero that
// would quietly drag an average down.
//
// The papers table is the teachers' view: average, highest, lowest and how many
// marks are in, so a class can see where a subject went wrong before the report
// cards are printed.

const RANK_VIEWS = ["section", "class", "school"];

export default function ResultsView({ examId, onBack }: { examId: string; onBack: () => void }) {
    const query = useApiQuery(["exams", "plan", "results", examId], () => getExamResults(examId));
    if (query.isPending) return <Spinner />;

    const results = query.data;
    if (!results) {
        return (
            <div className="space-y-3">
                <BackLink onBack={onBack} />
                <p className="text-muted-foreground text-sm">These results could not be read.</p>
            </div>
        );
    }

    const ranksOn = RANK_VIEWS.includes(results.rankDisplay);
    const pendingSubjects = unpublishedSubjects(results);
    const topper = [...results.rows]
        .filter((row) => row.rank !== null)
        .sort((a, b) => (a.rank ?? 0) - (b.rank ?? 0))[0];

    return (
        <div className="space-y-4">
            <BackLink onBack={onBack} />

            <div className="glass-tile space-y-1 rounded-2xl p-4 sm:p-5">
                <div className="flex flex-wrap items-center gap-2">
                    <h3 className="text-base font-semibold tracking-tight">{results.name}</h3>
                    <Badge tone="accent">
                        {ranksOn ? `Ranked by ${results.rankDisplay}` : "No ranks"}
                    </Badge>
                    <Badge tone="muted">
                        {results.gradeScale === "grade" ? "Grade scale" : "Percentage"}
                    </Badge>
                    {results.ownOnly && <Badge tone="teal">Your own child</Badge>}
                </div>
                <p className="text-muted-foreground text-sm">
                    {results.rows.length} {results.rows.length === 1 ? "student" : "students"} ·{" "}
                    {results.papers.length} {results.papers.length === 1 ? "paper" : "papers"}
                    {topper?.rank === 1 ? ` · topper: ${topper.name}` : ""}
                </p>
                {pendingSubjects.length > 0 && (
                    <p className="text-sm text-amber-600" role="status">
                        Not published yet: {pendingSubjects.join(", ")}.
                    </p>
                )}
            </div>

            <div className="space-y-2">
                <h4 className="text-sm font-semibold">By paper</h4>
                <Table
                    columns={[
                        {
                            key: "subject",
                            header: "Subject",
                            render: (paper: ExamResultPaper) => (
                                <div>
                                    <p className="font-medium">{paper.subject}</p>
                                    <p className="text-muted-foreground text-xs">
                                        {paper.examDate ? dayText(paper.examDate) : "Date not set"}{" "}
                                        · out of {figureText(paper.maxMarks)}
                                    </p>
                                </div>
                            ),
                        },
                        {
                            key: "average",
                            header: "Average",
                            align: "right",
                            render: (paper: ExamResultPaper) => (
                                <span className="text-sm tabular-nums">
                                    {figureText(paper.average)}
                                </span>
                            ),
                        },
                        {
                            key: "highest",
                            header: "Highest",
                            align: "right",
                            render: (paper: ExamResultPaper) => (
                                <span className="text-sm tabular-nums">
                                    {figureText(paper.highest)}
                                </span>
                            ),
                        },
                        {
                            key: "lowest",
                            header: "Lowest",
                            align: "right",
                            render: (paper: ExamResultPaper) => (
                                <span className="text-sm tabular-nums">
                                    {figureText(paper.lowest)}
                                </span>
                            ),
                        },
                        {
                            key: "entered",
                            header: "Marks in",
                            align: "right",
                            render: (paper: ExamResultPaper) => (
                                <span className="text-sm tabular-nums">
                                    {paper.entered}
                                    {paper.absent > 0 ? ` · ${paper.absent} absent` : ""}
                                </span>
                            ),
                        },
                        {
                            key: "state",
                            header: "State",
                            render: (paper: ExamResultPaper) => (
                                <Badge tone={paper.published ? "green" : "muted"}>
                                    {paper.published ? "Published" : "Draft"}
                                </Badge>
                            ),
                        },
                    ]}
                    rows={results.papers}
                    rowKey={(paper) => paper.paperId}
                    empty="No paper in this exam yet."
                />
            </div>

            <div className="space-y-2">
                <h4 className="text-sm font-semibold">Report card</h4>
                <Table
                    columns={[
                        {
                            key: "name",
                            header: "Student",
                            render: (row: ExamResultRow) => (
                                <div>
                                    <p className="font-medium">{row.name}</p>
                                    <p className="text-muted-foreground text-xs">
                                        {row.admissionNumber ?? "—"}
                                        {row.className && row.section
                                            ? ` · ${row.className}-${row.section}`
                                            : ""}
                                    </p>
                                </div>
                            ),
                        },
                        ...results.papers.map((paper) => ({
                            key: `paper-${paper.paperId}`,
                            header: paper.subject,
                            align: "right" as const,
                            render: (row: ExamResultRow) => {
                                const mark = row.marks.find(
                                    (item) => item.paperId === paper.paperId,
                                );
                                if (!mark) return <span className="text-muted-foreground">—</span>;
                                return (
                                    <span
                                        className={mark.absent ? "text-amber-600" : "tabular-nums"}
                                    >
                                        {markCellText(mark)}
                                    </span>
                                );
                            },
                        })),
                        {
                            key: "total",
                            header: "Total",
                            align: "right",
                            render: (row: ExamResultRow) => (
                                <span className="text-sm tabular-nums">
                                    {figureText(row.total)}/{figureText(row.outOf)}
                                </span>
                            ),
                        },
                        {
                            key: "percent",
                            header: "%",
                            align: "right",
                            render: (row: ExamResultRow) => (
                                <span className="text-sm tabular-nums">
                                    {percentText(row.percent)}
                                </span>
                            ),
                        },
                        {
                            key: "grade",
                            header: "Grade",
                            render: (row: ExamResultRow) =>
                                row.grade ? (
                                    <Badge tone={gradeTone(row.grade)}>{row.grade}</Badge>
                                ) : (
                                    <span className="text-muted-foreground">—</span>
                                ),
                        },
                        {
                            key: "rank",
                            header: "Rank",
                            align: "right",
                            render: (row: ExamResultRow) => (
                                <span className="text-sm tabular-nums">
                                    {rankText(row.rank, ranksOn)}
                                </span>
                            ),
                        },
                        {
                            key: "pass",
                            header: "Pass",
                            render: (row: ExamResultRow) => {
                                const text = passText(row);
                                return (
                                    <Badge
                                        tone={
                                            row.passedAll === null
                                                ? "muted"
                                                : row.passedAll
                                                  ? "green"
                                                  : "red"
                                        }
                                    >
                                        {text}
                                    </Badge>
                                );
                            },
                        },
                    ]}
                    rows={results.rows}
                    rowKey={(row) => row.studentId}
                    empty="No marks have been entered for this exam yet."
                />
            </div>
        </div>
    );
}

/** The back link every drill-down screen in this tab shares. */
function BackLink({ onBack }: { onBack: () => void }) {
    return (
        <button type="button" onClick={onBack} className="classroom-back-link">
            <ArrowLeft aria-hidden="true" className="size-4" />
            Back to the exams
        </button>
    );
}
