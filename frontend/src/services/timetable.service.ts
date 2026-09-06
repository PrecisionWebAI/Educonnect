import { api } from "@/lib/api/client";
import type { TimetableSlot } from "@/types";

export async function getTimetable(): Promise<TimetableSlot[]> {
    return api.get<TimetableSlot[]>("/timetable");
}
