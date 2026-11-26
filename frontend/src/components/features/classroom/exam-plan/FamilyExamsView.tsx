"use client";

import { useMemo, useState } from "react";
import { Badge, Button, EmptyState, Spinner, Table } from "@/components/ui";
import { errorMessage } from "@/lib/api/client";
import { classTestChip } from "@/lib/exams/classTest";
import {
    familySubtitle,
    familyTitle,
    hasSyllabusColumn,
    sortForFamily,
} from "@/lib/exams/familyExams";
import { passText } from "@/lib/exams/schoolExam";
import { dayText, figureText } from "@/lib/exams/view";
import type { ExamPaperPlan, ExamPlan } from "@/types";
import SyllabusDialog from "./SyllabusDialog";
import { useExamList } from "./useExamPlan";

// What a student or guardian reads about **upcoming** exams: each class test and each
// published date sheet - subject, date, total marks, pass line and a Syllabus button that
// is live only once the subject teacher has written one - with the teacher's note for the
// family. The server shows them only their own children's sections, and a date sheet only
// once the class teacher has published it; nothing here can show more than that.

export default function FamilyExamsView() {
    const list = useExamList();
    const [reading, setReading] = useState<ExamPaperPlan | null>(null);
    const exams = useMemo(() => sortForFamily(list.data ?? []), [list.data]);

    if (list.isPending) return <Spinner />;
    if (list.isError) {
        return (
            <p className="text-sm text-red-500" role="alert">
                {errorMessage(list.error, "Could not read the exams.")}
            </p>
        );
    }
    if (exams.length === 0) {
        return (
            <EmptyState
                icon="🗓️"
                title="Nothing is scheduled yet"
                body="Class tests and date sheets appear here as soon as your teachers publish them."
            />
        );
    }

    return (
        <div className="space-y-5">
            {exams.map((exam) => (
                <ExamCard key={exam.id} exam={exam} onSyllabus={setReading} />
            ))}
            <SyllabusDialog
                paperId={reading?.id ?? null}
                subject={reading?.subject ?? ""}
                editable={false}
                onClose={() => setReading(null)}
            />
        </div>
    );
}

function ExamCard({
    exam,
    onSyllabus,
}: {
    exam: ExamPlan;
    onSyllabus: (paper: ExamPaperPlan) => void;
}) {
    const cancelled = exam.status === "cancelled";
    const chip = exam.examType === "class_test" ? classTestChip(exam) : null;
    const sections = new Set(exam.papers.map((paper) => paper.classroomId));

    return (
        <section className="glass-tile space-y-3 rounded-2xl p-4 sm:p-5">
            <div className="flex flex-wrap items-center gap-2">
                <h3 className="text-base font-semibold tracking-tight">{familyTitle(exam)}</h3>
                {chip ? (
                    <Badge tone={chip.tone}>{chip.label}</Badge>
                ) : cancelled ? (
                    <Badge tone="red">Cancelled</Badge>
                ) : null}
                <span className="text-muted-foreground text-xs">{familySubtitle(exam)}</span>
            </div>
            {exam.familyNote && (
                <p className="bg-muted/40 rounded-xl px-3 py-2 text-sm">{exam.familyNote}</p>
            )}
            <Table
                columns={[
                    {
                        key: "subject",
                        header: "Subject",
                        render: (paper: ExamPaperPlan) => (
                            <div className="min-w-0">
                                <p className="text-sm font-medium">{paper.subject}</p>
                                {sections.size > 1 && (
                                    <p className="text-muted-foreground text-xs">{paper.section}</p>
                                )}
                            </div>
                        ),
                    },
                    {
                        key: "date",
                        header: "Date",
                        render: (paper: ExamPaperPlan) => (
                            <span className="text-sm">{dayText(paper.examDate)}</span>
                        ),
                    },
                    {
                        key: "total",
                        header: "Total marks",
                        align: "right",
                        render: (paper: ExamPaperPlan) => (
                            <span className="text-sm tabular-nums">
                                {figureText(paper.maxMarks)}
                            </span>
                        ),
                    },
                    {
                        key: "pass",
                        header: "Pass",
                        render: (paper: ExamPaperPlan) => (
                            <span className="text-sm">{passText(paper)}</span>
                        ),
                    },
                    ...(hasSyllabusColumn(exam)
                        ? [
                              {
                                  key: "syllabus",
                                  header: "Syllabus",
                                  render: (paper: ExamPaperPlan) => (
                                      <Button
                                          size="sm"
                                          variant="outline"
                                          disabled={!paper.hasSyllabus}
                                          title={
                                              paper.hasSyllabus
                                                  ? "Read the syllabus"
                                                  : "Syllabus not added yet"
                                          }
                                          onClick={() => onSyllabus(paper)}
                                      >
                                          View
                                      </Button>
                                  ),
                              },
                          ]
                        : []),
                    {
                        key: "result",
                        header: "",
                        align: "right" as const,
                        render: (paper: ExamPaperPlan) =>
                            paper.publishedAt ? <Badge tone="green">Result out</Badge> : null,
                    },
                ]}
                rows={exam.papers}
                rowKey={(paper) => paper.id}
                empty="No subject is on this list yet."
            />
        </section>
    );
}
