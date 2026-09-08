"use client";
import { useMemo, useState } from "react";
import {
    getQuestionBank,
    getPaperDraftsFull,
    getExamSchedule,
    getExamMarkings,
    getExamPaperReviews,
} from "@/services";
import { useApiQuery } from "@/lib/api/use-api-query";

export type ExamsTab =
    | "AI Paper Generator"
    | "Question Bank"
    | "My Papers"
    | "Conduct & Marking"
    | "Schedule & Seating";

export function useExams() {
    const questionsQuery = useApiQuery(["exams", "questions"], getQuestionBank);
    const papersQuery = useApiQuery(["exams", "papers"], getPaperDraftsFull);
    const scheduleQuery = useApiQuery(["exams", "schedule"], getExamSchedule);
    const markingsQuery = useApiQuery(["exams", "markings"], getExamMarkings);
    const reviewsQuery = useApiQuery(["exams", "reviews"], getExamPaperReviews);
    const questions = questionsQuery.data ?? [];
    const papers = papersQuery.data ?? [];
    const schedule = scheduleQuery.data ?? [];
    const markings = markingsQuery.data ?? [];
    const reviews = reviewsQuery.data ?? [];
    const loading =
        questionsQuery.isPending ||
        papersQuery.isPending ||
        scheduleQuery.isPending ||
        markingsQuery.isPending ||
        reviewsQuery.isPending;
    const [query, setQuery] = useState("");
    const [subject, setSubject] = useState("All");

    const subjects = useMemo(
        () => ["All", ...Array.from(new Set(questions.map((q) => q.subject)))],
        [questions],
    );
    const questionTypes = useMemo(
        () => Array.from(new Set(questions.map((q) => q.type))),
        [questions],
    );

    const filteredQuestions = useMemo(
        () =>
            questions.filter((q) => {
                const qs = query.trim().toLowerCase();
                const matchQ =
                    !qs ||
                    q.text.toLowerCase().includes(qs) ||
                    q.chapter.toLowerCase().includes(qs);
                const matchS = subject === "All" || q.subject === subject;
                return matchQ && matchS;
            }),
        [questions, query, subject],
    );

    return {
        questions,
        filteredQuestions,
        papers,
        schedule,
        markings,
        reviews,
        loading,
        query,
        setQuery,
        subject,
        setSubject,
        subjects,
        questionTypes,
    };
}
