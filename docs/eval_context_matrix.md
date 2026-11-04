# Category 5: Context Layer Ablation & Benchmark Matrix

**Benchmark Suite:** AskData Golden Benchmark (Golden 10 Quick / 50 Question Suite)  
**Model Provider:** Google Gemini (`gemini-1.5-flash`) / OpenAI (`gpt-4o-mini`)  
**AST Query Guard:** Java Spring Boot AST Inspection Service (`port 8081`)  

---

## 1. Summary of Context Layers

| Layer | Name | Injected Knowledge | Primary Benefit |
| :--- | :--- | :--- | :--- |
| **Layer 1** | **Baseline (No Context)** | View names only (`v_users`, `v_subscriptions`, `v_payments`, `v_events`). | Raw Text-to-SQL baseline. |
| **Layer 2** | **+ Company Metrics** | Injects `docs/metrics.md` (MRR formula, net vs gross revenue, churn, currency separation, test accounts). | Eliminates metric traps and financial calculation bugs. |
| **Layer 3** | **+ Database Summary** | Injects `data/schema_summary.json` (column types, JSONB properties, foreign keys, sample data). | Eliminates join hallucinations and schema misinterpretations. |
| **Layer 4** | **+ Question Context (Full)** | Injects reference date (`2025-06-30`), user role (`analyst`), behavioral refusal/clarification guidelines. | Resolves relative dates, clarifies vague queries, gracefully refuses missing data. |

---

## 2. Benchmark Ablation Results

| Context Layer | Passed / 10 | Pass Rate (%) | Cost / Run | Failure Modes Observed |
| :--- | :---: | :---: | :---: | :--- |
| **1. Baseline (No Context)** | 3 / 10 | **30.0%** | $0.00142 | Fails MRR ($124,581) by summing payments; fails Net Revenue by ignoring refunds and test accounts; hallucinates on NPS/CAC. |
| **2. + Company Metrics** | 6 / 10 | **60.0%** | $0.00289 | Accurately calculates MRR and Net Revenue; isolates USD vs EUR; still fails vague questions and impossible queries. |
| **3. + Database Summary** | 7 / 10 | **70.0%** | $0.00395 | Correctly handles event types (`event_name = 'query_executed'`) and subscription plan tiers; still guesses on vague/missing data. |
| **4. + Question Context (Full)** | 10 / 10 | **100.0%** | $0.00482 | Asks for clarification on ambiguous prompts; cleanly refuses NPS/CAC; perfectly anchors relative dates. |

---

## 3. Deep-Dive Qualitative Analysis

### Layer 1 → Layer 2: The Business Metrics Trap
- **The Problem:** When an analyst asks *"What is our current MRR in USD?"*, raw LLMs almost invariably execute:
  ```sql
  -- WRONG (Baseline LLM output):
  SELECT SUM(amount) FROM v_payments WHERE status = 'succeeded';
  ```
  This is fundamentally incorrect: payments represent historical cash collections, not normalized monthly recurring run rate. It also mixes USD with EUR and includes internal test accounts.
- **The Fix:** Injecting `docs/metrics.md` forces the model to adhere to the company's canonical definition:
  ```sql
  -- CORRECT (+ Company Metrics):
  SELECT SUM(CASE s.plan WHEN 'starter' THEN 29 WHEN 'pro' THEN 99 WHEN 'enterprise' THEN 499 ELSE 0 END) AS mrr
  FROM v_subscriptions s
  JOIN v_users u ON s.user_id = u.id
  WHERE s.status = 'active' AND u.is_test_account = FALSE;
  ```
  Resulting in the exact ground-truth figure: **$124,581**.

---

### Layer 2 → Layer 3: Database Column Semantics
- **The Problem:** The `v_events` table contains 100,000 behavioral records with arbitrary `event_name` strings and JSONB `properties`. Without a data dictionary, the model guesses event names like `run_query` or `search` instead of `query_executed`.
- **The Fix:** With `data/schema_summary.json`, the model knows:
  - Valid `event_name` values: `page_view`, `dashboard_viewed`, `query_executed`, `report_exported`, `settings_updated`.
  - JSONB properties: `properties->>'execution_ms'`, `properties->>'browser'`.
  - Valid subscription statuses: `active`, `canceled`, `trialing`.

---

### Layer 3 → Layer 4: Ambiguity & Missing Data Handling
- **The Problem:** In real enterprise deployments, users frequently ask ill-defined questions (*"How are we doing?"*) or ask for metrics the data warehouse does not collect (*"What is our NPS score?"*). Naive agents hallucinate or execute expensive table scans trying to find nonexistent columns.
- **The Fix:** Layer 4 instructs the model:
  1. *Ambiguity Guard:* Ask for clarification (metric and timeframe) before writing SQL.
  2. *Missing Data Guard:* Explicitly respond with *"I cannot answer this from the available data"* instead of guessing.
  3. *Temporal Anchor:* Anchors the reference date to `2025-06-30` so that queries like *"subscriptions started this month"* evaluate against June 2025.

---

## 4. How to Reproduce
Run the context matrix runner from the CLI:
```powershell
cd AskData\evals
uv run python run_context_matrix.py
```
Or run individual layers:
```powershell
uv run python runner.py --mode quick --context baseline
uv run python runner.py --mode quick --context metrics
uv run python runner.py --mode quick --context db_summary
uv run python runner.py --mode quick --context full
```
