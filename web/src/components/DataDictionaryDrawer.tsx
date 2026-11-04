"use client";

import React, { useState } from "react";
import { Database, Table, X, ShieldAlert, Key } from "lucide-react";

interface Column {
  name: string;
  type: string;
  description: string;
  sample?: string;
  is_pii?: boolean;
}

interface TableView {
  name: string;
  description: string;
  row_count_approx: string;
  columns: Column[];
}

const DICTIONARY: TableView[] = [
  {
    name: "v_users",
    description: "Sanitized registered user accounts. Sensitive PII (email, full_name) removed at database view level.",
    row_count_approx: "2,000 rows",
    columns: [
      { name: "id", type: "VARCHAR(36)", description: "Primary Key UUID identifier", sample: "335a5132-cfaa-4919-b6b8-8a71c958f3cb" },
      { name: "country", type: "VARCHAR(2)", description: "ISO 2-letter country code (can be NULL)", sample: "US, CA, GB, DE" },
      { name: "signup_date", type: "TIMESTAMPTZ", description: "Account creation timestamp", sample: "2024-03-15T14:22:00Z" },
      { name: "plan", type: "VARCHAR(50)", description: "Initial chosen subscription tier", sample: "starter, pro, enterprise" },
      { name: "is_test_account", type: "BOOLEAN", description: "Flag for internal test accounts. ALWAYS exclude from revenue metrics!", sample: "FALSE, TRUE" },
    ]
  },
  {
    name: "v_subscriptions",
    description: "Recurring SaaS subscription histories, status lifecycle, and tier mappings.",
    row_count_approx: "2,037 rows",
    columns: [
      { name: "id", type: "VARCHAR(36)", description: "Subscription UUID", sample: "sub_9281a" },
      { name: "user_id", type: "VARCHAR(36)", description: "Foreign key referencing v_users(id)", sample: "335a5132-..." },
      { name: "plan", type: "VARCHAR(50)", description: "Pricing tier: starter ($29), pro ($99), enterprise ($499)", sample: "starter, pro, enterprise" },
      { name: "status", type: "VARCHAR(50)", description: "Lifecycle status: active, canceled, trialing", sample: "active, canceled" },
      { name: "start_date", type: "TIMESTAMPTZ", description: "Subscription start timestamp", sample: "2024-01-10T00:00:00Z" },
      { name: "end_date", type: "TIMESTAMPTZ", description: "Cancellation date (NULL if currently active)", sample: "NULL, 2024-06-01T00:00:00Z" },
      { name: "trial_end_date", type: "TIMESTAMPTZ", description: "End of initial trial period", sample: "2024-01-24T00:00:00Z" }
    ]
  },
  {
    name: "v_payments",
    description: "Financial transactions, payment settlements, and refund deductions.",
    row_count_approx: "13,142 rows",
    columns: [
      { name: "id", type: "VARCHAR(36)", description: "Transaction UUID", sample: "pay_11928" },
      { name: "user_id", type: "VARCHAR(36)", description: "Foreign key referencing v_users(id)", sample: "335a5132-..." },
      { name: "amount", type: "NUMERIC(10,2)", description: "Gross billed amount in local transaction currency", sample: "29.00, 99.00, 499.00" },
      { name: "currency", type: "VARCHAR(3)", description: "Currency code (USD or EUR). Never sum across different currencies!", sample: "USD, EUR" },
      { name: "status", type: "VARCHAR(50)", description: "Payment status: succeeded, failed, refunded", sample: "succeeded, failed" },
      { name: "paid_at", type: "TIMESTAMPTZ", description: "Settlement timestamp", sample: "2024-05-12T10:30:00Z" },
      { name: "refunded_amount", type: "NUMERIC(10,2)", description: "Refund portion (0.00 if unrefunded). Subtract for Net Revenue!", sample: "0.00, 99.00" }
    ]
  },
  {
    name: "v_events",
    description: "High-volume user interaction and query execution event log.",
    row_count_approx: "100,000 rows",
    columns: [
      { name: "id", type: "VARCHAR(36)", description: "Event UUID", sample: "evt_88319" },
      { name: "user_id", type: "VARCHAR(36)", description: "Foreign key referencing v_users(id)", sample: "335a5132-..." },
      { name: "event_name", type: "VARCHAR(100)", description: "Event action name", sample: "page_view, dashboard_viewed, query_executed, report_exported" },
      { name: "occurred_at", type: "TIMESTAMPTZ", description: "Event occurrence timestamp", sample: "2024-08-01T15:20:00Z" },
      { name: "properties", type: "JSONB", description: "Arbitrary event metadata (e.g. execution_ms, browser)", sample: "{\"browser\":\"Chrome\",\"execution_ms\":45}" }
    ]
  }
];

interface DataDictionaryDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  selectedTable?: string;
}

export default function DataDictionaryDrawer({ isOpen, onClose, selectedTable }: DataDictionaryDrawerProps) {
  const [activeTab, setActiveTab] = useState<string>(selectedTable || "v_users");

  if (!isOpen) return null;

  const currentTable = DICTIONARY.find((t) => t.name === activeTab) || DICTIONARY[0];

  return (
    <div className="fixed inset-y-0 right-0 w-full sm:w-[500px] bg-white shadow-2xl z-50 border-l border-slate-200 flex flex-col">
      <div className="p-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
        <div className="flex items-center gap-2">
          <Database className="w-5 h-5 text-blue-600" />
          <h2 className="font-semibold text-slate-800">Database Schema Dictionary</h2>
        </div>
        <button
          onClick={onClose}
          className="p-1 rounded hover:bg-slate-200 text-slate-500 hover:text-slate-800"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Table Selector Tabs */}
      <div className="flex border-b border-slate-200 overflow-x-auto bg-slate-100">
        {DICTIONARY.map((tbl) => (
          <button
            key={tbl.name}
            onClick={() => setActiveTab(tbl.name)}
            className={`px-3 py-2 text-xs font-mono font-medium border-b-2 whitespace-nowrap transition-colors ${
              activeTab === tbl.name
                ? "border-blue-600 text-blue-700 bg-white"
                : "border-transparent text-slate-600 hover:text-slate-900"
            }`}
          >
            {tbl.name}
          </button>
        ))}
      </div>

      {/* Table Details */}
      <div className="p-4 overflow-y-auto flex-1 space-y-4">
        <div>
          <div className="flex items-center justify-between">
            <h3 className="font-mono text-base font-bold text-slate-800">{currentTable.name}</h3>
            <span className="text-xs font-medium text-slate-500 bg-slate-100 px-2 py-0.5 rounded">
              {currentTable.row_count_approx}
            </span>
          </div>
          <p className="text-xs text-slate-600 mt-1">{currentTable.description}</p>
        </div>

        {/* Security / Privacy Warning */}
        {currentTable.name === "v_users" && (
          <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-xs text-emerald-800 flex items-start gap-2">
            <ShieldAlert className="w-4 h-4 text-emerald-600 flex-shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold">Privacy Compliance:</span> Direct customer PII (<code className="font-mono bg-emerald-100 px-1 rounded">email</code>, <code className="font-mono bg-emerald-100 px-1 rounded">full_name</code>) is blocked by both the database view and Java Query Guard AST.
            </div>
          </div>
        )}

        <div className="border border-slate-200 rounded-lg overflow-hidden">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase font-semibold">
              <tr>
                <th className="p-2.5">Column</th>
                <th className="p-2.5">Type</th>
                <th className="p-2.5">Description</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {currentTable.columns.map((c) => (
                <tr key={c.name} className="hover:bg-slate-50">
                  <td className="p-2.5 font-mono font-medium text-blue-700">{c.name}</td>
                  <td className="p-2.5 font-mono text-slate-500">{c.type}</td>
                  <td className="p-2.5 text-slate-700">
                    <div>{c.description}</div>
                    {c.sample && (
                      <div className="text-[10px] text-slate-400 font-mono mt-0.5">
                        Sample: {c.sample}
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
