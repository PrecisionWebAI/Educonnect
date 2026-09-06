import { api } from "@/lib/api/client";
import type { StaffMember, Teacher } from "@/types";

export interface WorkloadMatrixRow {
    staff: string;
    subject: string;
    classes: string[];
    periods: number;
    utilisation: number;
}

export interface StaffLeaveItem {
    id: number;
    staff: string;
    from: string;
    to: string;
    reason: string;
    substitute: string;
    status: "Approved" | "Pending" | "Rejected";
}

export interface StaffPerformance {
    id: number;
    staff: string;
    rating: number;
    reviews: number;
    trend: "up" | "flat" | "down";
    score: number;
}

export async function getTeachers(skip = 0, limit = 100): Promise<Teacher[]> {
    return api.get<Teacher[]>(`/teachers?skip=${skip}&limit=${limit}`);
}

export async function getStaff(skip = 0, limit = 100): Promise<StaffMember[]> {
    return api.get<StaffMember[]>(`/teachers?skip=${skip}&limit=${limit}`);
}

export async function getWorkloadMatrix(): Promise<WorkloadMatrixRow[]> {
    return api.get<WorkloadMatrixRow[]>("/teachers/workload");
}

export async function getStaffLeaves(): Promise<StaffLeaveItem[]> {
    return api.get<StaffLeaveItem[]>("/leave/staff-requests");
}

export async function getStaffPerformance(): Promise<StaffPerformance[]> {
    return api.get<StaffPerformance[]>("/teachers/performance");
}
