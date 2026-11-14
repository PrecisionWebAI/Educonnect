"use client";
import TeachersPage from "@/components/features/teachers/TeachersPage";

/**
 * People & Finance -> Staff (0.9).
 *
 * The same screen as Teachers, asking for the other half of the split: one
 * employee appears in exactly one of the two lists, and the rule is the role list
 * read two ways (`repository.roll_employees`). No route or codename moved.
 */
export default function Page() {
    return <TeachersPage kind="staff" />;
}
