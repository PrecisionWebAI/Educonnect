import type { LeaveApplicationItem } from "@/types";
const delay = (ms = 250) => new Promise((res) => setTimeout(res, ms));
export async function getLeaveApplications(): Promise<LeaveApplicationItem[]> {
    await delay();
    return [
        {
            id: 1,
            type: "Medical",
            student: "Aarav Mehta",
            className: "10-A",
            from: "2026/09/05",
            to: "2026/09/06",
            days: 2,
            reason: "Fever",
            status: "Pending",
            submittedAt: "2h ago",
        },
        {
            id: 2,
            type: "Personal",
            student: "Diya Sharma",
            className: "10-A",
            from: "2026/09/10",
            to: "2026/09/10",
            days: 1,
            reason: "Family function",
            status: "Approved",
            submittedAt: "Yesterday",
        },
    ];
}
