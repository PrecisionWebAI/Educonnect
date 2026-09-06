"use client";
import { useState } from "react";
import { PageHeader, Tabs, Spinner } from "@/components/ui";
import { useClassroom, type ClassroomTab } from "./useClassroom";
import MyClasses from "./MyClasses";
import LessonPlan from "./LessonPlan";

const TABS: ClassroomTab[] = ["My Classes", "Lesson Plan"];

export default function ClassroomPage() {
    const [tab, setTab] = useState<ClassroomTab>("My Classes");
    const c = useClassroom();

    return (
        <div>
            <PageHeader title="Classroom" subtitle="Your classes and lesson plans at a glance." />

            {c.loading ? (
                <Spinner />
            ) : (
                <>
                    <div className="stat-tiles">
                        <div className="stat-tile">
                            <b>{c.classrooms.length}</b>
                            <span>My Classes</span>
                        </div>
                        <div className="stat-tile">
                            <b>{c.totalStudents}</b>
                            <span>Total Students</span>
                        </div>
                        {c.lesson && (
                            <div className="stat-tile">
                                <b>{c.lesson.topics.length}</b>
                                <span>Lesson Topics</span>
                            </div>
                        )}
                    </div>

                    <Tabs tabs={TABS} active={tab} onChange={(t) => setTab(t as ClassroomTab)} />

                    {tab === "My Classes" && <MyClasses rows={c.classrooms} />}
                    {tab === "Lesson Plan" && c.lesson && <LessonPlan lesson={c.lesson} />}
                </>
            )}
        </div>
    );
}
