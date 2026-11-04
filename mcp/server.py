"""
server.py
Official Model Context Protocol (MCP) Server for AskData.
Wraps the 4 analytical tools:
  1. list_tables
  2. describe_table
  3. run_query (enforces the Java Query Guard at http://localhost:8081)
  4. make_chart

Supports dual runtime modes:
  - Mode A: Official Python MCP SDK (FastMCP) when 'mcp' package is installed.
  - Mode B: Built-in zero-dependency JSON-RPC 2.0 stdio protocol handler.
In both modes, every query strictly routes through the Java Query Guard.
"""

import sys
import os
import json
from pathlib import Path
from typing import Dict, Any, List

# Ensure agent directory is importable
agent_dir = Path(__file__).parent.parent / "agent"
sys.path.append(str(agent_dir))

import tools

# Load environment variables (.env)
def load_env():
    possible_envs = [
        Path(__file__).parent / ".env",
        Path(__file__).parent.parent / ".env"
    ]
    for p in possible_envs:
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip('"').strip("'")
                        if k not in os.environ:
                            os.environ[k] = v
            break

load_env()

# Check for official MCP SDK
try:
    from mcp.server.fastmcp import FastMCP
    HAS_FASTMCP = True
except ImportError:
    HAS_FASTMCP = False

# Tool definitions
MCP_TOOLS_SPEC = [
    {
        "name": "list_tables",
        "description": "Lists all available analytical database views (e.g. v_users, v_subscriptions, v_payments, v_events).",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "describe_table",
        "description": "Provides schema, column definitions, data types, and sample values for an analytical view.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "table_name": {
                    "type": "string",
                    "description": "Name of the table/view (e.g. 'v_users', 'v_payments')"
                }
            },
            "required": ["table_name"]
        }
    },
    {
        "name": "run_query",
        "description": "Executes a SELECT query strictly through the AskData Java Query Guard (port 8081) with AST security inspection.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "sql": {
                    "type": "string",
                    "description": "The exact SQL SELECT query to validate and execute."
                },
                "user_id": {
                    "type": "string",
                    "description": "User identifier for audit logging (default: 'mcp-analyst')."
                },
                "question": {
                    "type": "string",
                    "description": "Original business question for audit logging."
                }
            },
            "required": ["sql"]
        }
    },
    {
        "name": "make_chart",
        "description": "Generates a structured JSON chart specification for visualizing data.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "chart_type": {
                    "type": "string",
                    "enum": ["bar", "line", "pie", "area"],
                    "description": "Type of visualization."
                },
                "title": {
                    "type": "string",
                    "description": "Title of the chart."
                },
                "x_axis": {
                    "type": "string",
                    "description": "Column name for X axis."
                },
                "y_axis": {
                    "type": "string",
                    "description": "Column name for Y axis."
                },
                "data": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Data points list returned from query."
                }
            },
            "required": ["chart_type", "title", "x_axis", "y_axis", "data"]
        }
    }
]

def run_pure_stdio_mcp():
    """
    Standard JSON-RPC 2.0 stdio server implementation adhering to the MCP 2024-11-05 specification.
    Compatible with Claude Desktop, Cursor, and any MCP stdio transport client.
    """
    sys.stderr.write("[AskData MCP] Starting stdio MCP server (protocol version: 2024-11-05)...\n")
    sys.stderr.flush()

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue

        req_id = req.get("id")
        method = req.get("method")
        params = req.get("params", {})

        # Handle notifications (no id)
        if req_id is None:
            if method == "notifications/initialized":
                sys.stderr.write("[AskData MCP] Client initialized notification received.\n")
                sys.stderr.flush()
            continue

        response = {
            "jsonrpc": "2.0",
            "id": req_id
        }

        if method == "initialize":
            response["result"] = {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "askdata-query-guard-mcp",
                    "version": "1.0.0"
                }
            }

        elif method == "tools/list":
            response["result"] = {
                "tools": MCP_TOOLS_SPEC
            }

        elif method == "tools/call":
            tool_name = params.get("name")
            args = params.get("arguments", {})

            try:
                res = tools.execute_tool(
                    tool_name=tool_name,
                    args=args,
                    user_id=args.get("user_id", "mcp-analyst"),
                    question=args.get("question", "MCP tool invocation")
                )
                response["result"] = {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(res, indent=2, default=str)
                        }
                    ]
                }
            except Exception as e:
                response["result"] = {
                    "isError": True,
                    "content": [
                        {
                            "type": "text",
                            "text": f"Tool execution failed: {str(e)}"
                        }
                    ]
                }

        elif method == "ping":
            response["result"] = {}

        else:
            response["error"] = {
                "code": -32601,
                "message": f"Method not found: {method}"
            }

        out_str = json.dumps(response)
        sys.stdout.write(out_str + "\n")
        sys.stdout.flush()

def run_fastmcp():
    """Runs the server using the official FastMCP SDK."""
    mcp = FastMCP(
        "AskData Guard Tools",
        description="AskData Text-to-SQL analytics tools guarded by Java AST security filter."
    )

    @mcp.tool()
    def list_tables() -> List[str]:
        """Lists all queryable analytical database views."""
        return tools.list_tables()

    @mcp.tool()
    def describe_table(table_name: str) -> Dict[str, Any]:
        """Describes schema, columns, types, and sample data for an analytical view."""
        return tools.describe_table(table_name)

    @mcp.tool()
    def run_query(sql: str, user_id: str = "mcp-user", question: str = "") -> Dict[str, Any]:
        """Executes a SELECT query strictly through the Java Query Guard (port 8081)."""
        return tools.run_query(sql, user_id, question)

    @mcp.tool()
    def make_chart(chart_type: str, title: str, x_axis: str, y_axis: str, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generates a structured JSON chart specification for visual rendering."""
        return tools.make_chart(chart_type, title, x_axis, y_axis, data)

    mcp.run()

if __name__ == "__main__":
    # If explicitly requested or fastmcp available with argument
    if "--fastmcp" in sys.argv and HAS_FASTMCP:
        run_fastmcp()
    else:
        run_pure_stdio_mcp()
