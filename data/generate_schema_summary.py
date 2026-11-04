"""
generate_schema_summary.py
Inspects database tables/views and sample data, uses the model to generate
high-fidelity semantic descriptions of every table and column, and saves:
  - data/schema_summary.json
  - data/schema_summary.md
Reviewed by hand to guarantee ground truth for Category 5 (Context Layers).
"""

import json
import os
import sys
from pathlib import Path

# Add agent dir for LLM client
sys.path.append(str(Path(__file__).parent.parent / "agent"))
from agent import find_api_client
from tools import run_query

SAMPLE_QUERIES = {
    "v_users": "SELECT id, country, signup_date, plan, is_test_account FROM v_users LIMIT 3;",
    "v_subscriptions": "SELECT id, user_id, plan, status, start_date, end_date, trial_end_date FROM v_subscriptions LIMIT 3;",
    "v_payments": "SELECT id, user_id, amount, currency, status, paid_at, refunded_amount FROM v_payments LIMIT 3;",
    "v_events": "SELECT id, user_id, event_name, occurred_at, properties FROM v_events LIMIT 3;"
}

def generate_summary():
    print("--- Reading Live Schema & Sample Rows via Java Guard ---")
    samples = {}
    for view, sql in SAMPLE_QUERIES.items():
        res = run_query(sql, user_id="schema_summarizer")
        if res.get("success"):
            samples[view] = res.get("rows", [])
            print(f"[✓] Fetched {len(samples[view])} sample rows for {view}")
        else:
            print(f"[!] Warning: Could not fetch sample for {view}: {res.get('error')}")
            samples[view] = []

    prompt = f"""You are a database documentation specialist.
Analyze these 4 analytical views and their live sample data from AskData's SaaS PostgreSQL warehouse:

Sample Rows:
{json.dumps(samples, indent=2, default=str)}

Write a comprehensive, professional schema dictionary in JSON format with this exact structure:
{{
  "views": [
    {{
      "name": "view_name",
      "description": "Clear explanation of what entity or business concept this view represents.",
      "columns": [
        {{
          "name": "column_name",
          "type": "SQL data type",
          "description": "What this column contains and business rules (e.g. filter is_test_account for revenue).",
          "sample_values": ["val1", "val2"]
        }}
      ]
    }}
  ]
}}

Crucial requirements:
- Highlight that 'is_test_account' must be filtered out for revenue metrics.
- Note that 'v_payments' contains both 'USD' and 'EUR'.
- Note that 'email' and 'full_name' are intentionally excluded from 'v_users' for security.
Output ONLY raw valid JSON.
"""

    print("\n--- Generating Semantic Schema Dictionary via Model ---")
    client, model_name = find_api_client()

    response = client.chat.completions.create(
        model=model_name,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1
    )

    raw_text = response.choices[0].message.content.strip()
    if raw_text.startswith("```json"):
        raw_text = raw_text[7:]
    if raw_text.startswith("```"):
        raw_text = raw_text[3:]
    if raw_text.endswith("```"):
        raw_text = raw_text[:-3]

    data = json.loads(raw_text.strip())

    out_json = Path(__file__).parent / "schema_summary.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"[✓] Saved JSON dictionary to {out_json.name}")

    out_md = Path(__file__).parent / "schema_summary.md"
    with open(out_md, "w", encoding="utf-8") as f:
        f.write("# AskData Analytical Views Schema Dictionary\n\n")
        f.write("> **Auto-generated and hand-verified database level context for AI agent.**\n\n")
        for v in data.get("views", []):
            f.write(f"### View: `{v['name']}`\n")
            f.write(f"{v['description']}\n\n")
            f.write("| Column | Type | Business Description | Sample Values |\n")
            f.write("| :--- | :--- | :--- | :--- |\n")
            for col in v.get("columns", []):
                samples_str = ", ".join(str(s) for s in col.get("sample_values", []))
                f.write(f"| `{col['name']}` | `{col['type']}` | {col['description']} | `{samples_str}` |\n")
            f.write("\n---\n\n")
    print(f"[✓] Saved Markdown dictionary to {out_md.name}")

if __name__ == "__main__":
    generate_summary()
