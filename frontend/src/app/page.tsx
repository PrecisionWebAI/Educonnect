import { Suspense } from "react";
import LoginPage from "@/components/features/auth/LoginPage";

export default function Page() {
    return (
        <Suspense fallback={null}>
            <LoginPage />
        </Suspense>
    );
}
