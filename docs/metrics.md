# AskData: Metric Definitions

This document defines the strict business rules and SQL criteria for core SaaS metrics in AskData. These definitions are binding across all SQL generation, validation, and evaluation benchmarks.

---

### Monthly Recurring Revenue (MRR)
MRR is the normalized monthly contracted subscription revenue from all active, paying subscriptions held by real customers as of the measurement date. It is calculated by summing the plan amounts (`starter` = $29, `pro` = $99, `enterprise` = $499) for all subscriptions with `status = 'active'`. It **strictly excludes** internal/test accounts (`is_test_account = TRUE`), trial subscriptions (`status = 'trialing'` or within `trial_end_date`), and canceled subscriptions (`status = 'canceled'`). One-time refunds and payment processing failures do not alter contracted MRR (they affect cash revenue instead). Multi-currency subscriptions must be reported partitioned by currency (`USD` vs `EUR`) or converted using a defined FX rate.

---

### Customer Churn Rate
Monthly Customer Churn Rate is defined as the number of distinct real customers whose subscriptions entered `status = 'canceled'` (with `end_date` falling within that calendar month), divided by the total number of active subscribers at the start of that calendar month, expressed as a percentage. Internal/test accounts (`is_test_account = TRUE`) are strictly excluded. When a customer cancels and later reactivates with a new subscription, their initial cancellation is counted in the month it occurred, and their reactivation is treated as a new active subscription in the return month; historical churn is not retroactively erased.

---

### Active User (WAU / MAU)
An Active User is defined as any distinct non-test customer (`is_test_account = FALSE`) who has logged at least one intentional core product interaction event (`event_name IN ('dashboard_viewed', 'query_executed', 'report_exported')`) within a rolling 30-day window (Monthly Active User - MAU) or 7-day window (Weekly Active User - WAU). Passive system-level events (`page_view`, `settings_updated`) and background jobs are excluded from core engagement calculations unless explicitly requested.

---

### Net Revenue vs Gross Revenue
Gross Revenue is the total sum of all settled payments (`status = 'succeeded'`) from non-test accounts (`is_test_account = FALSE`) within a specified time window, reported separately by currency. Net Revenue is defined as Gross Revenue minus all refunded amounts (`refunded_amount`) on payments within that same period (`Net Revenue = SUM(amount - COALESCE(refunded_amount, 0))` where `status = 'succeeded'`). Failed payments (`status = 'failed'`), pending transactions, and test account charges (`is_test_account = TRUE`) are strictly excluded from both gross and net revenue.
