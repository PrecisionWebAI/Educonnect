import { redirect } from "next/navigation";

// Exams & AI Papers now live **inside the Classroom**: open a class-section and
// its "Exams & AI Papers" tab builds a paper for that class-section, and every
// draft/generated paper is private to the person who created it.
//
// This route only exists so an old bookmark does not 404.
export default function Page() {
    redirect("/dashboard/classroom");
}
