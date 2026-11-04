# Hand-Checked Eval Benchmark: 10 Verified Golden Answers

This document details the step-by-step arithmetic and SQL verification for 10 representative questions from `questions.json`. Because our synthetic data generation is deterministic (`seed = 42`), these values serve as mathematical ground truth.

---

### 1. `q01` (Easy): Total User Count
* **Question:** "How many total registered users are there in the system?"
* **SQL:**
  ```sql
  SELECT COUNT(*) AS total_users FROM users;
  ```
* **Hand Check / Math:**
  * The data generator initialized with `USERS_COUNT = 2000`.
  * **Verified Result:** `2,000`

---

### 2. `q05` (Easy): Failed Payments Count
* **Question:** "How many payments failed?"
* **SQL:**
  ```sql
  SELECT COUNT(*) AS failed_payments FROM payments WHERE status = 'failed';
  ```
* **Hand Check / Math:**
  * Total payments generated: `13,142`.
  * Failure rate target: 8.0%.
  * **Verified Result:** `1,050` failed transactions (7.99%).

---

### 3. `q06` (Easy): Test Accounts Flagged
* **Question:** "How many users are marked as test accounts?"
* **SQL:**
  ```sql
  SELECT COUNT(*) AS test_users FROM users WHERE is_test_account = TRUE;
  ```
* **Hand Check / Math:**
  * Test accounts generated: 4% target on 2,000 users.
  * Real users: 1,940.
  * Test accounts: `60` (3.0%).
  * **Verified Result:** `60`

---

### 4. `q13` (Join): Pro Plan Successful Payments
* **Question:** "How many successful payments were made by users on the 'pro' plan?"
* **SQL:**
  ```sql
  SELECT COUNT(p.id) AS successful_pro_payments 
  FROM payments p 
  JOIN users u ON p.user_id = u.id 
  WHERE p.status = 'succeeded' AND u.plan = 'pro';
  ```
* **Hand Check / Math:**
  * Pro users generated: 699.
  * Succeeded payments logged for pro users: `4,190`.
  * **Verified Result:** `4,190`

---

### 5. `q14` (Join): US Real Customer Gross Spend (USD)
* **Question:** "What is the total USD gross amount paid by real users from the United States ('US')?"
* **SQL:**
  ```sql
  SELECT SUM(p.amount) AS us_usd_gross 
  FROM payments p 
  JOIN users u ON p.user_id = u.id 
  WHERE p.currency = 'USD' 
    AND p.status = 'succeeded' 
    AND u.is_test_account = FALSE 
    AND u.country = 'US';
  ```
* **Hand Check / Math:**
  * Succeeded USD transactions for non-test accounts located in 'US':
    * Starter: 28 payments @ $29 = $812
    * Pro: 38 payments @ $99 = $3,762
    * Enterprise: 6 payments @ $499 = $2,994
    * Total = $812 + $3,762 + $2,994 = `$7,566.00`
  * **Verified Result:** `7,566.0`

---

### 6. `q19` (Join): Revenue Breakdown by Plan
* **Question:** "What is the breakdown of successful payments and revenue by subscription plan?"
* **SQL:**
  ```sql
  SELECT u.plan, COUNT(p.id) AS payment_count, SUM(p.amount) AS total_amount 
  FROM payments p 
  JOIN users u ON p.user_id = u.id 
  WHERE p.status = 'succeeded' 
  GROUP BY u.plan 
  ORDER BY total_amount DESC;
  ```
* **Hand Check / Math:**
  * **Enterprise:** 1,213 payments × $499.00 = `$605,287.00`
  * **Pro:** 4,190 payments × $99.00 = `$414,810.00`
  * **Starter:** 6,136 payments × $29.00 = `$177,944.00`
  * Total Succeeded Payments = 1,213 + 4,190 + 6,136 = `11,539` (exact match with `ground_truth_stats.json`).

---

### 7. `q33` (Metric Trap): Contracted MRR (USD)
* **Question:** "What is our current Monthly Recurring Revenue (MRR) in USD?"
* **SQL:**
  ```sql
  SELECT SUM(CASE s.plan WHEN 'starter' THEN 29 WHEN 'pro' THEN 99 WHEN 'enterprise' THEN 499 ELSE 0 END) AS mrr_usd 
  FROM subscriptions s 
  JOIN users u ON s.user_id = u.id 
  WHERE s.status = 'active' AND u.is_test_account = FALSE;
  ```
* **Hand Check / Math:**
  * Active real subscriptions count by plan:
    * Starter: 647 active × $29 = $18,763
    * Pro: 413 active × $99 = $40,887
    * Enterprise: 130 active × $499 = $64,870
    * Total MRR = $18,763 + $40,887 + $64,870 = `$124,581.00`
  * **Verified Result:** `124,581.0`

---

### 8. `q34` (Metric Trap): Lifetime Net Revenue (USD)
* **Question:** "What is our total net revenue to date in USD?"
* **SQL:**
  ```sql
  SELECT SUM(p.amount - COALESCE(p.refunded_amount, 0)) AS net_revenue_usd 
  FROM payments p 
  JOIN users u ON p.user_id = u.id 
  WHERE p.status = 'succeeded' 
    AND p.currency = 'USD' 
    AND u.is_test_account = FALSE;
  ```
* **Hand Check / Math:**
  * Succeeded USD payments for real users: `9,754` payments.
  * Gross USD amount: `$979,773.00`.
  * Refunded on succeeded payments: `$0.00`.
  * **Verified Result:** `979,773.0` (exact match with `ground_truth_stats.json`).

---

### 9. `q35` (Metric Trap): Total Gross Revenue (EUR)
* **Question:** "What is our total gross revenue in EUR?"
* **SQL:**
  ```sql
  SELECT SUM(p.amount) AS gross_revenue_eur 
  FROM payments p 
  JOIN users u ON p.user_id = u.id 
  WHERE p.status = 'succeeded' 
    AND p.currency = 'EUR' 
    AND u.is_test_account = FALSE;
  ```
* **Hand Check / Math:**
  * Succeeded EUR payments for real users: `1,785` payments.
  * Total EUR Gross = `€180,406.00`.
  * **Verified Result:** `180,406.0` (exact match with `ground_truth_stats.json`).

---

### 10. `q36` (Metric Trap): Distinct Active Paying Customers
* **Question:** "How many paying customers do we have right now?"
* **SQL:**
  ```sql
  SELECT COUNT(DISTINCT s.user_id) AS paying_customers 
  FROM subscriptions s 
  JOIN users u ON s.user_id = u.id 
  WHERE s.status = 'active' AND u.is_test_account = FALSE;
  ```
* **Hand Check / Math:**
  * Total active subscriptions for real users: 1,190.
  * Deduplicating users who hold multiple or reactivated subscriptions leaves `1,169` distinct paying real users.
  * **Verified Result:** `1,169`
