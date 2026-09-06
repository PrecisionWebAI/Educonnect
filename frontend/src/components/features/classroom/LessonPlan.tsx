"use client";
import { Card, Badge } from "@/components/ui";
import type { LessonDetail } from "@/types";

export default function LessonPlan({ lesson }: { lesson: LessonDetail }) {
    return (
        <div style={{ display: "grid", gap: "1rem" }}>
            <Card title={lesson.title} action={<Badge tone="accent">{lesson.duration}</Badge>}>
                <div
                    style={{
                        display: "grid",
                        gap: "0.4rem",
                        color: "var(--muted)",
                        fontSize: "0.88rem",
                        marginBottom: "0.8rem",
                    }}
                >
                    <div>
                        <b style={{ color: "var(--text)" }}>{lesson.subject}</b> ·{" "}
                        {lesson.className}
                    </div>
                </div>
                <h4 style={{ fontSize: "0.9rem", marginBottom: "0.4rem" }}>Topics</h4>
                <ul
                    style={{
                        paddingLeft: "1.2rem",
                        display: "grid",
                        gap: "0.25rem",
                        fontSize: "0.88rem",
                    }}
                >
                    {lesson.topics.map((t) => (
                        <li key={t}>{t}</li>
                    ))}
                </ul>
            </Card>

            <Card title="Resources">
                <div style={{ display: "grid", gap: "0.5rem" }}>
                    {lesson.resources.map((r) => (
                        <div
                            key={r.id}
                            style={{
                                display: "flex",
                                justifyContent: "space-between",
                                alignItems: "center",
                                fontSize: "0.88rem",
                            }}
                        >
                            <span>{r.title}</span>
                            <Badge
                                tone={
                                    r.type === "Video"
                                        ? "violet"
                                        : r.type === "PDF"
                                          ? "teal"
                                          : "amber"
                                }
                            >
                                {r.type}
                            </Badge>
                        </div>
                    ))}
                </div>
            </Card>

            <Card title="Homework">
                <p style={{ fontSize: "0.88rem", color: "var(--muted)" }}>{lesson.homework}</p>
            </Card>
        </div>
    );
}
