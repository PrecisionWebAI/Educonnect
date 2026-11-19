"use client";

import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
    Badge,
    Button,
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    Select,
    Spinner,
    Tabs,
    Textarea,
} from "@/components/ui";
import { DialogFooter } from "@/components/ui/dialog";
import { useToast } from "@/components/ui/toast";
import { usePermission } from "@/hooks/use-authorization";
import { errorMessage } from "@/lib/api/client";
import { useApiQuery } from "@/lib/api/use-api-query";
import {
    canReject,
    canSubmitWeek,
    missingRequired,
    monthLabel,
    planContent,
    planStatus,
    teachingDaysLabel,
    weekRangeLabel,
} from "@/lib/course/lesson-plan";
import {
    approveLessonPlan,
    getLessonPlanMonth,
    rejectLessonPlan,
    submitLessonPlanWeek,
} from "@/services";
import type { CourseSubject, LessonPlanContent } from "@/types";

const EMPTY: LessonPlanContent = {
    topics: "",
    learningObjectives: "",
    activities: "",
    homework: "",
    resources: "",
    assessment: "",
};

const MONTHS = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
];

function today(): { year: number; month: number } {
    const now = new Date();
    return { year: now.getFullYear(), month: now.getMonth() + 1 };
}

/**
 * The weekly Lesson Plan popup.
 *
 * Week 1-4, plus Week 5 only when the month has a 29th. Each week is submitted on its
 * own - there is no draft - and the server writes an immutable snapshot at the same time.
 * An approved week is read-only until "Request change", which submits a new version while
 * the principal's approved snapshot stays visible.
 */
export default function WeeklyLessonPlanDialog({
    subject,
    open,
    onOpenChange,
}: {
    subject: CourseSubject | null;
    open: boolean;
    onOpenChange: (open: boolean) => void;
}) {
    const queryClient = useQueryClient();
    const toast = useToast();
    const canApprove = usePermission("course.approve");
    const current = today();
    const [year, setYear] = useState(current.year);
    const [month, setMonth] = useState(current.month);
    const [activeWeek, setActiveWeek] = useState(1);
    const [content, setContent] = useState<LessonPlanContent>(EMPTY);
    const [changeMode, setChangeMode] = useState(false);
    const [saving, setSaving] = useState(false);
    const [reviewing, setReviewing] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [rejectOpen, setRejectOpen] = useState(false);
    const [rejectReason, setRejectReason] = useState("");
    const [reviewError, setReviewError] = useState<string | null>(null);

    const courseId = subject?.classroomSubjectId ?? null;
    const plan = useApiQuery(
        ["course", "lesson-plan", courseId, year, month],
        () => getLessonPlanMonth(courseId as string, year, month),
        { enabled: open && courseId !== null },
    );
    const weeks = plan.data ?? [];
    const active = weeks.find((week) => week.weekNo === activeWeek) ?? weeks[0];

    useEffect(() => {
        if (!open) return;
        const now = today();
        setYear(now.year);
        setMonth(now.month);
        setActiveWeek(1);
        setChangeMode(false);
        setError(null);
    }, [open]);

    useEffect(() => {
        if (!active) {
            setContent(EMPTY);
            return;
        }
        setContent(planContent(active));
        setChangeMode(false);
        setError(null);
    }, [activeWeek, year, month, active?.version, active?.status]);

    async function submit() {
        if (!courseId || !active) return;
        const missing = missingRequired(content);
        if (missing) {
            setError(missing);
            return;
        }

        setSaving(true);
        setError(null);
        try {
            await submitLessonPlanWeek(courseId, year, month, active.weekNo, {
                ...content,
                expectedVersion: active.expectedVersion,
                intent:
                    active.status === "Approved" && changeMode ? "change" : null,
            });
            await queryClient.invalidateQueries({ queryKey: ["course"] });
            await queryClient.invalidateQueries({ queryKey: ["classroom"] });
            toast.push(
                "success",
                changeMode ? "Change submitted for review" : "Week submitted for review",
            );
            setChangeMode(false);
        } catch (cause) {
            setError(errorMessage(cause, "Could not submit the week."));
        } finally {
            setSaving(false);
        }
    }

    async function approveActive() {
        if (!active?.planId) return;
        setReviewing(true);
        try {
            await approveLessonPlan(active.planId, active.expectedVersion);
            await queryClient.invalidateQueries({ queryKey: ["course"] });
            await queryClient.invalidateQueries({ queryKey: ["classroom"] });
            toast.push("success", "Week approved");
        } catch (cause) {
            toast.push("error", errorMessage(cause, "Could not approve the week."));
        } finally {
            setReviewing(false);
        }
    }

    async function rejectActive() {
        if (!active?.planId || !canReject(rejectReason)) {
            setReviewError("Write the reason - the teacher needs to know what to correct.");
            return;
        }
        setReviewing(true);
        setReviewError(null);
        try {
            await rejectLessonPlan(
                active.planId,
                rejectReason.trim(),
                active.expectedVersion,
            );
            await queryClient.invalidateQueries({ queryKey: ["course"] });
            await queryClient.invalidateQueries({ queryKey: ["classroom"] });
            toast.push("success", "Week rejected");
            setRejectOpen(false);
            setRejectReason("");
        } catch (cause) {
            setReviewError(errorMessage(cause, "Could not reject the week."));
        } finally {
            setReviewing(false);
        }
    }

    if (!subject) return null;

    const editable = active
        ? active.canEdit || (active.status === "Approved" && changeMode)
        : false;

    return (
        <>
            <Dialog open={open} onOpenChange={onOpenChange}>
                <DialogContent className="sm:max-w-4xl">
                <DialogHeader>
                    <DialogTitle>Lesson plan · {subject.subject}</DialogTitle>
                </DialogHeader>

                <div className="grid gap-3 sm:grid-cols-2">
                    <Select
                        label="Month"
                        value={String(month)}
                        onChange={(event) => {
                            setMonth(Number(event.target.value));
                            setActiveWeek(1);
                        }}
                    >
                        {MONTHS.map((label, index) => (
                            <option key={label} value={index + 1}>
                                {label}
                            </option>
                        ))}
                    </Select>
                    <Select
                        label="Year"
                        value={String(year)}
                        onChange={(event) => {
                            setYear(Number(event.target.value));
                            setActiveWeek(1);
                        }}
                    >
                        {[current.year - 1, current.year, current.year + 1].map((value) => (
                            <option key={value} value={value}>
                                {value}
                            </option>
                        ))}
                    </Select>
                </div>

                {plan.isPending ? (
                    <Spinner />
                ) : active ? (
                    <>
                        <Tabs
                            tabs={weeks.map((week) => `Week ${week.weekNo}`)}
                            active={`Week ${active.weekNo}`}
                            onChange={(tab) => setActiveWeek(Number(tab.replace("Week ", "")))}
                        />

                        <div className="flex flex-wrap items-center justify-between gap-2">
                            <div className="flex flex-col gap-1">
                                <span className="text-sm font-medium">
                                    {monthLabel(year, month)} · {weekRangeLabel(active)}
                                </span>
                                <span className="text-muted-foreground text-xs">
                                    {teachingDaysLabel(active)}
                                    {active.version > 0 ? ` · version ${active.version}` : ""}
                                    {active.submittedBy ? ` · ${active.submittedBy}` : ""}
                                </span>
                            </div>
                            <div className="flex flex-wrap items-center gap-2">
                                {canApprove &&
                                    active.status === "Submitted" &&
                                    active.planId && (
                                        <>
                                            <Button
                                                size="sm"
                                                onClick={approveActive}
                                                loading={reviewing}
                                            >
                                                Approve
                                            </Button>
                                            <Button
                                                size="sm"
                                                variant="danger"
                                                onClick={() => {
                                                    setRejectOpen(true);
                                                    setRejectReason("");
                                                    setReviewError(null);
                                                }}
                                            >
                                                Reject
                                            </Button>
                                        </>
                                    )}
                                <Badge tone={planStatus(active).tone}>
                                    {planStatus(active).label}
                                </Badge>
                            </div>
                        </div>

                        {active.status === "Rejected" && active.rejectionReason && (
                            <p className="rounded-md border border-red-200 bg-red-50 p-2 text-sm text-red-700">
                                <b>Rejected:</b> {active.rejectionReason}
                            </p>
                        )}

                        {active.status === "Approved" && (
                            <div className="flex flex-wrap items-center justify-between gap-2 rounded-md border p-2">
                                <span className="text-sm">
                                    This week is approved and read-only.
                                </span>
                                {active.canRequestChange && !changeMode && (
                                    <Button
                                        size="sm"
                                        variant="outline"
                                        onClick={() => setChangeMode(true)}
                                    >
                                        Request change
                                    </Button>
                                )}
                                {changeMode && (
                                    <Badge tone="amber">
                                        Change mode · new version on submit
                                    </Badge>
                                )}
                            </div>
                        )}

                        {active.approved &&
                            active.approvedVersion !== null &&
                            active.version !== active.approvedVersion && (
                                <details className="rounded-md border p-2 text-sm">
                                    <summary className="cursor-pointer font-medium">
                                        Approved version {active.approvedVersion}
                                    </summary>
                                    <div className="mt-2 grid gap-2 sm:grid-cols-2">
                                        <p>
                                            <b>Topics:</b> {active.approved.topics || "—"}
                                        </p>
                                        <p>
                                            <b>Objectives:</b>{" "}
                                            {active.approved.learningObjectives || "—"}
                                        </p>
                                        <p>
                                            <b>Activities:</b>{" "}
                                            {active.approved.activities || "—"}
                                        </p>
                                        <p>
                                            <b>Homework:</b>{" "}
                                            {active.approved.homework || "—"}
                                        </p>
                                        <p>
                                            <b>Resources:</b>{" "}
                                            {active.approved.resources || "—"}
                                        </p>
                                        <p>
                                            <b>Assessment:</b>{" "}
                                            {active.approved.assessment || "—"}
                                        </p>
                                    </div>
                                </details>
                            )}

                        <div className="grid gap-3 sm:grid-cols-2">
                            <Textarea
                                label="Topics *"
                                rows={4}
                                value={content.topics}
                                disabled={!editable}
                                onChange={(event) =>
                                    setContent({ ...content, topics: event.target.value })
                                }
                                hint="What the week covers."
                            />
                            <Textarea
                                label="Learning objectives *"
                                rows={4}
                                value={content.learningObjectives}
                                disabled={!editable}
                                onChange={(event) =>
                                    setContent({
                                        ...content,
                                        learningObjectives: event.target.value,
                                    })
                                }
                                hint="What the class should be able to do by Friday."
                            />
                            <Textarea
                                label="Activities"
                                rows={3}
                                value={content.activities}
                                disabled={!editable}
                                onChange={(event) =>
                                    setContent({ ...content, activities: event.target.value })
                                }
                            />
                            <Textarea
                                label="Homework"
                                rows={3}
                                value={content.homework}
                                disabled={!editable}
                                onChange={(event) =>
                                    setContent({ ...content, homework: event.target.value })
                                }
                            />
                            <Textarea
                                label="Resources"
                                rows={3}
                                value={content.resources}
                                disabled={!editable}
                                onChange={(event) =>
                                    setContent({ ...content, resources: event.target.value })
                                }
                            />
                            <Textarea
                                label="Assessment"
                                rows={3}
                                value={content.assessment}
                                disabled={!editable}
                                onChange={(event) =>
                                    setContent({ ...content, assessment: event.target.value })
                                }
                            />
                        </div>

                        {error && (
                            <p className="text-sm text-red-500" role="alert">
                                {error}
                            </p>
                        )}
                    </>
                ) : (
                    <p className="text-muted-foreground text-sm">
                        No week is available for this month.
                    </p>
                )}

                <DialogFooter>
                    <Button
                        variant="outline"
                        onClick={() => onOpenChange(false)}
                        disabled={saving}
                    >
                        Close
                    </Button>
                    {active &&
                        (active.canEdit ||
                            (active.status === "Approved" && changeMode)) && (
                            <Button
                                onClick={submit}
                                loading={saving}
                                disabled={!canSubmitWeek(active, content, changeMode)}
                            >
                                {active.status === "Approved"
                                    ? "Submit change"
                                    : active.status
                                      ? "Resubmit week"
                                      : "Submit week"}
                            </Button>
                        )}
                </DialogFooter>
            </DialogContent>
        </Dialog>

            <Dialog open={rejectOpen} onOpenChange={setRejectOpen}>
                <DialogContent className="sm:max-w-lg">
                    <DialogHeader>
                        <DialogTitle>Reject this week</DialogTitle>
                    </DialogHeader>
                    <Textarea
                        label="Reason *"
                        rows={4}
                        value={rejectReason}
                        onChange={(event) => setRejectReason(event.target.value)}
                        hint="The teacher sees this reason and can correct the week."
                    />
                    {reviewError && (
                        <p className="text-sm text-red-500" role="alert">
                            {reviewError}
                        </p>
                    )}
                    <DialogFooter>
                        <Button
                            variant="outline"
                            onClick={() => setRejectOpen(false)}
                            disabled={reviewing}
                        >
                            Cancel
                        </Button>
                        <Button
                            variant="danger"
                            onClick={rejectActive}
                            loading={reviewing}
                            disabled={!canReject(rejectReason)}
                        >
                            Reject week
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </>
    );
}