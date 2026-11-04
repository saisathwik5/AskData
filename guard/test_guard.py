"""
test_guard.py
Tests the running Java Query Guard service at http://localhost:8081
Sends valid queries and attack vectors, verifying responses and audit logging.
"""

import json
import urllib.request
import urllib.error

GUARD_URL = "http://localhost:8081"

def send_query(sql: str, user_id: str, question: str):
    url = f"{GUARD_URL}/query"
    payload = json.dumps({
        "sql": sql,
        "userId": user_id,
        "question": question
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return resp.status, data
    except urllib.error.HTTPError as e:
        data = json.loads(e.read().decode("utf-8"))
        return e.code, data
    except Exception as e:
        return 0, {"error": str(e)}

def main():
    print("=========================================================")
    print("       AskData Java Query Guard - Live Verification      ")
    print("=========================================================\n")

    # 1. Health check
    try:
        with urllib.request.urlopen(f"{GUARD_URL}/health") as resp:
            print(f"[✓] Health Check (200 OK): {resp.read().decode('utf-8')}\n")
    except Exception as e:
        print(f"[!] Guard service is not reachable at {GUARD_URL}. Make sure 'mvn spring-boot:run' is running!\nError: {e}")
        return

    test_cases = [
        {
            "name": "Test 1: Valid Analytical Query on v_users",
            "sql": "SELECT country, count(*) AS user_count FROM v_users WHERE country IS NOT NULL GROUP BY country ORDER BY user_count DESC LIMIT 3",
            "userId": "analyst_alice",
            "question": "What are our top 3 countries by user count?",
            "expect_success": True
        },
        {
            "name": "Test 2: PII Attack (Selecting 'email')",
            "sql": "SELECT email FROM users",
            "userId": "hacker_bob",
            "question": "Give me all customer emails",
            "expect_success": False
        },
        {
            "name": "Test 3: Multi-Statement / Drop Table Attack",
            "sql": "SELECT 1; DROP TABLE payments;",
            "userId": "hacker_bob",
            "question": "Wipe payments table",
            "expect_success": False
        },
        {
            "name": "Test 4: Time-Based DOS Attack (pg_sleep)",
            "sql": "SELECT pg_sleep(100)",
            "userId": "hacker_bob",
            "question": "Hang the database server",
            "expect_success": False
        },
        {
            "name": "Test 5: Valid Join Query on Subscriptions & Payments",
            "sql": "SELECT s.plan, COUNT(p.id) AS payments_count FROM v_subscriptions s JOIN v_payments p ON s.user_id = p.user_id WHERE p.status = 'succeeded' GROUP BY s.plan",
            "userId": "analyst_alice",
            "question": "Show successful payments by subscription plan",
            "expect_success": True
        }
    ]

    for tc in test_cases:
        print(f"--- Running {tc['name']} ---")
        print(f"SQL: \"{tc['sql']}\"")
        status, response = send_query(tc["sql"], tc["userId"], tc["question"])

        if tc["expect_success"]:
            if status == 200 and response.get("success"):
                print(f"[PASSED] 200 OK - Execution time: {response.get('executionTimeMs')}ms, Rows returned: {response.get('rowCount')}")
                print(f"Columns: {response.get('columns')}")
                print(f"Sample Rows: {response.get('rows', [])[:2]}")
                print(f"Executed SQL (with limit): \"{response.get('executedSql')}\"\n")
            else:
                print(f"[FAILED] Expected success but got status {status}: {response}\n")
        else:
            if status == 400 and not response.get("success"):
                print(f"[PASSED] 400 Blocked - Error Code: {response.get('errorCode')}")
                print(f"Rejection Message: \"{response.get('message')}\"\n")
            else:
                print(f"[FAILED] Expected blocked but got status {status}: {response}\n")

    print("=========================================================")
    print("Verification complete! Check query_audit_logs in Supabase to see all queries recorded.")

if __name__ == "__main__":
    main()
