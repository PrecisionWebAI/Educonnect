"use client";

import { createContext, useContext, useState, useEffect, type ReactNode } from "react";

interface CopilotContextType {
    isOpen: boolean;
    setIsOpen: (isOpen: boolean) => void;
    toggle: () => void;
}

const CopilotContext = createContext<CopilotContextType | undefined>(undefined);

export function CopilotProvider({ children }: { children: ReactNode }) {
    const [isOpen, setIsOpen] = useState(false);

    useEffect(() => {
        const handleOpen = () => setIsOpen(true);
        window.addEventListener("open-copilot", handleOpen);
        return () => window.removeEventListener("open-copilot", handleOpen);
    }, []);

    const toggle = () => setIsOpen((prev) => !prev);

    return (
        <CopilotContext.Provider value={{ isOpen, setIsOpen, toggle }}>
            {children}
        </CopilotContext.Provider>
    );
}

export function useCopilotContext() {
    const context = useContext(CopilotContext);
    if (!context) {
        throw new Error("useCopilotContext must be used within a CopilotProvider");
    }
    return context;
}
