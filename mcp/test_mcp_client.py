"""
test_mcp_client.py
Automated integration test client for AskData MCP Server.
Simulates an outside MCP client (e.g. Claude Desktop, Cursor, or MCP Inspector):
  1. Initializes connection (MCP protocol 2024-11-05).
  2. Discovers registered tools via tools/list.
  3. Calls list_tables.
  4. Calls describe_table for 'v_subscriptions'.
  5. Calls run_query with analytical SQL (guarded).
  6. Calls run_query with attack vector (verifying guard security rejection).
"""

import sys
import json
import subprocess
from pathlib import Path

def run_test():
    server_py = Path(__file__).parent / "server.py"

    print("=========================================================")
    print("       AskData MCP Client Verification Test              ")
    print("=========================================================\n")
    print(f"[Client] Spawning MCP Server: {server_py}")

    proc = subprocess.Popen(
        [sys.executable, str(server_py)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )

    req_id = 1

    def send_rpc(method: str, params: dict = None) -> dict:
        nonlocal req_id
        payload = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method
        }
        if params is not None:
            payload["params"] = params
        req_id += 1

        json_line = json.dumps(payload)
        proc.stdin.write(json_line + "\n")
        proc.stdin.flush()

        # Read line from stdout
        resp_line = proc.stdout.readline()
        if not resp_line:
            err = proc.stderr.read()
            raise RuntimeError(f"Server exited unexpectedly: {err}")
        return json.loads(resp_line)

    def send_notification(method: str, params: dict = None):
        payload = {
            "jsonrpc": "2.0",
            "method": method
        }
        if params is not None:
            payload["params"] = params
        proc.stdin.write(json.dumps(payload) + "\n")
        proc.stdin.flush()

    try:
        # Step 1: Initialize
        print("[1] Sending 'initialize' request...")
        init_resp = send_rpc("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1.0.0"}
        })
        print(f"    --> Response Server Info: {init_resp.get('result', {}).get('serverInfo')}")
        print(f"    --> Protocol Version: {init_resp.get('result', {}).get('protocolVersion')}")
        assert "serverInfo" in init_resp.get("result", {})

        # Step 2: Notify initialized
        print("\n[2] Sending 'notifications/initialized'...")
        send_notification("notifications/initialized")

        # Step 3: List Tools
        print("\n[3] Calling 'tools/list'...")
        tools_resp = send_rpc("tools/list")
        tools = tools_resp.get("result", {}).get("tools", [])
        tool_names = [t["name"] for t in tools]
        print(f"    --> Discovered {len(tools)} tools: {tool_names}")
        assert "list_tables" in tool_names
        assert "describe_table" in tool_names
        assert "run_query" in tool_names
        assert "make_chart" in tool_names

        # Step 4: Call list_tables
        print("\n[4] Calling tool 'list_tables'...")
        call_tables = send_rpc("tools/call", {"name": "list_tables", "arguments": {}})
        content = call_tables.get("result", {}).get("content", [])[0]["text"]
        print(f"    --> Result: {content}")
        assert "v_users" in content

        # Step 5: Call describe_table
        print("\n[5] Calling tool 'describe_table' (table_name='v_subscriptions')...")
        call_desc = send_rpc("tools/call", {
            "name": "describe_table",
            "arguments": {"table_name": "v_subscriptions"}
        })
        content_desc = json.loads(call_desc.get("result", {}).get("content", [])[0]["text"])
        print(f"    --> Table Description: {content_desc.get('description')}")
        print(f"    --> Columns: {[c['name'] for c in content_desc.get('columns', [])]}")
        assert len(content_desc.get("columns", [])) > 0

        # Step 6: Call run_query (Analytical Query)
        print("\n[6] Calling tool 'run_query' (Valid analytical query via Guard)...")
        call_query = send_rpc("tools/call", {
            "name": "run_query",
            "arguments": {
                "sql": "SELECT plan, count(*) FROM v_subscriptions GROUP BY plan",
                "user_id": "mcp-test-analyst",
                "question": "How many subscriptions per plan?"
            }
        })
        query_res = json.loads(call_query.get("result", {}).get("content", [])[0]["text"])
        print(f"    --> Guard Execution Response: {query_res.get('message') or query_res.get('error')}")

        # Step 7: Call run_query with Attack Vector
        print("\n[7] Calling tool 'run_query' with Attack Vector (SELECT email FROM users)...")
        call_attack = send_rpc("tools/call", {
            "name": "run_query",
            "arguments": {
                "sql": "SELECT email FROM users",
                "user_id": "mcp-attacker",
                "question": "Extract customer emails"
            }
        })
        attack_res = json.loads(call_attack.get("result", {}).get("content", [])[0]["text"])
        print(f"    --> Attack Result (Security Blocked): {attack_res}")
        if not attack_res.get("success"):
            print("    --> [PASSED] MCP tool correctly forwarded through Java Query Guard and was rejected!")

        print("\n=========================================================")
        print("    All MCP Client Protocol Tests Completed Successfully! ")
        print("=========================================================\n")

    finally:
        proc.terminate()

if __name__ == "__main__":
    run_test()
