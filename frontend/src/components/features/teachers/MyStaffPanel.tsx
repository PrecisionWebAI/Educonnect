"use client";
import { Badge, Card, Spinner } from "@/components/ui";
import { errorMessage } from "@/lib/api/client";
import { useMyStaff } from "./useMyStaff";

/**
 * What a teacher sees instead of the school's directory.
 *
 * Phase 9's rule: a teacher-only account gets **"my" reads**, not the roster. The
 * three figures are the ones a person actually needs - what the office has recorded
 * about their month, how heavy their week is, and who they are on file as - and each
 * is read from the same tables the office screen reads, scoped to the caller.
 *
 * A month repeat is deliberately not offered: this is "how is it going", not history.
 */
export default function MyStaffPanel() {
    const me = useMyStaff();

    if (me.loading) return <Spinner />;

    if (me.error !== null) {
        return (
            <p className="text-sm" style={{ color: "var(--danger, #b42318)" }}>
                {errorMessage(me.error, "Your staff record could not be loaded.")}
            </p>
        );
    }

    const month = me.month;

    return (
        <div className="grid gap-3">
            <Card>
                <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                        <b>{me.row?.name ?? "My record"}</b>
                        <div className="text-muted-foreground text-xs">
                            {me.row?.staffCode ?? ""}
                            {me.row?.department ? ` · ${me.row.department}` : ""}
                            {me.row?.subject ? ` · ${me.row.subject}` : ""}
                        </div>
                    </div>
                    <Badge tone="teal">{me.row?.status ?? "Active"}</Badge>
                </div>
            </Card>

            <div className="stat-tiles">
                <div className="stat-tile">
                    <b>{me.week?.periods ?? "—"}</b>
                    <span>My periods / week</span>
                </div>
                <div className="stat-tile">
                    <b>{me.week?.duties ?? "—"}</b>
                    <span>My duties</span>
                </div>
                <div className="stat-tile">
                    <b>{month ? `${month.percent}%` : "—"}</b>
                    <span>Attended this month</span>
                </div>
                <div className="stat-tile">
                    <b>{month?.marked ?? "—"}</b>
                    <span>Days marked</span>
                </div>
            </div>

            {month !== null && (
                <Card>
                    <div className="flex flex-wrap gap-2">
                        <Badge tone="green">Present {month.present}</Badge>
                        <Badge tone="amber">Half Day {month.halfDay}</Badge>
                        <Badge tone="red">Absent {month.absent}</Badge>
                        <Badge tone="teal">On Leave {month.onLeave}</Badge>
                        <Badge tone="muted">Not Marked {month.notMarked}</Badge>
                    </div>
                    <p className="text-muted-foreground mt-2 text-xs">
                        {month.monthLabel}: {month.percent}% is a share of the {month.marked}{" "}
                        {month.marked === 1 ? "day" : "days"} the office has marked - not of the
                        month. Approved leave is counted apart from both attendance and absence. If
                        something looks wrong, the office amends the register; this screen only
                        reads it.
                    </p>
                </Card>
            )}
        </div>
    );
}
