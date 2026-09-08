"use client";
import { useState } from "react";
import { getClassrooms, getLessonDetail } from "@/services";
import { useApiQuery } from "@/lib/api/use-api-query";

export type ClassroomTab = "My Classes" | "Lesson Plan";

export function useClassroom() {
    const classroomsQuery = useApiQuery(["classroom"], getClassrooms);
    const lessonQuery = useApiQuery(["classroom", "lesson"], getLessonDetail);
    const classrooms = classroomsQuery.data ?? [];
    const lesson = lessonQuery.data ?? null;
    const loading = classroomsQuery.isPending || lessonQuery.isPending;

    const totalStudents = classrooms.reduce((sum, c) => sum + c.students, 0);

    return { classrooms, lesson, loading, totalStudents };
}
