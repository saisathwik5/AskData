# AskData: Enterprise AI Text-to-SQL with AST Query Guard

> **A production-grade, defense-in-depth conversational data analytics platform.**  
> Features a hand-crafted Python agent loop, multi-model adapter, a dedicated **Java Spring Boot AST Query Guard**, full **Model Context Protocol (MCP)** support, and progressive context layers.

---

## 🏛️ System Architecture

```
                                  ┌────────────────────────┐
                                  │   User / Web UI / MCP  │
                                  └───────────┬────────────┘
                                              │ Business Question
                                              ▼
                             ┌─────────────────────────────────┐
                             │       AskData Python Agent      │
                             │  (Hand-crafted loop, max 8 steps)│
                             │  - Priority: Google Gemini 1st  │
                             │  - Priority: OpenAI ChatGPT 2nd │
                             └───────────────┬─────────────────┘
                                             │ Generated SQL
                                             ▼
                             ┌─────────────────────────────────┐
                             │     Java Query Guard (Port 8081)│
                             │  (Spring Boot + JSqlParser AST) │
                             │  • Single SELECT validation     │
                             │  • PII Column Blocking (email)  │
                             │  • Dangerous Function Blocking  │
                             │  • LIMIT 1000 injection/clamping│
                             │  • Writes query_audit_logs      │
                             └───────────────┬─────────────────┘
                                             │ AST-Approved SQL
                                             ▼
                             ┌─────────────────────────────────┐
                             │   Supabase PostgreSQL Pooler    │
                             │  • Role: askdata_readonly       │
                             │  • Safe Views: v_users, ...     │
                             │  • statement_timeout = 5000ms   │
                             │  • Row-Level Security (RLS)     │
                             └─────────────────────────────────┘
```

---

## 🛡️ Defense-in-Depth Security Model

AskData rejects the naive paradigm of letting an LLM execute arbitrary SQL directly against an operational database:

1. **Database Layer (Primary Defense):**
   - **Restricted Role:** Connected via `askdata_readonly` with zero permissions on underlying tables.
   - **Sanitized Analytical Views:** `v_users` directly excludes PII (`email`, `full_name`).
   - **Strict Timeout:** `ALTER ROLE askdata_readonly SET statement_timeout = '5000ms';` protects against expensive table scans and denial-of-service queries.
2. **AST Inspection Layer (Secondary Defense):**
   - Implemented as a dedicated Java microservice utilizing **JSqlParser 4.9**.
   - Traverses the SQL Abstract Syntax Tree (AST), inspecting all `Select`, `Join`, `ParenthesedSelect`, and `WithItem` (CTE) expressions.
   - Blocks non-SELECT statements (`INSERT`, `UPDATE`, `DROP`, `ALTER`, `GRANT`, multiple statements).
   - Blocks dangerous system catalogs (`information_schema`, `pg_catalog`) and functions (`pg_sleep`).
   - Injects or clamps `LIMIT 1000` to prevent memory exhaustion.
   - Records every attempt (user, query, execution time, block status) to `query_audit_logs`.
   - Verified with **38 automated JUnit security attack tests**.

---

## 📊 Category 5: Context Layer Ablation Benchmark

We evaluated the agent across **4 progressive context layers** against our 50-question golden dataset:

| Context Layer | Pass Rate | Key Improvements & Observations |
| :--- | :---: | :--- |
| **1. Baseline (No Context)** | **30.0%** | Fails financial metric traps (sums historical payments instead of multiplying active subscription plan prices); fails net revenue by ignoring refunds; hallucinates on uncollected metrics. |
| **2. + Company Metrics** | **60.0%** | Injects `docs/metrics.md`. Eliminates the MRR trap ($124,581), correctly computes Net Revenue ($979,773), isolates USD vs EUR, and excludes internal test accounts (`is_test_account = FALSE`). |
| **3. + Database Summary** | **70.0%** | Injects `data/schema_summary.json`. Eliminates schema hallucinations, informs the model of enum values (`status = 'active'`, `event_name = 'query_executed'`), and correctly navigates JSONB properties. |
| **4. + Question Context (Full)** | **100.0%** *(Quick)* / **92.0%** *(Full 50)* | Injects reference date (`2025-06-30`), user role (`analyst`), and behavioral rules. Correctly asks for clarification on vague queries and gracefully refuses uncollected metrics (NPS, CAC). |

*Full analysis available in [docs/eval_context_matrix.md](file:///c:/Users/Sai%20Sathwik/OneDrive/Desktop/job%20apps/project/AskData/docs/eval_context_matrix.md).*

---

## 🤖 Category 7: Multi-Model Switch

Switch model providers seamlessly via environment variables or `.env`:
- **1st Preference (Default):** Google Gemini (`gemini-1.5-flash` / `gemini-2.0-flash` / `gemini-2.5-flash`) via the OpenAI-compatible endpoint.
- **2nd Preference:** OpenAI ChatGPT (`gpt-4o-mini` / `gpt-4o`).
- **3rd Preference:** Anthropic Claude (`claude-3-5-sonnet`).

```bash
# In your .env:
MODEL_PROVIDER="gemini"
GEMINI_MODEL="gemini-1.5-flash"
GEMINI_API_KEY="AIzaSy..."

# Or switch to OpenAI:
# MODEL_PROVIDER="openai"
# OPENAI_MODEL="gpt-4o-mini"
# OPENAI_API_KEY="sk-proj-..."
```

---

## 🔌 Category 6: Model Context Protocol (MCP) Server

AskData provides an official MCP Server in `mcp/server.py` exposing all 4 analytical tools (`list_tables`, `describe_table`, `run_query`, `make_chart`) over stdio JSON-RPC 2.0.

> **Crucial Guarantee:** The MCP server **never** bypasses the security guard:
> `MCP Client (Claude Desktop / Cursor)` → `mcp/server.py` → `Java Guard (Port 8081)` → `Database`

### Connect to Claude Desktop
Add to `%APPDATA%\Claude\claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "askdata-analytics": {
      "command": "python",
      "args": ["C:\\Users\\Sai Sathwik\\OneDrive\\Desktop\\job apps\\project\\AskData\\mcp\\server.py"],
      "env": {
        "GUARD_SERVICE_URL": "http://localhost:8081"
      }
    }
  }
}
```

Verify with the automated MCP test client:
```powershell
uv run python mcp/test_mcp_client.py
```

---

## 🚀 Quickstart Guide

### 1. Start the Java Query Guard (Port 8081)
```powershell
cd guard
mvn spring-boot:run
```
*(Runs AST security filter and database proxy at `http://localhost:8081`).*

### 2. Run the Interactive CLI Agent
```powershell
cd agent
uv run python cli.py "What is our current Monthly Recurring Revenue (MRR) in USD?"
```

### 3. Launch the Web UI & Streaming API
```powershell
cd agent
uv run uvicorn app:app --port 8000 --reload
```
Open **`http://localhost:8000`** in your browser to interact with the streaming chat dashboard, collapsible reasoning drawers, Chart.js visualizations, and schema dictionary!

Or run the Next.js 14 frontend:
```powershell
cd web
npm install
npm run dev
```

### 4. Run the Golden Evaluation Suite
```powershell
cd evals
# Quick benchmark (10 core questions)
uv run python runner.py --mode quick

# Run full context layer progression matrix
uv run python run_context_matrix.py
```

---

## 📁 Repository Structure

```
AskData/
├── agent/                     # Hand-crafted Python Agent loop
│   ├── agent.py               # Core step-by-step orchestrator
│   ├── app.py                 # FastAPI streaming SSE server & web host
│   ├── cli.py                 # Interactive terminal CLI
│   ├── context.py             # Category 5: Progressive context layer builder
│   ├── models.py              # Category 7: Multi-model adapter (Gemini/OpenAI)
│   ├── tools.py               # 4 Tools (list_tables, describe, run_query, chart)
│   └── static/index.html      # Category 9: Rich browser analytics dashboard
├── data/                      # Synthetic SaaS data & DB setup
│   ├── generate_data.py       # Seeded generator (users, subs, payments, 100k events)
│   ├── guard_setup.sql        # Views, askdata_readonly role, query_audit_logs
│   └── schema_summary.json    # Database data dictionary
├── docs/                      # Business metrics & system docs
│   ├── metrics.md             # Canonical MRR, churn, and revenue definitions
│   ├── eval_context_matrix.md # Category 5 ablation benchmark table
│   └── deployment.md          # Docker & AWS/ECS production deployment guide
├── evals/                     # Benchmark suite
│   ├── questions.json         # 50 golden questions across 6 categories
│   ├── runner.py              # Automated test runner with numeric tolerances
│   └── run_context_matrix.py  # Context ablation runner
├── guard/                     # Category 3: Java Query Guard Microservice
│   ├── src/main/java/...      # JSqlParser AST analysis & Supabase proxy
│   ├── src/test/java/...      # 38 JUnit security attack tests
│   └── pom.xml                # Spring Boot 3 + JSqlParser 4.9
├── mcp/                       # Category 6: Model Context Protocol
│   ├── server.py              # MCP stdio & FastMCP server
│   ├── test_mcp_client.py     # MCP automated test client
│   └── README.md              # Claude Desktop / Cursor configuration
├── web/                       # Category 9: Next.js 14 Web Frontend
│   ├── src/app/page.tsx       # Real-time chat & streaming UI
│   ├── src/components/        # Recharts, StepDrawer, DataDictionary
│   └── package.json           # Next.js, Tailwind, Recharts, Lucide
├── docker-compose.yml         # Container orchestration (Guard + Agent)
├── .env.example               # Template environment configuration
└── README.md                  # System documentation
```
