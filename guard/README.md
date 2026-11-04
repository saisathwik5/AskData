# /guard: Java Query Guard Service

The Java Query Guard is the secondary enforcement layer in AskData's defense-in-depth architecture. It acts as a secure reverse-proxy between the Python agent and the database, performing Abstract Syntax Tree (AST) inspection with JSqlParser before any SQL reaches PostgreSQL.

---

## Defense-in-Depth Architecture

```
[User / Agent] ──(SQL)──> [Java Guard Service] ──(AST Checked)──> [Supabase Read-Only]
                                │                                           │
                                ├─ Blocks non-SELECT                        ├─ Role: askdata_readonly
                                ├─ Blocks PII (email, full_name)            ├─ Access to safe views only
                                ├─ Blocks dangerous functions (pg_sleep)    ├─ 5s statement_timeout
                                ├─ Clamps/Injects LIMIT 1000                └─ RLS enabled
                                └─ Writes query_audit_logs
```

---

## Core Security Rules Enforced

1. **Exactly One Statement:** Rejects multiple statements separated by semicolons (e.g. `SELECT 1; DROP TABLE users;`) and comment-based splitting.
2. **SELECT Only:** Rejects all `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`, and administrative commands.
3. **Allowed Views & Relations Only:** Only allows queries targeting approved analytical views (`v_users`, `v_subscriptions`, `v_payments`, `v_events`). Any reference to system schemas (`pg_catalog.*`, `information_schema.*`) is blocked.
4. **No Blocked Columns:** Rejects queries referencing PII columns (`email`, `full_name`, `password`, `secret`, `token`) in `SELECT`, `WHERE`, `JOIN`, `ORDER BY`, `GROUP BY`, subqueries, or CTEs.
5. **Prohibit Wildcard Star on Base User Table:** Blocks `SELECT * FROM users`. Users must query the safe view `v_users` or list explicit non-sensitive columns.
6. **Block Dangerous Functions:** Rejects DOS functions (`pg_sleep`), file access (`pg_read_file`), and process killers (`pg_terminate_backend`).
7. **Enforce Row Limit:** Injects `LIMIT 1000` if absent, and clamps any requested limit exceeding 1,000 down to 1,000.
8. **Audit Logging:** Every query (allowed or blocked) is logged to `query_audit_logs` with timestamps, execution duration, row counts, and rejection reasons.

---

## API Specification

### `POST /query`
**Request:**
```json
{
  "sql": "SELECT country, count(*) FROM v_users GROUP BY country",
  "userId": "analyst-01",
  "question": "Show user count by country"
}
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "message": "Query executed successfully",
  "columns": ["country", "count"],
  "rows": [
    {"country": "US", "count": 142},
    {"country": "CA", "count": 28}
  ],
  "rowCount": 2,
  "executionTimeMs": 35,
  "executedSql": "SELECT country, count(*) FROM v_users GROUP BY country LIMIT 1000"
}
```

**Security Violation Response (400 Bad Request):**
```json
{
  "success": false,
  "errorCode": "SECURITY_VIOLATION",
  "message": "Column 'email' is blocked for privacy and compliance reasons.",
  "executedSql": "SELECT email FROM users"
}
```

---

## Running the Guard & Tests

### Run the 35+ Security Attack Tests
```bash
mvn test
```

### Run the Spring Boot Application
```bash
mvn spring-boot:run
```
The guard will start on `http://localhost:8080`.
