import React from "react";
import { cn } from "cn";

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
    decoration?: "top" | "bottom" | "left" | "right";
    decorationColor?: string;
}

export const Card = React.forwardRef<HTMLDivElement, CardProps>(
    ({ className, decoration, decorationColor = "bg-primary", children, ...props }, ref) => {
        return (
            <div
                ref={ref}
                className={cn(
                    "relative overflow-hidden rounded-xl border border-border bg-card p-6 text-card-foreground shadow-sm",
                    className
                )}
                {...props}
            >
                {decoration && (
                    <div
                        className={cn(
                            "absolute",
                            decorationColor,
                            decoration === "top" && "top-0 left-0 right-0 h-1",
                            decoration === "bottom" && "bottom-0 left-0 right-0 h-1",
                            decoration === "left" && "top-0 bottom-0 left-0 w-1",
                            decoration === "right" && "top-0 bottom-0 right-0 w-1"
                        )}
                    />
                )}
                {children}
            </div>
        );
    }
);

Card.displayName = "Card";
