"use client";

import { PageHeader, Spinner } from "@/components/ui";
import { dayLabel } from "@/lib/attendance/view";
import { useHolidays } from "./useHolidays";
import SchoolCalendar from "./SchoolCalendar";

// **Operations & Insights → Calendar**: the school's own calendar, not a classroom's.
//
// The page opens with the same three stat tiles Reports & Analytics uses ("Avg data quality /
// Need attention / Critical"): **Total holidays**, **Public holidays**, **Vacation days**. Every
// number comes from the server in one read (`GET /attendance/holidays/summary`), over the
// school's **current session** - so a card can never disagree with the list beneath it.
//
// Under the cards sits the calendar itself: month grid (holiday fill, weekly-off shade, the
// legend), the weekly-off setting (weekdays + 1st-4th Saturday), the holiday list and the
// add/edit form. Clicking a closed day opens **just that date**; clicking an open day adds a
// holiday. A dated closure removed from the list is gone for good - the registers deleted
// with it are not brought back.
export default function CalendarPage() {
    const cal = useHolidays();
    const summary = cal.summary;

    // "1 Apr 2026 - 31 Mar 2027 · Session 2026-27" - the window the cards counted.
    const windowLabel = summary
        ? `${dayLabel(summary.fromDate)} – ${dayLabel(summary.toDate)}${
              summary.sessionLabel ? ` · Session ${summary.sessionLabel}` : ""
          }`
        : "";

    const figure = (value: number | undefined) =>
        cal.summaryLoading ? "…" : value === undefined ? "—" : value;

    return (
        <div>
            <PageHeader
                title="Calendar"
                subtitle="The school's holidays, weekly offs and vacation days - one calendar for every class and section."
            />

            <div className="stat-tiles">
                <div className="stat-tile">
                    <b>{figure(summary?.total)}</b>
                    <span>Total holidays</span>
                </div>
                <div className="stat-tile">
                    <b>{figure(summary?.public)}</b>
                    <span>Public holidays</span>
                </div>
                <div className="stat-tile">
                    <b>{figure(summary?.vacationDays)}</b>
                    <span>Vacation days</span>
                </div>
            </div>

            <p className="text-muted-foreground mb-4 text-xs">
                {windowLabel
                    ? `${windowLabel} · a weekly off closes a day but is not counted as a holiday.`
                    : "Counting the school's current session."}
            </p>

            {cal.summaryLoading && <Spinner />}

            <SchoolCalendar />
        </div>
    );
}
