import { api } from "@/lib/api/client";
import type { TimetableSlot } from "@/types";

/** The school-wide week (names only) — the personal timetable view reads this. */
export async function getTimetable(): Promise<TimetableSlot[]> {
    return api.get<TimetableSlot[]>("/timetable");
}

/**
 * One period of one class-section's week, with the ids an editor needs.
 *
 * The backend row names its section (`section_id`), subject and teacher by id;
 * the class-section grid already knows their names, so it renders them itself.
 */
export interface TimetablePeriodItem {
    id: string;
    sectionId: string;
    subjectId: string;
    teacherId: string;
    /** `monday` … `saturday` (the backend's enum values). */
    dayOfWeek: string;
    /** `HH:MM`. */
    startTime: string;
    endTime: string;
    room: string | null;
}

/** What the grid sends to add a period or move one. */
export interface TimetablePeriodInput {
    sectionId: string;
    subjectId: string;
    teacherId: string;
    dayOfWeek: string;
    startTime: string;
    endTime: string;
    room?: string | null;
}

/** The API's shape for a period (snake_case, `HH:MM:SS` times). */
interface BackendPeriod {
    id: string;
    section_id: string;
    subject_id: string;
    teacher_id: string;
    day_of_week: string;
    start_time: string;
    end_time: string;
    room: string | null;
}

/** `08:00:00` → `08:00`. */
function hhmm(value: string): string {
    return value.slice(0, 5);
}

function toItem(period: BackendPeriod): TimetablePeriodItem {
    return {
        id: period.id,
        sectionId: period.section_id,
        subjectId: period.subject_id,
        teacherId: period.teacher_id,
        dayOfWeek: period.day_of_week,
        startTime: hhmm(period.start_time),
        endTime: hhmm(period.end_time),
        room: period.room,
    };
}

function toBody(input: TimetablePeriodInput) {
    return {
        section_id: input.sectionId,
        subject_id: input.subjectId,
        teacher_id: input.teacherId,
        day_of_week: input.dayOfWeek,
        start_time: input.startTime,
        end_time: input.endTime,
        room: input.room ?? null,
    };
}

/** One class-section's week (`GET /timetable/class/{classId}?section_id=`). */
export async function getSectionTimetable(
    classId: string,
    sectionId: string,
): Promise<TimetablePeriodItem[]> {
    const rows = await api.get<BackendPeriod[]>(
        `/timetable/class/${classId}?section_id=${sectionId}`,
    );
    return rows.map(toItem);
}

/** Add a period to a class-section's week. */
export async function createTimetablePeriod(
    input: TimetablePeriodInput,
): Promise<TimetablePeriodItem> {
    return toItem(await api.post<BackendPeriod>("/timetable", toBody(input)));
}

/** Move a period (another subject, teacher, room or slot). */
export async function updateTimetablePeriod(
    periodId: string,
    input: TimetablePeriodInput,
): Promise<TimetablePeriodItem> {
    return toItem(await api.patch<BackendPeriod>(`/timetable/${periodId}`, toBody(input)));
}

/** Clear a slot from the week. */
export async function deleteTimetablePeriod(periodId: string): Promise<void> {
    await api.delete<void>(`/timetable/${periodId}`);
}
