"use client";

import React from "react";
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from "recharts";

interface ChartSpec {
  type: string;
  chart_type: string;
  title: string;
  x_axis: string;
  y_axis: string;
  data: any[];
}

interface ChartViewerProps {
  spec: ChartSpec;
}

const COLORS = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899"];

export default function ChartViewer({ spec }: ChartViewerProps) {
  if (!spec || !spec.data || spec.data.length === 0) return null;

  const type = (spec.chart_type || "bar").toLowerCase();

  return (
    <div className="my-4 p-4 border border-slate-200 rounded-xl bg-white shadow-sm">
      <h3 className="text-sm font-semibold text-slate-800 mb-3">{spec.title}</h3>
      <div className="w-full h-64">
        <ResponsiveContainer width="100%" height="100%">
          {type === "line" ? (
            <LineChart data={spec.data}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
              <XAxis dataKey={spec.x_axis} stroke="#64748b" fontSize={12} />
              <YAxis stroke="#64748b" fontSize={12} />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey={spec.y_axis} stroke="#2563eb" strokeWidth={2} />
            </LineChart>
          ) : type === "pie" ? (
            <PieChart>
              <Tooltip />
              <Legend />
              <Pie
                data={spec.data}
                dataKey={spec.y_axis}
                nameKey={spec.x_axis}
                cx="50%"
                cy="50%"
                outerRadius={80}
                label
              >
                {spec.data.map((_, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
            </PieChart>
          ) : (
            <BarChart data={spec.data}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
              <XAxis dataKey={spec.x_axis} stroke="#64748b" fontSize={12} />
              <YAxis stroke="#64748b" fontSize={12} />
              <Tooltip />
              <Legend />
              <Bar dataKey={spec.y_axis} fill="#3b82f6" radius={[4, 4, 0, 0]} />
            </BarChart>
          )}
        </ResponsiveContainer>
      </div>
    </div>
  );
}
