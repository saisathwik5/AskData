# AskData Analytical Views Schema Dictionary

> **Auto-generated and hand-verified database level context for AI agent.**

### View: `v_users`
Safe view of all registered SaaS user accounts. Sensitive PII columns ('email' and 'full_name') are intentionally excluded for compliance and privacy.

| Column | Type | Business Description | Sample Values |
| :--- | :--- | :--- | :--- |
| `id` | `VARCHAR(36)` | Unique identifier (UUID) for each registered user. Serves as primary key. | `335a5132-cfaa-4919-b6b8-8a71c958f3cb` |
| `country` | `VARCHAR(2)` | Two-letter ISO 3166-1 alpha-2 country code. Can be NULL if not provided during registration. | `US, CA, DE, NULL` |
| `signup_date` | `TIMESTAMPTZ` | Timestamp with timezone recording when the user registered. | `2024-01-15T10:30:00Z` |
| `plan` | `VARCHAR(50)` | The initial plan selected at registration: 'starter', 'pro', or 'enterprise'. | `starter, pro, enterprise` |
| `is_test_account` | `BOOLEAN` | **CRITICAL:** Boolean flag marking internal test/staging accounts. MUST be filtered out (`is_test_account = FALSE`) for all business metrics, revenue, and active user analytics. | `false, true` |

---

### View: `v_subscriptions`
Customer recurring subscription contracts, lifecycle statuses, and trial periods.

| Column | Type | Business Description | Sample Values |
| :--- | :--- | :--- | :--- |
| `id` | `VARCHAR(36)` | Unique subscription contract identifier (UUID). | `s-1001` |
| `user_id` | `VARCHAR(36)` | Foreign key linking subscription to v_users.id. | `335a5132-cfaa-4919-b6b8-8a71c958f3cb` |
| `plan` | `VARCHAR(50)` | Contract tier: 'starter' ($29/mo), 'pro' ($99/mo), 'enterprise' ($499/mo). Used to compute MRR. | `starter, pro, enterprise` |
| `status` | `VARCHAR(50)` | Current lifecycle status: 'active' (currently paying), 'canceled' (churned), or 'trialing' (free trial). | `active, canceled, trialing` |
| `start_date` | `TIMESTAMPTZ` | Start timestamp of the subscription contract. | `2024-02-01T00:00:00Z` |
| `end_date` | `TIMESTAMPTZ` | Cancellation timestamp for churned subscriptions. NULL for actively running subscriptions. | `NULL, 2024-08-01T00:00:00Z` |
| `trial_end_date` | `TIMESTAMPTZ` | Timestamp when the 14-day free trial concluded. | `2024-02-15T00:00:00Z` |

---

### View: `v_payments`
Financial ledger of all billed credit card transactions, currencies, charges, and refunds.

| Column | Type | Business Description | Sample Values |
| :--- | :--- | :--- | :--- |
| `id` | `VARCHAR(36)` | Unique transaction charge identifier (UUID). | `p-501` |
| `user_id` | `VARCHAR(36)` | Foreign key linking payment to v_users.id. | `335a5132-cfaa-4919-b6b8-8a71c958f3cb` |
| `amount` | `NUMERIC(10,2)` | Gross billed transaction amount. Never use floating point. | `29.00, 99.00, 499.00` |
| `currency` | `VARCHAR(3)` | **CRITICAL:** Multi-currency column ('USD' vs 'EUR'). NEVER sum amounts without filtering or grouping by currency. | `USD, EUR` |
| `status` | `VARCHAR(50)` | Payment outcome: 'succeeded' (collected revenue), 'failed' (declined), or 'refunded'. | `succeeded, failed, refunded` |
| `paid_at` | `TIMESTAMPTZ` | Timestamp when the payment was settled. | `2024-04-10T12:00:00Z` |
| `refunded_amount` | `NUMERIC(10,2)` | Amount refunded to customer. Net Revenue = SUM(amount - COALESCE(refunded_amount, 0)) for succeeded charges. | `0.00, 99.00` |

---

### View: `v_events`
Product telemetry and behavioral event stream tracking user engagement (100,000 rows).

| Column | Type | Business Description | Sample Values |
| :--- | :--- | :--- | :--- |
| `id` | `VARCHAR(36)` | Unique event tracking ID. | `e-9001` |
| `user_id` | `VARCHAR(36)` | Foreign key linking event to v_users.id. | `335a5132-cfaa-4919-b6b8-8a71c958f3cb` |
| `event_name` | `VARCHAR(100)` | Intentional actions: 'dashboard_viewed', 'query_executed', 'report_exported'. Passive actions: 'page_view', 'settings_updated'. | `query_executed, dashboard_viewed` |
| `occurred_at` | `TIMESTAMPTZ` | Timestamp when the user took the action. | `2024-05-18T22:15:00Z` |
| `properties` | `JSONB` | JSON metadata. For 'query_executed', contains execution_ms. For 'report_exported', contains format. | `{"browser": "Chrome", "execution_ms": 82}` |
