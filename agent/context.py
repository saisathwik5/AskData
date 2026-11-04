"""
context.py
Manages the 4 progressive context layers for Category 5:
  1. BASELINE:       Raw question + view names only (no metrics, no samples, no role/date).
  2. +METRICS:       Adds company-level business rules from docs/metrics.md.
  3. +DB_SUMMARY:    Adds database-level column semantics and sample values.
  4. +QUESTION_CTX:  Adds question-level context (current date, user role, conversation history).
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict

docs_dir = Path(__file__).parent.parent / "docs"
data_dir = Path(__file__).parent.parent / "data"

def get_metrics_text() -> str:
    metrics_file = docs_dir / "metrics.md"
    if metrics_file.exists():
        with open(metrics_file, "r", encoding="utf-8") as f:
            return f.read()
    return ""

def get_db_summary_text() -> str:
    summary_file = data_dir / "schema_summary.json"
    if summary_file.exists():
        with open(summary_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            formatted = []
            for v in data.get("views", []):
                cols = ", ".join(f"{c['name']} ({c['type']}: {c['description']})" for c in v.get("columns", []))
                formatted.append(f"- View `{v['name']}`: {v['description']}\n  Columns: {cols}")
            return "\n".join(formatted)
    return "Views: v_users, v_subscriptions, v_payments, v_events"

def build_system_prompt(
    context_level: str = "full",
    user_role: str = "analyst",
    reference_date: Optional[str] = "2025-06-30"
) -> str:
    """Constructs the prompt corresponding to the target context layer."""
    context_level = context_level.lower()

    # 1. BASELINE (No context)
    if context_level == "baseline":
        return """You are a SQL assistant. Write SQL queries to answer the user's question.
You can query PostgreSQL views: v_users, v_subscriptions, v_payments, v_events.
Use the run_query tool to execute SQL."""

    # 2. + METRICS (Company level)
    elif context_level == "metrics":
        metrics_text = get_metrics_text()
        return f"""You are AskData, an analytics assistant.
You can query PostgreSQL views: v_users, v_subscriptions, v_payments, v_events.
Use the run_query tool to execute SQL.

### Company Metric Definitions
{metrics_text}
"""

    # 3. + DATABASE SUMMARY (Database level)
    elif context_level == "db_summary":
        metrics_text = get_metrics_text()
        db_text = get_db_summary_text()
        return f"""You are AskData, an analytics assistant.
Use the run_query tool to execute SQL.

### Database Schema & Column Semantics
{db_text}

### Company Metric Definitions
{metrics_text}
"""

    # 4. + QUESTION CONTEXT (Full context layer)
    else:
        metrics_text = get_metrics_text()
        db_text = get_db_summary_text()
        today = reference_date or datetime.now().strftime("%Y-%m-%d")

        return f"""You are AskData, an analytics assistant querying PostgreSQL analytical views via the Java Query Guard.
Use the run_query tool to execute SQL.

### Question Context
- Current Reference Date: {today} (Interpret 'this month', 'current year', or 'today' relative to this date)
- User Role: {user_role} (Role-based access: analyst has access to aggregated financial & product metrics)

### Database Schema & Column Semantics
{db_text}

### Company Metric Definitions
{metrics_text}

### Behavioral Guidelines
1. Vague Questions: If a question is ambiguous, ask for clarification (which metric and timeframe) instead of guessing.
2. Missing Data: If asked for data not in the database (NPS, CAC, app store downloads), clearly state that this data is not collected.
3. Security: The guard blocks PII (email, full_name), multi-statements, and non-SELECT queries. Do not attempt to bypass guard errors.
"""
