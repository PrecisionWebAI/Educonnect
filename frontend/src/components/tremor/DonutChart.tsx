"use client";

import React from "react";
import {
    Pie,
    PieChart as RechartsPieChart,
    Cell,
    Legend,
    ResponsiveContainer,
    Tooltip,
} from "recharts";
import { cn } from "cn";

export interface DonutChartProps extends React.HTMLAttributes<HTMLDivElement> {
    data: Record<string, unknown>[];
    category: string;
    index: string;
    colors?: string[];
    valueFormatter?: (value: number) => string;
    showAnimation?: boolean;
    showTooltip?: boolean;
    showLegend?: boolean;
    variant?: "donut" | "pie";
}

const defaultColors = [
    "var(--chart-1)",
    "var(--chart-2)",
    "var(--chart-3)",
    "var(--chart-4)",
    "var(--chart-5)",
];

interface TooltipPayload {
    name: string;
    value: number;
    payload: {
        fill: string;
    };
}

interface CustomTooltipProps {
    active?: boolean;
    payload?: TooltipPayload[];
    valueFormatter?: (value: number) => string;
}

const CustomTooltip = ({ active, payload, valueFormatter }: CustomTooltipProps) => {
    if (active && payload && payload.length) {
        return (
            <div className="border-border bg-popover rounded-lg border px-4 py-3 shadow-md">
                <div className="flex flex-col gap-1.5">
                    {payload.map((entry: TooltipPayload, index: number) => (
                        <div
                            key={index}
                            className="flex items-center justify-between gap-6 text-sm"
                        >
                            <div className="flex items-center gap-2">
                                <span
                                    className="h-2.5 w-2.5 shrink-0 rounded-xs"
                                    style={{ backgroundColor: entry.payload.fill }}
                                />
                                <span className="text-muted-foreground">{entry.name}</span>
                            </div>
                            <span className="text-foreground font-medium">
                                {valueFormatter ? valueFormatter(entry.value) : entry.value}
                            </span>
                        </div>
                    ))}
                </div>
            </div>
        );
    }
    return null;
};

export const DonutChart = React.forwardRef<HTMLDivElement, DonutChartProps>(
    (
        {
            data = [],
            category,
            index,
            colors = defaultColors,
            valueFormatter = (val) => val.toString(),
            showAnimation = true,
            showTooltip = true,
            showLegend = true,
            variant = "donut",
            className,
            ...props
        },
        ref,
    ) => {
        const isDonut = variant === "donut";

        return (
            <div ref={ref} className={cn("h-72 w-full sm:h-80", className)} {...props}>
                <ResponsiveContainer width="100%" height="100%">
                    <RechartsPieChart margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
                        <Pie
                            data={data}
                            cx="50%"
                            cy="50%"
                            innerRadius={isDonut ? "65%" : "0%"}
                            outerRadius="90%"
                            paddingAngle={isDonut ? 2 : 0}
                            dataKey={category}
                            nameKey={index}
                            isAnimationActive={showAnimation}
                            stroke="var(--background)"
                            strokeWidth={2}
                        >
                            {data.map((_, i) => (
                                <Cell key={`cell-${i}`} fill={colors[i % colors.length]} />
                            ))}
                        </Pie>
                        {showTooltip && (
                            <Tooltip content={<CustomTooltip valueFormatter={valueFormatter} />} />
                        )}
                        {showLegend && (
                            <Legend
                                verticalAlign="bottom"
                                height={40}
                                iconType="circle"
                                wrapperStyle={{
                                    fontSize: "13px",
                                    color: "var(--muted-foreground)",
                                    paddingTop: "10px",
                                }}
                            />
                        )}
                    </RechartsPieChart>
                </ResponsiveContainer>
            </div>
        );
    },
);

DonutChart.displayName = "DonutChart";
