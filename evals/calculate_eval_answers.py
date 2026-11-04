"""
calculate_eval_answers.py
Executes the SQL queries for the 50 eval questions against the seed dataset
to verify expected results and guarantee ground-truth precision.
"""

import sqlite3
import json
from pathlib import Path

def main():
    con = sqlite3.connect(":memory:")
    cur = con.cursor()

    cur.execute("""
    CREATE TABLE users (
        id TEXT PRIMARY KEY,
        email TEXT NOT NULL UNIQUE,
        full_name TEXT NOT NULL,
        country TEXT,
        signup_date TEXT NOT NULL,
        plan TEXT NOT NULL,
        is_test_account BOOLEAN NOT NULL DEFAULT 0
    );
    """)
    cur.execute("""
    CREATE TABLE subscriptions (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        plan TEXT NOT NULL,
        status TEXT NOT NULL,
        start_date TEXT NOT NULL,
        end_date TEXT,
        trial_end_date TEXT
    );
    """)
    cur.execute("""
    CREATE TABLE payments (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        amount NUMERIC NOT NULL,
        currency TEXT NOT NULL,
        status TEXT NOT NULL,
        paid_at TEXT NOT NULL,
        refunded_amount NUMERIC DEFAULT 0.00
    );
    """)
    cur.execute("""
    CREATE TABLE events (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        event_name TEXT NOT NULL,
        occurred_at TEXT NOT NULL,
        properties TEXT
    );
    """)

    dump_path = Path(__file__).parent.parent / "data" / "askdata_dump.sql"
    print(f"Loading {dump_path.name} into SQLite in-memory engine...")
    with open(dump_path, "r", encoding="utf-8") as f:
        sql = f.read()

    sql = sql.replace("TRUE", "1").replace("FALSE", "0")
    cur.executescript(sql)
    print("Dataset loaded successfully.")

    queries = {
        # 12 Easy
        "q01": "SELECT COUNT(*) FROM users;",
        "q02": "SELECT COUNT(*) FROM users WHERE country = 'CA';",
        "q03": "SELECT COUNT(*) FROM subscriptions WHERE status = 'active';",
        "q04": "SELECT DISTINCT plan FROM subscriptions ORDER BY plan;",
        "q05": "SELECT COUNT(*) FROM payments WHERE status = 'failed';",
        "q06": "SELECT COUNT(*) FROM users WHERE is_test_account = 1;",
        "q07": "SELECT COUNT(*) FROM events;",
        "q08": "SELECT COUNT(*) FROM subscriptions WHERE status = 'trialing';",
        "q09": "SELECT COUNT(*) FROM payments WHERE currency = 'EUR';",
        "q10": "SELECT COUNT(*) FROM events WHERE event_name = 'report_exported';",
        "q11": "SELECT COUNT(*) FROM users WHERE plan = 'enterprise';",
        "q12": "SELECT MAX(amount) FROM payments;",

        # 12 Joins
        "q13": "SELECT COUNT(p.id) FROM payments p JOIN users u ON p.user_id = u.id WHERE p.status = 'succeeded' AND u.plan = 'pro';",
        "q14": "SELECT SUM(p.amount) FROM payments p JOIN users u ON p.user_id = u.id WHERE p.currency = 'USD' AND p.status = 'succeeded' AND u.is_test_account = 0 AND u.country = 'US';",
        "q15": "SELECT u.id, COUNT(e.id) AS query_count FROM users u JOIN events e ON u.id = e.user_id WHERE e.event_name = 'query_executed' GROUP BY u.id ORDER BY query_count DESC LIMIT 5;",
        "q16": "SELECT COUNT(DISTINCT s.user_id) FROM subscriptions s JOIN events e ON s.user_id = e.user_id WHERE s.status = 'active' AND e.event_name = 'dashboard_viewed';",
        "q17": "SELECT COUNT(e.id) FROM events e JOIN users u ON e.user_id = u.id WHERE u.plan = 'starter';",
        "q18": "SELECT COUNT(p.id) FROM payments p JOIN users u ON p.user_id = u.id WHERE p.status = 'refunded' AND u.signup_date >= '2024-01-01' AND u.signup_date < '2025-01-01';",
        "q19": "SELECT u.plan, COUNT(p.id) AS payment_count, SUM(p.amount) AS total_amount FROM payments p JOIN users u ON p.user_id = u.id WHERE p.status = 'succeeded' GROUP BY u.plan ORDER BY total_amount DESC;",
        "q20": "SELECT COUNT(e.id) FROM events e JOIN users u ON e.user_id = u.id WHERE u.is_test_account = 1;",
        "q21": "SELECT u.country, COUNT(DISTINCT u.id) AS paying_users FROM users u JOIN payments p ON u.id = p.user_id WHERE u.is_test_account = 0 AND u.country IS NOT NULL AND p.status = 'succeeded' GROUP BY u.country ORDER BY paying_users DESC LIMIT 3;",
        "q22": "SELECT COUNT(DISTINCT s.user_id) FROM subscriptions s JOIN events e ON s.user_id = e.user_id WHERE s.status = 'canceled' AND s.end_date IS NOT NULL AND e.occurred_at > s.end_date;",
        "q23": "SELECT COALESCE(SUM(p.refunded_amount), 0.00) FROM payments p JOIN users u ON p.user_id = u.id WHERE u.plan = 'enterprise' AND p.currency = 'USD' AND p.status = 'refunded';",
        "q24": "SELECT COUNT(DISTINCT s.user_id) FROM subscriptions s JOIN payments p ON s.user_id = p.user_id WHERE s.status = 'active' AND p.status = 'failed';",

        # 8 Metric Traps
        "q33": "SELECT SUM(CASE s.plan WHEN 'starter' THEN 29 WHEN 'pro' THEN 99 WHEN 'enterprise' THEN 499 ELSE 0 END) AS mrr_usd FROM subscriptions s JOIN users u ON s.user_id = u.id WHERE s.status = 'active' AND u.is_test_account = 0;",
        "q34": "SELECT SUM(p.amount - COALESCE(p.refunded_amount, 0)) AS net_revenue_usd FROM payments p JOIN users u ON p.user_id = u.id WHERE p.status = 'succeeded' AND p.currency = 'USD' AND u.is_test_account = 0;",
        "q35": "SELECT SUM(p.amount) AS gross_revenue_eur FROM payments p JOIN users u ON p.user_id = u.id WHERE p.status = 'succeeded' AND p.currency = 'EUR' AND u.is_test_account = 0;",
        "q36": "SELECT COUNT(DISTINCT s.user_id) AS paying_customers FROM subscriptions s JOIN users u ON s.user_id = u.id WHERE s.status = 'active' AND u.is_test_account = 0;",
        "q37": "SELECT ROUND(SUM(p.refunded_amount) * 100.0 / NULLIF(SUM(p.amount), 0), 2) AS refund_percentage FROM payments p JOIN users u ON p.user_id = u.id WHERE p.status = 'succeeded' AND p.currency = 'USD' AND u.is_test_account = 0;",
        "q38": "SELECT COUNT(DISTINCT s.user_id) FROM subscriptions s JOIN users u ON s.user_id = u.id WHERE u.is_test_account = 0 AND s.trial_end_date IS NOT NULL AND s.status = 'active';",
        "q39": "SELECT COUNT(DISTINCT s.user_id) FROM subscriptions s JOIN users u ON s.user_id = u.id WHERE u.is_test_account = 0 AND s.status = 'canceled' AND s.end_date >= '2024-12-01' AND s.end_date < '2025-01-01';",
        "q40": "SELECT COUNT(DISTINCT e.user_id) FROM events e JOIN users u ON e.user_id = u.id WHERE u.is_test_account = 0 AND e.event_name IN ('query_executed', 'report_exported') AND e.occurred_at >= '2025-06-01' AND e.occurred_at < '2025-07-01';",
    }

    results = {}
    for qid, qsql in queries.items():
        cur.execute(qsql)
        res = cur.fetchall()
        if len(res) == 1 and len(res[0]) == 1:
            val = res[0][0]
            results[qid] = float(val) if isinstance(val, float) else val
        else:
            results[qid] = res
        print(f"[{qid}] -> {results[qid]}")

    out_file = Path(__file__).parent / "ground_truth_answers.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nAll answers exported to {out_file.name}")
    con.close()

if __name__ == "__main__":
    main()
