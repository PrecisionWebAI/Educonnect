"use client";

import { useState } from "react";
import Link from "next/link";
import { Button, Card, Modal, Spinner } from "@/components/ui";
import { useToast } from "@/components/ui/toast";
import { useAuth } from "@/providers/auth-context";
import { useAcademicYear } from "@/providers/academic-year-context";
import { ACADEMIC_STAFF_ROLES, hasAnyRole } from "@/lib/auth/rbac";
import { errorMessage } from "@/lib/api/client";
import { closedTone, isWeeklyOffReason } from "@/lib/attendance/view";
import { useAttendance } from "./useAttendance";
import AttendanceDatePicker from "./AttendanceDatePicker";
import MarkAttendanceTab from "./MarkAttendanceTab";
import { SummaryStrip, TrendCard } from "./AttendanceWidgets";
import AttentionList from "./AttentionList";
import LateStudentsCard from "./LateStudentsCard";
import StudentHistoryDialog from "./StudentHistoryDialog";

// The attendance register **inside one class-section**.
//
// It is one screen now: the day's register - the date, Save, the four cards and the roster
// (each child's own month figures and annual percentage on the row), with the trend, the
// attention list and last month's late students beside it.
//
// The school's calendar used to be a second tab here. It is not a classroom's business: it
// moved to **Operations & Insights → Calendar**, where one calendar serves every class. This
// screen only says *when* it needs it - a closed day keeps the register off and links there.
//
// On a closed day the register is not drawn at all - the same calendar that decides the
// percentages decides what the screen asks for.

export default function AttendancePanel({
    sectionId,
}: {
    /** The `section.id` the register is written against. */
    sectionId: string;
}) {
    const toast = useToast();
    const { user } = useAuth();
    const canMark = hasAnyRole(user?.roles, ACADEMIC_STAFF_ROLES);
    const att = useAttendance({ sectionId });
    const { current: academicYear } = useAcademicYear();
    const [error, setError] = useState<string | null>(null);
    // The day can be saved while children are still unmarked - but only after saying so
    // once, in words that name how many are left. Silently saving a half-marked register
    // is how a child ends up with no attendance at all.
    const [warnOpen, setWarnOpen] = useState(false);
    /** The child whose register history is open, if any. */
    const [history, setHistory] = useState<{ id: string; name: string } | null>(null);

    async function save() {
        setError(null);
        try {
            const result = await att.save();
            if (!result) return;
            toast.push(
                "success",
                `Saved · ${result.present}/${result.total} present on ${att.date}`,
            );
        } catch (cause) {
            const message = errorMessage(cause, "Could not save the register");
            setError(message);
            toast.push("error", message);
        }
    }

    function handleSave() {
        if (att.counts.unmarked > 0) {
            setWarnOpen(true);
            return;
        }
        void save();
    }

    if (att.loading) return <Spinner />;

    // Why the school is closed, in the words the calendar itself uses: a weekly off names
    // its weekday (or its Saturday rule), a holiday names itself. The colour comes from the
    // server's `closedKind`; the weekday-name test is only a fallback for an older payload.
    const isWeeklyOff =
        att.closedKind !== null
            ? closedTone(att.closedKind) === "off"
            : isWeeklyOffReason(att.closedReason);
    const closedTitle = att.closedReason
        ? isWeeklyOff
            ? `Weekly off · ${att.closedReason}`
            : `Holiday · ${att.closedReason}`
        : null;
    const closedNote = att.isClosed
        ? `The school is closed (${att.closedReason}). No register is taken on this day.`
        : null;

    // The side panels: the same three in both branches, so the view-only screen and the
    // marking screen cannot drift apart.
    const sidePanels = (
        <>
            <TrendCard
                bars={att.trendValues}
                range={att.trendRange}
                onRangeChange={att.setTrendRange}
            />
            <AttentionList
                rows={att.attention}
                threshold={att.threshold}
                onOpen={(row) => setHistory({ id: row.studentId, name: row.name })}
            />
            <LateStudentsCard
                data={att.late}
                loading={att.lateLoading}
                onOpen={(row) => setHistory({ id: row.studentId, name: row.name })}
            />
        </>
    );

    return (
        <div className="space-y-4">
            <div className="toolbar">
                <AttendanceDatePicker
                    date={att.date}
                    days={att.calendarDays}
                    onChange={att.setDate}
                    yearWindow={academicYear}
                />
                {closedTitle && (
                    <span className="text-muted-foreground text-xs">{closedTitle}</span>
                )}
                {canMark && (
                    <Button
                        className="ml-auto"
                        onClick={handleSave}
                        disabled={
                            att.saving ||
                            !att.isDirty ||
                            att.isClosed ||
                            att.isFuture ||
                            att.yearLock.locked
                        }
                        title={
                            att.yearLock.locked
                                ? (att.yearLock.message ?? undefined)
                                : att.isFuture
                                  ? "A future day cannot be marked - the register records what happened."
                                  : (closedNote ?? undefined)
                        }
                    >
                        {att.saving ? "Saving…" : att.hasSaved && !att.isDirty ? "Saved" : "Save"}
                    </Button>
                )}
            </div>

            {error && <p className="text-sm text-red-500">{error}</p>}

            {att.yearLock.locked && (
                <Card title="Read-only">
                    <p className="text-muted-foreground text-sm">{att.yearLock.message}</p>
                </Card>
            )}

            {att.isFuture && (
                <Card title="A future day">
                    <p className="text-muted-foreground text-sm">
                        The register records what happened, so a day that has not happened cannot be
                        marked. Pick today or an earlier date - every past day stays open to a
                        correction.
                    </p>
                </Card>
            )}

            {att.isClosed ? (
                <>
                    <Card title={closedTitle ?? "School closed"}>
                        <p className="text-muted-foreground text-sm">
                            {closedNote} The school calendar lives in{" "}
                            <Link
                                href="/dashboard/operations/calendar"
                                className="text-primary underline"
                            >
                                Operations &amp; Insights → Calendar
                            </Link>
                            .
                        </p>
                    </Card>
                    {!canMark && <div className="two-col-side">{sidePanels}</div>}
                </>
            ) : canMark ? (
                <div className="two-col">
                    <div className="two-col-main">
                        <SummaryStrip counts={att.counts} />
                        <MarkAttendanceTab
                            rows={att.rosterRows}
                            onSetMark={att.setMark}
                            onSetAll={att.setAll}
                            onReset={att.reset}
                            disabled={att.isClosed || att.isFuture || att.yearLock.locked}
                        />
                    </div>
                    <aside className="two-col-side">{sidePanels}</aside>
                </div>
            ) : (
                <div className="two-col-side">{sidePanels}</div>
            )}

            <Modal
                open={warnOpen}
                title="Some students are still unmarked"
                onClose={() => setWarnOpen(false)}
            >
                <p className="text-muted-foreground text-sm">
                    {att.counts.unmarked}{" "}
                    {att.counts.unmarked === 1 ? "student is" : "students are"} still unmarked. You
                    can go back and mark them, or save what is here - saving now leaves them
                    unmarked in the register.
                </p>
                <div className="modal-actions">
                    <Button variant="ghost" onClick={() => setWarnOpen(false)}>
                        Go back and mark
                    </Button>
                    <Button
                        onClick={() => {
                            setWarnOpen(false);
                            void save();
                        }}
                    >
                        Save anyway
                    </Button>
                </div>
            </Modal>

            <StudentHistoryDialog
                open={Boolean(history)}
                student={history}
                onClose={() => setHistory(null)}
            />
        </div>
    );
}
