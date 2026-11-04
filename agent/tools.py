"""
tools.py
Tool definitions and implementations for the AskData Python Agent.
Includes:
  1. list_tables
  2. describe_table
  3. run_query (invokes the Java Guard service)
  4. make_chart
"""

import json
import os
import urllib.request
import urllib.error
from typing import Dict, Any, List

GUARD_SERVICE_URL = os.getenv("GUARD_SERVICE_URL", "http://localhost:8081")

# Static schema descriptions for fast inspection
SCHEMA_CATALOG = {
    "v_users": {
        "description": "Safe view of registered users (PII email & full_name removed).",
        "columns": [
            {"name": "id", "type": "VARCHAR(36)", "description": "Primary key UUID", "sample": "335a5132-cfaa-4919-b6b8-8a71c958f3cb"},
            {"name": "country", "type": "VARCHAR(2)", "description": "ISO 2-letter country code (can be NULL)", "sample": "US, CA, DE, NULL"},
            {"name": "signup_date", "type": "TIMESTAMPTZ", "description": "When the user registered", "sample": "2024-03-15T14:22:00Z"},
            {"name": "plan", "type": "VARCHAR(50)", "description": "Initial selected plan", "sample": "starter, pro, enterprise"},
            {"name": "is_test_account", "type": "BOOLEAN", "description": "TRUE for internal test accounts (exclude from revenue!)", "sample": "FALSE, TRUE"}
        ]
    },
    "v_subscriptions": {
        "description": "Customer subscription histories and statuses.",
        "columns": [
            {"name": "id", "type": "VARCHAR(36)", "description": "Primary key UUID", "sample": "s-48192-uuid"},
            {"name": "user_id", "type": "VARCHAR(36)", "description": "Foreign key referencing v_users(id)", "sample": "u-1234"},
            {"name": "plan", "type": "VARCHAR(50)", "description": "Subscription tier: starter ($29), pro ($99), enterprise ($499)", "sample": "starter, pro, enterprise"},
            {"name": "status", "type": "VARCHAR(50)", "description": "Subscription status", "sample": "active, canceled, trialing"},
            {"name": "start_date", "type": "TIMESTAMPTZ", "description": "When subscription started", "sample": "2024-01-15T00:00:00Z"},
            {"name": "end_date", "type": "TIMESTAMPTZ", "description": "When canceled (NULL for active)", "sample": "NULL, 2024-06-01T00:00:00Z"},
            {"name": "trial_end_date", "type": "TIMESTAMPTZ", "description": "End of 14-day trial period", "sample": "2024-01-29T00:00:00Z"}
        ]
    },
    "v_payments": {
        "description": "Billing charges, settlements, and refund logs.",
        "columns": [
            {"name": "id", "type": "VARCHAR(36)", "description": "Primary key UUID", "sample": "p-99124-uuid"},
            {"name": "user_id", "type": "VARCHAR(36)", "description": "Foreign key referencing v_users(id)", "sample": "u-1234"},
            {"name": "amount", "type": "NUMERIC(10,2)", "description": "Gross billed charge amount", "sample": "29.00, 99.00, 499.00"},
            {"name": "currency", "type": "VARCHAR(3)", "description": "Billing currency (USD or EUR - DO NOT MIX)", "sample": "USD, EUR"},
            {"name": "status", "type": "VARCHAR(50)", "description": "Payment outcome", "sample": "succeeded, failed, refunded"},
            {"name": "paid_at", "type": "TIMESTAMPTZ", "description": "Transaction settlement timestamp", "sample": "2024-05-10T12:00:00Z"},
            {"name": "refunded_amount", "type": "NUMERIC(10,2)", "description": "Portion refunded (0.00 for non-refunds)", "sample": "0.00, 99.00"}
        ]
    },
    "v_events": {
        "description": "High-volume product usage and behavioral event stream (100k rows).",
        "columns": [
            {"name": "id", "type": "VARCHAR(36)", "description": "Primary key UUID", "sample": "e-55102-uuid"},
            {"name": "user_id", "type": "VARCHAR(36)", "description": "Foreign key referencing v_users(id)", "sample": "u-1234"},
            {"name": "event_name", "type": "VARCHAR(100)", "description": "Product action", "sample": "page_view, dashboard_viewed, query_executed, report_exported, settings_updated"},
            {"name": "occurred_at", "type": "TIMESTAMPTZ", "description": "When action took place", "sample": "2024-08-12T19:40:00Z"},
            {"name": "properties", "type": "JSONB", "description": "JSON metadata (e.g. execution_ms, browser, format)", "sample": "{\"browser\": \"Chrome\", \"execution_ms\": 42}"}
        ]
    }
}

# --- Tool Functions ---

def list_tables() -> List[str]:
    """Returns the names of all queryable views in the analytical database."""
    return list(SCHEMA_CATALOG.keys())

def describe_table(table_name: str) -> Dict[str, Any]:
    """Returns the schema, column types, descriptions, and sample values for a table/view."""
    table_name = table_name.lower().strip()
    if table_name.startswith("public."):
        table_name = table_name.replace("public.", "")
    if table_name in SCHEMA_CATALOG:
        return SCHEMA_CATALOG[table_name]
    return {
        "error": f"Table '{table_name}' does not exist. Permitted views are: {list_tables()}"
    }

def run_query(sql: str, user_id: str = "agent_user", question: str = "") -> Dict[str, Any]:
    """Sends SQL to the Java Query Guard (port 8081). Enforces AST validation and read-only execution."""
    guard_endpoint = f"{GUARD_SERVICE_URL}/query"
    payload = json.dumps({
        "sql": sql,
        "userId": user_id,
        "question": question
    }).encode("utf-8")

    req = urllib.request.Request(
        guard_endpoint,
        data=payload,
        headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data
    except urllib.error.HTTPError as e:
        try:
            error_data = json.loads(e.read().decode("utf-8"))
            return {
                "success": False,
                "error": error_data.get("message", "Security Guard Rejected Query"),
                "errorCode": error_data.get("errorCode", "GUARD_REJECTED"),
                "executedSql": sql
            }
        except Exception:
            return {
                "success": False,
                "error": f"HTTP {e.code}: {e.reason}",
                "executedSql": sql
            }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to connect to Java Query Guard at {GUARD_SERVICE_URL}. Is the service running? Details: {str(e)}",
            "executedSql": sql
        }

def make_chart(chart_type: str, title: str, x_axis: str, y_axis: str, data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generates a standard JSON chart specification for visual rendering."""
    valid_types = ["bar", "line", "pie", "area"]
    if chart_type.lower() not in valid_types:
        chart_type = "bar"
    return {
        "type": "chart",
        "chart_type": chart_type.lower(),
        "title": title,
        "x_axis": x_axis,
        "y_axis": y_axis,
        "data": data
    }


# --- Tool Definitions (OpenAI / Gemini function calling format) ---

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "list_tables",
            "description": "Lists the available analytical views in the database.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "describe_table",
            "description": "Describes the schema, columns, types, and sample data for a table or view.",
            "parameters": {
                "type": "object",
                "properties": {
                    "table_name": {
                        "type": "string",
                        "description": "The name of the view (e.g. 'v_users', 'v_payments')"
                    }
                },
                "required": ["table_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_query",
            "description": "Executes a validated SELECT query against the PostgreSQL database via the Java Query Guard.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": "The exact SQL SELECT query to run (targeting v_users, v_subscriptions, v_payments, or v_events)."
                    }
                },
                "required": ["sql"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "make_chart",
            "description": "Creates a chart specification to visualize query results (e.g. bar chart, line chart, pie chart).",
            "parameters": {
                "type": "object",
                "properties": {
                    "chart_type": {
                        "type": "string",
                        "enum": ["bar", "line", "pie", "area"],
                        "description": "The type of chart to display."
                    },
                    "title": {
                        "type": "string",
                        "description": "Title of the chart"
                    },
                    "x_axis": {
                        "type": "string",
                        "description": "Name of the column for the X-axis"
                    },
                    "y_axis": {
                        "type": "string",
                        "description": "Name of the column for the Y-axis"
                    },
                    "data": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "List of data point objects returned from the query"
                    }
                },
                "required": ["chart_type", "title", "x_axis", "y_axis", "data"]
            }
        }
    }
]

def execute_tool(tool_name: str, args: Dict[str, Any], user_id: str = "agent_user", question: str = "") -> Any:
    """Dispatches tool execution to the appropriate Python function."""
    if tool_name == "list_tables":
        return list_tables()
    elif tool_name == "describe_table":
        return describe_table(args.get("table_name", ""))
    elif tool_name == "run_query":
        return run_query(args.get("sql", ""), user_id=user_id, question=question)
    elif tool_name == "make_chart":
        return make_chart(
            chart_type=args.get("chart_type", "bar"),
            title=args.get("title", ""),
            x_axis=args.get("x_axis", ""),
            y_axis=args.get("y_axis", ""),
            data=args.get("data", [])
        )
    else:
        return {"error": f"Unknown tool '{tool_name}'"}
