"use client";

import React from "react";
import {
    Bar,
    BarChart as RechartsBarChart,
    CartesianGrid,
    Legend,
    ResponsiveContainer,
    Tooltip,
    XAxis,
    YAxis,
} from "recharts";
import { cn } from "cn";

export interface BarChartProps extends React.HTMLAttributes<HTMLDivElement> {
    data: Record<string, unknown>[];
    index: string;
    categories: string[];
    colors?: string[];
    valueFormatter?: (value: number) => string;
    yAxisWidth?: number;
    showAnimation?: boolean;
    showTooltip?: boolean;
    showLegend?: boolean;
    showGridLines?: boolean;
    layout?: "vertical" | "horizontal";
}

const defaultColors = [
    "var(--chart-1)",
    "var(--chart-2)",
    "var(--chart-3)",
    "var(--chart-4)",
    "var(--chart-5)",
];

interface CustomTooltipProps {
    active?: boolean;
    payload?: { color: string; name: string; value: number }[];
    label?: string;
    valueFormatter?: (value: number) => string;
}

const CustomTooltip = ({ active, payload, label, valueFormatter }: CustomTooltipProps) => {
    if (active && payload && payload.length) {
        return (
            <div className="rounded-lg border border-border bg-popover px-4 py-3 shadow-md">
                <p className="text-foreground mb-2 text-sm font-medium">{label}</p>
                <div className="flex flex-col gap-1.5">
                    {payload.map((entry, index: number) => (
                        <div
                            key={index}
                            className="flex items-center justify-between gap-6 text-sm"
                        >
                            <div className="flex items-center gap-2">
                                <span
                                    className="rounded-px h-2.5 w-2.5 shrink-0"
                                    style={{ backgroundColor: entry.color }}
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

export const BarChart = React.forwardRef<HTMLDivElement, BarChartProps>(
    (
        {
            data = [],
            categories = [],
            index,
            colors = defaultColors,
            valueFormatter = (val) => val.toString(),
            yAxisWidth = 56,
            showAnimation = true,
            showTooltip = true,
            showLegend = true,
            showGridLines = true,
            layout = "horizontal",
            className,
            ...props
        },
        ref,
    ) => {
        return (
            <div ref={ref} className={cn("h-72 w-full sm:h-80", className)} {...props}>
                <ResponsiveContainer width="100%" height="100%">
                    <RechartsBarChart
                        data={data}
                        layout={layout}
                        margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
                        barCategoryGap="15%"
                        barGap={2}
                    >
                        {showGridLines && (
                            <CartesianGrid
                                strokeDasharray="none"
                                vertical={layout === "horizontal"}
                                horizontal={layout === "vertical"}
                                stroke="var(--border)"
                                strokeOpacity={0.5}
                            />
                        )}
                        <XAxis
                            type={layout === "horizontal" ? "category" : "number"}
                            dataKey={layout === "horizontal" ? index : undefined}
                            tick={{ fill: "var(--muted-foreground)" }}
                            tickLine={false}
                            axisLine={false}
                            fontSize={12}
                            dy={layout === "horizontal" ? 10 : 0}
                            hide={layout === "vertical"}
                        />
                        <YAxis
                            type={layout === "horizontal" ? "number" : "category"}
                            dataKey={layout === "vertical" ? index : undefined}
                            width={yAxisWidth}
                            tick={{ fill: "var(--muted-foreground)" }}
                            tickLine={false}
                            axisLine={false}
                            fontSize={12}
                            tickFormatter={layout === "horizontal" ? valueFormatter : undefined}
                        />
                        {showTooltip && (
                            <Tooltip
                                cursor={{ fill: "var(--muted)", opacity: 0.2 }}
                                content={<CustomTooltip valueFormatter={valueFormatter} />}
                            />
                        )}
                        {showLegend && (
                            <Legend
                                verticalAlign="top"
                                height={40}
                                iconType="circle"
                                wrapperStyle={{
                                    fontSize: "13px",
                                    color: "var(--muted-foreground)",
                                    paddingBottom: "10px",
                                }}
                            />
                        )}
                        {categories.map((category, i) => (
                            <Bar
                                key={category}
                                dataKey={category}
                                fill={colors[i % colors.length]}
                                radius={layout === "horizontal" ? [4, 4, 0, 0] : [0, 4, 4, 0]}
                                isAnimationActive={showAnimation}
                            />
                        ))}
                    </RechartsBarChart>
                </ResponsiveContainer>
            </div>
        );
    },
);

BarChart.displayName = "BarChart";
