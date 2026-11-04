# /agent: Python Text-to-SQL Agent

The AskData Python Agent is a hand-crafted autonomous analytics agent that translates natural language questions into safe SQL queries, executes them through the Java Query Guard, and returns verified insights.

---

## Agent Loop Architecture

```
User Question
     │
     ▼
[System Prompt & Strict Metrics]
     │
     ▼
[Model Invocation] ──(Asks Tool)──> [Tool Execution]
     │                                     │
     │                           ┌─────────┴─────────┐
     │                           ▼                   ▼
     │                      list_tables         run_query
     │                     describe_table       make_chart
     │                           │                   │
     │                           └─────────┬─────────┘
     │                                     ▼
     │                          [Java Guard (8081)]
     │                                     │
     │                  (Success / Security Error)
     │                                     │
     ▼                                     ▼
[Model Reasoning] <───(Tool Result / Guard Feedback)
     │
     ├─ [If Error]: Self-corrects SQL (up to 3 retries)
     ├─ [If Vague]: Asks for metric/timeframe clarification
     ├─ [If Missing Data]: Refuses ("Data not collected")
     └─ [If Success]: Delivers final answer + tokens/cost metrics
```

---

## 4 Core Tools

1. **`list_tables`**: Lists permitted analytical views (`v_users`, `v_subscriptions`, `v_payments`, `v_events`).
2. **`describe_table`**: Returns schema definitions, column types, descriptions, and sample values.
3. **`run_query`**: Dispatches SQL to the **Java Query Guard** (`POST http://localhost:8081/query`), enforcing AST validation, PII blocking, and `LIMIT 1000`.
4. **`make_chart`**: Constructs visual chart specifications (bar, line, pie) for analytical breakdowns.

---

## Quick Start

### 1. Ensure the Java Guard is Running
```powershell
cd ../guard
mvn spring-boot:run
```
*(Runs on `http://localhost:8081`)*

### 2. Run the Command-Line Agent (CLI)
Ask any question directly from your terminal:

```powershell
cd ../agent
uv run --with-requirements requirements.txt python cli.py "What is our current MRR in USD?"
```

Or run interactive mode:
```powershell
uv run --with-requirements requirements.txt python cli.py
```

### 3. Start the FastAPI Server (Streaming SSE)
To serve the Next.js frontend or automated evaluators:

```powershell
uv run --with-requirements requirements.txt uvicorn app:app --port 8000 --reload
```
* **Streaming Endpoint:** `POST http://localhost:8000/chat` (Server-Sent Events)
* **Sync Endpoint:** `POST http://localhost:8000/chat/sync`
* **Health Check:** `GET http://localhost:8000/health`
