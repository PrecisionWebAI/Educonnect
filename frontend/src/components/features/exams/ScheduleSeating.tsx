"use client";
import { Table } from "@/components/ui";
import type { ExamScheduleItem } from "@/types";

export default function ScheduleSeating({ rows }: { rows: ExamScheduleItem[] }) {
    const cols = [
        { key: "subject", header: "Subject" },
        { key: "date", header: "Date" },
        { key: "time", header: "Time" },
        { key: "rooms", header: "Rooms", render: (r: ExamScheduleItem) => r.rooms.join(", ") },
        { key: "invigilator", header: "Invigilator" },
    ];
    return <Table columns={cols} rows={rows} rowKey={(r) => r.id} empty="No exams scheduled." />;
}
