import { redirect } from "next/navigation";

/**
 * The calendar moved into Leave & Applications (its first tab). The old address keeps
 * working - bookmarks and the link in a class's Attendance tab land on the new place.
 */
export default function Page() {
    redirect("/dashboard/leave?tab=calendar");
}
