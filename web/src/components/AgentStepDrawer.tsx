"use client";

import React, { useState } from "react";
import { ChevronDown, ChevronUp, ShieldCheck, ShieldAlert, Cpu, Clock, DollarSign } from "lucide-react";

interface Step {
  type: string;
  step?: number;
  tool?: string;
  arguments?: any;
  result?: any;
  rejection?: string;
  thought?: string;
  answer?: string;
  metrics?: {
    total_steps: number;
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
    estimated_cost_usd: number;
    guard_retries: number;
  };
}

interface AgentStepDrawerProps {
  steps: Step[];
  metrics?: any;
}

export default function AgentStepDrawer({ steps, metrics }: AgentStepDrawerProps) {
  const [isOpen, setIsOpen] = useState(false);

  if (!steps || steps.length === 0) return null;

  return (
    <div className="mt-3 border border-slate-200 rounded-lg bg-slate-50 overflow-hidden text-sm">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-4 py-2 flex items-center justify-between bg-slate-100 hover:bg-slate-200 transition-colors font-medium text-slate-700"
      >
        <div className="flex items-center gap-2">
          <Cpu className="w-4 h-4 text-blue-600" />
          <span>Show Agent Reasoning & Steps ({steps.length} events)</span>
          {metrics && (
            <span className="text-xs text-slate-500 font-normal ml-2">
              • {metrics.total_tokens || 0} tokens (${(metrics.estimated_cost_usd || 0).toFixed(5)})
            </span>
          )}
        </div>
        {isOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
      </button>

      {isOpen && (
        <div className="p-4 space-y-3 divide-y divide-slate-200">
          {/* Metrics summary banner */}
          {metrics && (
            <div className="grid grid-cols-4 gap-2 pb-2 text-xs text-slate-600 font-mono">
              <div className="flex items-center gap-1">
                <Clock className="w-3.5 h-3.5 text-slate-400" />
                <span>Steps: {metrics.total_steps}</span>
              </div>
              <div className="flex items-center gap-1">
                <Cpu className="w-3.5 h-3.5 text-slate-400" />
                <span>Tokens: {metrics.total_tokens}</span>
              </div>
              <div className="flex items-center gap-1">
                <DollarSign className="w-3.5 h-3.5 text-emerald-600" />
                <span>Cost: ${(metrics.estimated_cost_usd || 0).toFixed(6)}</span>
              </div>
              <div className="flex items-center gap-1">
                <ShieldCheck className="w-3.5 h-3.5 text-blue-500" />
                <span>Retries: {metrics.guard_retries || 0}</span>
              </div>
            </div>
          )}

          {/* Individual step logs */}
          <div className="space-y-3 pt-2">
            {steps.map((st, i) => {
              if (st.type === "tool_call") {
                return (
                  <div key={i} className="bg-white p-3 rounded border border-slate-200">
                    <div className="flex items-center justify-between text-xs text-slate-500 mb-1">
                      <span className="font-semibold text-blue-700">Step {st.step}: Tool Call ({st.tool})</span>
                    </div>
                    {st.thought && (
                      <p className="text-xs text-slate-600 italic mb-2">"{st.thought}"</p>
                    )}
                    {st.tool === "run_query" && st.arguments?.sql && (
                      <div className="bg-slate-900 text-emerald-400 p-2 rounded font-mono text-xs overflow-x-auto">
                        <code>{st.arguments.sql}</code>
                      </div>
                    )}
                    {st.tool !== "run_query" && (
                      <pre className="text-xs bg-slate-100 p-2 rounded text-slate-700 overflow-x-auto">
                        {JSON.stringify(st.arguments, null, 2)}
                      </pre>
                    )}
                  </div>
                );
              }

              if (st.type === "tool_result") {
                const res = st.result;
                const isSuccess = res?.success !== false;
                return (
                  <div key={i} className="pl-4 border-l-2 border-slate-300">
                    <div className="flex items-center gap-1 text-xs mb-1">
                      {isSuccess ? (
                        <span className="inline-flex items-center gap-1 text-emerald-600 font-medium">
                          <ShieldCheck className="w-3.5 h-3.5" /> Guard Approved ({res?.executionTimeMs || 0}ms)
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-rose-600 font-medium">
                          <ShieldAlert className="w-3.5 h-3.5" /> Guard Rejected
                        </span>
                      )}
                      {res?.rowCount !== undefined && (
                        <span className="text-slate-400">• {res.rowCount} rows returned</span>
                      )}
                    </div>
                    {res?.rows && (
                      <div className="text-xs font-mono text-slate-600 bg-slate-50 p-2 rounded overflow-x-auto max-h-32">
                        {JSON.stringify(res.rows.slice(0, 3), null, 2)}
                        {res.rows.length > 3 && `\n... and ${res.rows.length - 3} more rows`}
                      </div>
                    )}
                    {res?.error && (
                      <p className="text-xs text-rose-600 bg-rose-50 p-2 rounded font-mono">{res.error}</p>
                    )}
                  </div>
                );
              }

              if (st.type === "guard_rejection") {
                return (
                  <div key={i} className="p-2 bg-rose-50 border border-rose-200 rounded text-xs text-rose-800 flex items-center gap-2">
                    <ShieldAlert className="w-4 h-4 text-rose-600 flex-shrink-0" />
                    <span>Self-Correction Triggered: {st.rejection}</span>
                  </div>
                );
              }

              return null;
            })}
          </div>
        </div>
      )}
    </div>
  );
}
