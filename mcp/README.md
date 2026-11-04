# AskData Model Context Protocol (MCP) Server

This MCP server exposes the four core AskData analytical tools to any standard MCP client (such as Claude Desktop, Cursor, or MCP Inspector):
1. `list_tables`: Lists all analytical views (`v_users`, `v_subscriptions`, `v_payments`, `v_events`).
2. `describe_table`: Returns column types, descriptions, and sample values.
3. `run_query`: Executes SQL queries **strictly through the Java Query Guard (port 8081)**.
4. `make_chart`: Generates a standard JSON chart specification for data visualization.

---

## Defense-in-Depth Guarantee
> [!IMPORTANT]
> **The Java Guard is always in the path:**
> `MCP Client` → `MCP Server` (`mcp/server.py`) → `Java Query Guard` (`http://localhost:8081/query`) → `PostgreSQL Supabase (Read-Only Views)`
>
> The MCP server **never** connects directly to the database or bypasses AST inspection.

---

## 1. Quick Verification Test
Run the automated MCP client simulation script:
```powershell
python test_mcp_client.py
```
This script acts as an external MCP client, sending JSON-RPC 2.0 protocol handshakes (`initialize`, `tools/list`, and `tools/call`), verifying tool discovery and guarded query execution.

---

## 2. Connecting to Claude Desktop
Add this server to your Claude Desktop configuration file:
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "askdata-analytics": {
      "command": "python",
      "args": [
        "C:\\Users\\Sai Sathwik\\OneDrive\\Desktop\\job apps\\project\\AskData\\mcp\\server.py"
      ],
      "env": {
        "GUARD_SERVICE_URL": "http://localhost:8081"
      }
    }
  }
}
```

---

## 3. Connecting to Cursor
In Cursor Settings -> **Features** -> **MCP Servers** -> **Add New MCP Server**:
- **Name:** `askdata-guard`
- **Type:** `command`
- **Command:** `python "C:\Users\Sai Sathwik\OneDrive\Desktop\job apps\project\AskData\mcp\server.py"`

---

## 4. Running with the Official FastMCP SDK
If you install the official MCP SDK:
```powershell
pip install mcp
python server.py --fastmcp
```
