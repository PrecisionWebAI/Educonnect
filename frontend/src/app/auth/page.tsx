import { Suspense } from "react";
import LoginPage from "@/components/features/auth/LoginPage";

export default function Page() {
    // LoginPage reads `?expired=1` via useSearchParams, which needs a Suspense
    // boundary so the rest of the route stays statically renderable.
    return (
        <Suspense fallback={null}>
            <LoginPage />
        </Suspense>
    );
}
