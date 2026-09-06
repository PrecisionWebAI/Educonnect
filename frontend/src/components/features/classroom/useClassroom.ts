"use client";
import { useEffect, useState } from "react";
import { getClassrooms, getLessonDetail } from "@/services";
import type { ClassroomItem, LessonDetail } from "@/types";

export type ClassroomTab = "My Classes" | "Lesson Plan";

export function useClassroom() {
    const [classrooms, setClassrooms] = useState<ClassroomItem[]>([]);
    const [lesson, setLesson] = useState<LessonDetail | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        let alive = true;
        Promise.all([getClassrooms(), getLessonDetail()]).then(([c, l]) => {
            if (!alive) return;
            setClassrooms(c);
            setLesson(l);
            setLoading(false);
        });
        return () => {
            alive = false;
        };
    }, []);

    const totalStudents = classrooms.reduce((sum, c) => sum + c.students, 0);

    return { classrooms, lesson, loading, totalStudents };
}
