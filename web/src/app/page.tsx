"use client";

import React, { useState, useRef, useEffect } from "react";
import {
  Send, Bot, User, ShieldCheck, Database, BarChart3,
  RefreshCw, Sparkles, AlertCircle, Info, ChevronRight
} from "lucide-react";
import AgentStepDrawer from "../components/AgentStepDrawer";
import ChartViewer from "../components/ChartViewer";
import DataDictionaryDrawer from "../components/DataDictionaryDrawer";

interface Message {
  id: string;
  sender: "user" | "agent";
  text: string;
  steps: any[];
  charts: any[];
  metrics?: any;
  loading?: boolean;
}

const SAMPLE_PROMPTS = [
  "What is our current Monthly Recurring Revenue (MRR) in USD?",
  "What is our total net revenue to date in USD?",
  "Which 5 users have executed the highest number of queries?",
  "How many paying customers do we have right now?",
  "How are we doing? (Test vague clarification)",
  "SELECT email FROM users (Test attack refusal)"
];

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      sender: "agent",
      text: "👋 Welcome to **AskData**. I am your guarded AI data analytics assistant.\n\nAsk me any financial, subscription, or product usage questions. Every SQL query I execute is inspected by our secondary **Java Query Guard (Port 8081)** and strictly executed on sanitized read-only views with customer PII blocked.",
      steps: [],
      charts: []
    }
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isDictOpen, setIsDictOpen] = useState(false);
  const [selectedTable, setSelectedTable] = useState<string>("v_users");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (questionText?: string) => {
    const q = (questionText || input).trim();
    if (!q || isLoading) return;

    setInput("");
    const userMsgId = `user_${Date.now()}`;
    const agentMsgId = `agent_${Date.now()}`;

    // Add user message & placeholder agent message
    setMessages((prev) => [
      ...prev,
      { id: userMsgId, sender: "user", text: q, steps: [], charts: [] },
      { id: agentMsgId, sender: "agent", text: "", steps: [], charts: [], loading: true }
    ]);
    setIsLoading(true);

    try {
      const response = await fetch("http://localhost:8000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: json.stringify({ question: q, userId: "analyst-web" })
      });

      if (!response.ok) {
        throw new Error(`Server returned HTTP ${response.status}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let accumulatedSteps: any[] = [];
      let accumulatedCharts: any[] = [];
      let answerText = "";
      let metrics = undefined;

      while (reader) {
        const { value, done } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split("\n");

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const dataStr = line.slice(6).trim();
            if (dataStr === "[DONE]") break;

            try {
              const event = JSON.parse(dataStr);
              accumulatedSteps.push(event);

              if (event.type === "final_answer") {
                answerText = event.answer || "";
                accumulatedCharts = event.charts || [];
                metrics = event.metrics;
              } else if (event.type === "error") {
                answerText = `❌ Error: ${event.message}`;
              }

              // Update the active agent message in state
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === agentMsgId
                    ? {
                        ...m,
                        text: answerText || "Thinking and querying database...",
                        steps: [...accumulatedSteps],
                        charts: accumulatedCharts,
                        metrics: metrics,
                        loading: !answerText
                      }
                    : m
                )
              );
            } catch (err) {
              console.warn("Error parsing SSE JSON:", err);
            }
          }
        }
      }
    } catch (err: any) {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === agentMsgId
            ? {
                ...m,
                text: `⚠️ **Unable to connect to AskData Agent backend.**\n\nEnsure the Python FastAPI server is running: \`uvicorn app:app --port 8000\`\n\n*Error details:* \`${err.message}\``,
                loading: false
              }
            : m
        )
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex h-screen bg-slate-100 overflow-hidden font-sans">
      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col h-full max-w-5xl mx-auto border-x border-slate-200 bg-white shadow-sm">
        {/* Header */}
        <header className="p-4 border-b border-slate-200 flex items-center justify-between bg-white">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center text-white shadow-sm">
              <Bot className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="font-bold text-slate-900 text-lg">AskData Analytics</h1>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-100 text-emerald-800 flex items-center gap-1">
                  <ShieldCheck className="w-3 h-3" /> Java Guard Port 8081
                </span>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-blue-100 text-blue-800">
                  Gemini Flash (1st Pref)
                </span>
              </div>
              <p className="text-xs text-slate-500">Defense-in-depth conversational Text-to-SQL with AST query security</p>
            </div>
          </div>

          <button
            onClick={() => setIsDictOpen(true)}
            className="flex items-center gap-2 px-3 py-1.5 text-xs font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg border border-slate-300 transition-colors"
          >
            <Database className="w-4 h-4 text-blue-600" />
            <span>Schema Dictionary</span>
          </button>
        </header>

        {/* Messages List */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-slate-50">
          {messages.map((m) => (
            <div
              key={m.id}
              className={`flex gap-3 ${m.sender === "user" ? "justify-end" : "justify-start"}`}
            >
              {m.sender === "agent" && (
                <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-white flex-shrink-0 mt-1 shadow-sm">
                  <Bot className="w-4 h-4" />
                </div>
              )}

              <div
                className={`max-w-[85%] rounded-2xl p-4 shadow-sm text-sm ${
                  m.sender === "user"
                    ? "bg-blue-600 text-white rounded-tr-none"
                    : "bg-white text-slate-800 border border-slate-200 rounded-tl-none"
                }`}
              >
                {/* Content */}
                <div className="whitespace-pre-wrap leading-relaxed">
                  {m.text || (m.loading && <span className="animate-pulse text-slate-500">Querying database...</span>)}
                </div>

                {/* Render any charts */}
                {m.charts && m.charts.length > 0 && (
                  <div className="mt-3">
                    {m.charts.map((ch, idx) => (
                      <ChartViewer key={idx} spec={ch} />
                    ))}
                  </div>
                )}

                {/* Agent Steps Drawer */}
                {m.sender === "agent" && m.steps && m.steps.length > 0 && (
                  <AgentStepDrawer steps={m.steps} metrics={m.metrics} />
                )}
              </div>

              {m.sender === "user" && (
                <div className="w-8 h-8 rounded-full bg-slate-800 flex items-center justify-center text-white flex-shrink-0 mt-1 shadow-sm">
                  <User className="w-4 h-4" />
                </div>
              )}
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        {/* Sample Prompts Pills */}
        <div className="p-2 bg-slate-50 border-t border-slate-200 overflow-x-auto flex gap-2">
          {SAMPLE_PROMPTS.map((sp, idx) => (
            <button
              key={idx}
              onClick={() => handleSubmit(sp)}
              disabled={isLoading}
              className="text-xs bg-white hover:bg-blue-50 hover:text-blue-700 hover:border-blue-300 text-slate-600 border border-slate-200 px-3 py-1 rounded-full whitespace-nowrap transition-all shadow-2xs"
            >
              {sp}
            </button>
          ))}
        </div>

        {/* Input Form */}
        <div className="p-4 bg-white border-t border-slate-200">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSubmit();
            }}
            className="flex gap-2"
          >
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask an analytics question (e.g. 'What is our MRR in USD?')..."
              disabled={isLoading}
              className="flex-1 px-4 py-2.5 rounded-xl border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-slate-50 focus:bg-white transition-all text-slate-900"
            />
            <button
              type="submit"
              disabled={isLoading || !input.trim()}
              className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded-xl font-medium text-sm flex items-center gap-2 shadow-sm transition-colors"
            >
              {isLoading ? (
                <RefreshCw className="w-4 h-4 animate-spin" />
              ) : (
                <Send className="w-4 h-4" />
              )}
              <span>Ask</span>
            </button>
          </form>
        </div>
      </div>

      {/* Schema Dictionary Drawer */}
      <DataDictionaryDrawer
        isOpen={isDictOpen}
        onClose={() => setIsDictOpen(false)}
        selectedTable={selectedTable}
      />
    </div>
  );
}
