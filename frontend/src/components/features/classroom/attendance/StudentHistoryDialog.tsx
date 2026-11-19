"use client";

import { Modal } from "@/components/ui";
import { useApiQuery } from "@/lib/api/use-api-query";
import { titleCase } from "@/lib/format";
import { getStudentAttendance } from "@/services";

// One child's register history, opened from the Attention list.
//
// The list exists to start a conversation ("call the family about this child"), so the
// next thing the office needs is the dates - not another percentage. Every row is one day
// the school recorded, in the words the register uses.

const STATUS_WORDS: Record<string, string> = {
    present: "Present",
    absent: "Absent",
    late: "Late",
    half_day: "Half day",
    leave: "On leave",
};

function dayText(iso: string): string {
    const date = new Date(`${iso}T00:00:00`);
    return Number.isNaN(date.getTime())
        ? iso
        : date.toLocaleDateString("en-IN", {
              weekday: "short",
              day: "numeric",
              month: "short",
              year: "numeric",
          });
}

export default function StudentHistoryDialog({
    open,
    student,
    onClose,
}: {
    open: boolean;
    /** The child whose history is on screen; `null` while nothing is open. */
    student: { id: string; name: string } | null;
    onClose: () => void;
}) {
    const query = useApiQuery(
        ["attendance", "student", student?.id ?? "none"],
        () => getStudentAttendance(student?.id as string),
        { enabled: Boolean(student?.id) },
    );
    const rows = query.data ?? [];

    return (
        <Modal
            open={open}
            title={student ? titleCase(student.name) : "Attendance history"}
            onClose={onClose}
        >
            {query.isPending ? (
                <p className="text-muted-foreground text-sm">Loading the register…</p>
            ) : rows.length === 0 ? (
                <p className="text-muted-foreground text-sm">
                    No attendance has been recorded for this child yet.
                </p>
            ) : (
                <ul className="feed">
                    {rows.map((entry) => (
                        <li key={entry.id} className="feed-item">
                            <div className="feed-body">
                                <span className="feed-title">{dayText(entry.date)}</span>
                                <span className="feed-sub">
                                    {STATUS_WORDS[entry.status] ?? titleCase(entry.status)}
                                    {entry.subjectName ? ` · ${titleCase(entry.subjectName)}` : ""}
                                    {entry.remarks ? ` · ${entry.remarks}` : ""}
                                </span>
                            </div>
                        </li>
                    ))}
                </ul>
            )}
        </Modal>
    );
}
