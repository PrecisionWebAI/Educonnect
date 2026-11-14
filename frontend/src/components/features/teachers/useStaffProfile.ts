"use client";
import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
    addCertification,
    addExperience,
    addQualification,
    deleteCertification,
    deleteExperience,
    deleteQualification,
    deleteStaffDocument,
    fetchStaffDocument,
    getStaffProfile,
    saveEmployment,
    uploadStaffDocument,
    verifyStaffDocument,
    type CertificationInput,
    type EmploymentInput,
    type ExperienceInput,
    type QualificationInput,
} from "@/services";
import { useApiQuery } from "@/lib/api/use-api-query";

/**
 * The profile drawer's data.
 *
 * One query for the whole drawer (`["staff", "profile", id]`): the person, their
 * post and the four lists arrive together, so the tabs cannot contradict each
 * other while they load.
 *
 * Every write goes through `run`, which does three things in one place: it marks
 * which button is busy, it keeps the server's refusal (a `409` duplicate degree,
 * a `403` outside the HOD's department) as the drawer's message instead of
 * throwing it away, and after a success it invalidates **`["staff", …]`** - the
 * profile, the directory row and the tiles all read that prefix, so a saved
 * qualification shows up everywhere it is counted.
 */
export function useStaffProfile(teacherId: string | null) {
    const queryClient = useQueryClient();
    /** Which action is in flight, so its button can show a spinner. */
    const [busy, setBusy] = useState<string | null>(null);
    /** The last refusal, kept for the drawer to print (never a silent no-op). */
    const [error, setError] = useState<unknown>(null);
    /**
     * Whether the drawer asked for the **unmasked** Aadhaar / PAN / bank numbers.
     *
     * It is part of the query key, so flipping it refetches once - and only when
     * somebody presses "Show full". Every other open of the drawer reads the
     * masked values, which is what "masked by default" has to mean.
     */
    const [revealed, setRevealed] = useState(false);

    const query = useApiQuery(
        ["staff", "profile", teacherId, revealed],
        () => getStaffProfile(teacherId as string, revealed),
        { enabled: Boolean(teacherId) },
    );

    async function run(action: string, work: () => Promise<unknown>): Promise<boolean> {
        setBusy(action);
        setError(null);
        try {
            await work();
            await queryClient.invalidateQueries({ queryKey: ["staff"] });
            return true;
        } catch (problem) {
            setError(problem);
            return false;
        } finally {
            setBusy(null);
        }
    }

    return {
        profile: query.data ?? null,
        loading: query.isPending,
        loadError: query.error ?? null,
        error,
        setError,
        busy,
        canEdit: true,
        /** Ask for the unmasked Aadhaar / PAN / bank; the server audits the reveal. */
        revealed,
        showKyc: () => setRevealed(true),
        saveEmployment: (input: EmploymentInput) =>
            run("employment", () => saveEmployment(teacherId as string, input)),
        addQualification: (input: QualificationInput) =>
            run("qualification", () => addQualification(teacherId as string, input)),
        removeQualification: (rowId: string) =>
            run("qualification", () => deleteQualification(teacherId as string, rowId)),
        addExperience: (input: ExperienceInput) =>
            run("experience", () => addExperience(teacherId as string, input)),
        removeExperience: (rowId: string) =>
            run("experience", () => deleteExperience(teacherId as string, rowId)),
        addCertification: (input: CertificationInput) =>
            run("certification", () => addCertification(teacherId as string, input)),
        removeCertification: (rowId: string) =>
            run("certification", () => deleteCertification(teacherId as string, rowId)),
        uploadDocument: (input: { file: File; docType: string; title?: string }) =>
            run("document", () => uploadStaffDocument(teacherId as string, input)),
        verifyDocument: (rowId: string, verified = true) =>
            run("document", () => verifyStaffDocument(teacherId as string, rowId, verified)),
        removeDocument: (rowId: string) =>
            run("document", () => deleteStaffDocument(teacherId as string, rowId)),
        /**
         * Download one document.
         *
         * The API answers with bytes, so this is the one action that does not go
         * through `run`: it has to hand the browser a file (the row's own name)
         * rather than invalidate a query. A refusal is still printed.
         */
        downloadDocument: async (rowId: string, fileName: string) => {
            setBusy(`download-${rowId}`);
            setError(null);
            try {
                const blob = await fetchStaffDocument(teacherId as string, rowId);
                const url = URL.createObjectURL(blob);
                const link = window.document.createElement("a");
                link.href = url;
                link.download = fileName;
                window.document.body.appendChild(link);
                link.click();
                link.remove();
                URL.revokeObjectURL(url);
                return true;
            } catch (problem) {
                setError(problem);
                return false;
            } finally {
                setBusy(null);
            }
        },
    };
}
