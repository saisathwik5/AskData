"""
generate_data.py
Generates 2,000 users, ~5,000 payments, and ~100,000 events over an 18-month window.
Fully deterministic using random.seed(42) and Faker.seed(42).
Outputs:
  - askdata_dump.sql (Batch INSERT statements ready for Supabase)
  - ground_truth_stats.json (Exact metrics to verify evals by hand)
"""

import json
import random
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from faker import Faker

# 1. Deterministic Seeding
SEED = 42
random.seed(SEED)
Faker.seed(SEED)
fake = Faker()

START_DATE = datetime(2024, 1, 1, 0, 0, 0)
END_DATE = datetime(2025, 6, 30, 23, 59, 59)
TOTAL_DAYS = (END_DATE - START_DATE).days

PLANS = {
    "starter": {"monthly": Decimal("29.00"), "weight": 55},
    "pro": {"monthly": Decimal("99.00"), "weight": 35},
    "enterprise": {"monthly": Decimal("499.00"), "weight": 10},
}
PLAN_CHOICES = list(PLANS.keys())
PLAN_WEIGHTS = [PLANS[p]["weight"] for p in PLAN_CHOICES]

EVENT_TYPES = [
    ("page_view", 40),
    ("dashboard_viewed", 25),
    ("report_exported", 15),
    ("query_executed", 15),
    ("settings_updated", 5),
]
EVENT_NAMES = [e[0] for e in EVENT_TYPES]
EVENT_WEIGHTS = [e[1] for e in EVENT_TYPES]

def random_date(start: datetime, end: datetime) -> datetime:
    delta = end - start
    random_seconds = random.randint(0, int(delta.total_seconds()))
    return start + timedelta(seconds=random_seconds)

def escape_sql(val):
    if val is None:
        return "NULL"
    if isinstance(val, bool):
        return "TRUE" if val else "FALSE"
    if isinstance(val, (int, float, Decimal)):
        return str(val)
    # String / JSON
    val_str = str(val).replace("'", "''")
    return f"'{val_str}'"

print("Generating synthetic data for AskData...")

# 2. Generate 2,000 Users
USERS_COUNT = 2000
users = []
test_user_ids = set()

for _ in range(USERS_COUNT):
    u_id = str(uuid.uuid4())
    is_test = random.random() < 0.04  # 4% test accounts
    if is_test:
        email = f"test_{fake.user_name()}@askdata.internal"
        test_user_ids.add(u_id)
    else:
        email = fake.unique.email()
    
    signup_dt = random_date(START_DATE, END_DATE - timedelta(days=60))
    country = None if random.random() < 0.05 else fake.country_code()
    initial_plan = random.choices(PLAN_CHOICES, weights=PLAN_WEIGHTS)[0]
    
    users.append({
        "id": u_id,
        "email": email,
        "full_name": fake.name(),
        "country": country,
        "signup_date": signup_dt,
        "plan": initial_plan,
        "is_test_account": is_test
    })

# 3. Generate Subscriptions & Payments
subscriptions = []
payments = []

for u in users:
    u_id = u["id"]
    signup = u["signup_date"]
    
    # 20% trial and churn immediately
    is_trial_churn = random.random() < 0.20
    
    if is_trial_churn:
        s_id = str(uuid.uuid4())
        trial_end = signup + timedelta(days=14)
        subscriptions.append({
            "id": s_id,
            "user_id": u_id,
            "plan": u["plan"],
            "status": "canceled",
            "start_date": signup,
            "end_date": trial_end,
            "trial_end_date": trial_end
        })
        continue  # No payments

    # Active or previously active subscriber
    # Currency: 85% USD, 15% EUR
    curr = "EUR" if random.random() < 0.15 else "USD"
    plan_cost = PLANS[u["plan"]]["monthly"]
    
    sub_start = signup
    trial_end = sub_start + timedelta(days=14)
    
    # Check if user cancelled
    will_cancel = random.random() < 0.30
    cancel_date = None
    if will_cancel:
        active_days = random.randint(30, 180)
        cancel_date = sub_start + timedelta(days=active_days)
        if cancel_date > END_DATE:
            cancel_date = None
            sub_status = "active"
        else:
            sub_status = "canceled"
    else:
        sub_status = "active"
        
    s_id = str(uuid.uuid4())
    subscriptions.append({
        "id": s_id,
        "user_id": u_id,
        "plan": u["plan"],
        "status": sub_status,
        "start_date": sub_start,
        "end_date": cancel_date,
        "trial_end_date": trial_end
    })
    
    # Generate monthly billing cycles
    cycle_dt = trial_end
    cutoff_dt = cancel_date if cancel_date else END_DATE
    
    while cycle_dt <= cutoff_dt:
        p_id = str(uuid.uuid4())
        # Trap: 8% failed payments, 4% refunded payments
        roll = random.random()
        if roll < 0.08:
            status = "failed"
            refunded = Decimal("0.00")
        elif roll < 0.12:
            status = "refunded"
            # Some partial, some full
            refunded = plan_cost if random.random() < 0.70 else plan_cost / 2
        else:
            status = "succeeded"
            refunded = Decimal("0.00")
            
        payments.append({
            "id": p_id,
            "user_id": u_id,
            "amount": plan_cost,
            "currency": curr,
            "status": status,
            "paid_at": cycle_dt,
            "refunded_amount": refunded
        })
        cycle_dt += timedelta(days=30)
        
    # Reactivation trap: 12% of canceled users come back after 60 days
    if will_cancel and cancel_date and (cancel_date + timedelta(days=90) < END_DATE):
        if random.random() < 0.12:
            reactivate_start = cancel_date + timedelta(days=random.randint(60, 90))
            react_id = str(uuid.uuid4())
            subscriptions.append({
                "id": react_id,
                "user_id": u_id,
                "plan": u["plan"],
                "status": "active",
                "start_date": reactivate_start,
                "end_date": None,
                "trial_end_date": None
            })
            # Add payments after reactivation
            r_cycle = reactivate_start
            while r_cycle <= END_DATE:
                payments.append({
                    "id": str(uuid.uuid4()),
                    "user_id": u_id,
                    "amount": plan_cost,
                    "currency": curr,
                    "status": "succeeded",
                    "paid_at": r_cycle,
                    "refunded_amount": Decimal("0.00")
                })
                r_cycle += timedelta(days=30)

# 4. Generate ~100,000 Events
TOTAL_EVENTS_TARGET = 100000
events = []
active_user_list = [u for u in users if u["id"] not in test_user_ids]

for _ in range(TOTAL_EVENTS_TARGET):
    # Events cluster around users
    u = random.choice(active_user_list if random.random() > 0.02 else users)
    ev_dt = random_date(u["signup_date"], END_DATE)
    ev_name = random.choices(EVENT_NAMES, weights=EVENT_WEIGHTS)[0]
    
    props = {
        "browser": random.choice(["Chrome", "Firefox", "Safari", "Edge"]),
        "platform": random.choice(["macOS", "Windows", "Linux", "iOS"]),
    }
    if ev_name == "query_executed":
        props["execution_ms"] = random.randint(12, 1400)
    elif ev_name == "report_exported":
        props["format"] = random.choice(["csv", "pdf", "xlsx"])
        
    events.append({
        "id": str(uuid.uuid4()),
        "user_id": u["id"],
        "event_name": ev_name,
        "occurred_at": ev_dt,
        "properties": json.dumps(props)
    })

print(f"Generated: {len(users)} users, {len(subscriptions)} subscriptions, {len(payments)} payments, {len(events)} events.")

# 5. Export to SQL dump
output_sql = "askdata_dump.sql"
with open(output_sql, "w", encoding="utf-8") as f:
    f.write("-- Synthetic Data Seed for AskData\n")
    f.write("BEGIN;\n\n")
    
    # Users
    for u in users:
        f.write(f"INSERT INTO users VALUES ({escape_sql(u['id'])}, {escape_sql(u['email'])}, {escape_sql(u['full_name'])}, {escape_sql(u['country'])}, '{u['signup_date'].isoformat()}', {escape_sql(u['plan'])}, {escape_sql(u['is_test_account'])});\n")
    
    # Subscriptions
    for s in subscriptions:
        f.write(f"INSERT INTO subscriptions VALUES ({escape_sql(s['id'])}, {escape_sql(s['user_id'])}, {escape_sql(s['plan'])}, {escape_sql(s['status'])}, '{s['start_date'].isoformat()}', {'NULL' if not s['end_date'] else f'\'{s[\"end_date\"].isoformat()}\''}, {'NULL' if not s['trial_end_date'] else f'\'{s[\"trial_end_date\"].isoformat()}\''});\n")
        
    # Payments
    for p in payments:
        f.write(f"INSERT INTO payments VALUES ({escape_sql(p['id'])}, {escape_sql(p['user_id'])}, {p['amount']}, {escape_sql(p['currency'])}, {escape_sql(p['status'])}, '{p['paid_at'].isoformat()}', {p['refunded_amount']});\n")

    # Events in batches of 1000
    for chunk in range(0, len(events), 1000):
        batch = events[chunk:chunk + 1000]
        vals = []
        for e in batch:
            vals.append(f"({escape_sql(e['id'])}, {escape_sql(e['user_id'])}, {escape_sql(e['event_name'])}, '{e['occurred_at'].isoformat()}', {escape_sql(e['properties'])})")
        f.write(f"INSERT INTO events VALUES {', '.join(vals)};\n")
        
    f.write("\nCOMMIT;\n")

# 6. Export Ground-Truth Metrics for Hand-Checking Evals
real_users_ids = {u["id"] for u in users if not u["is_test_account"]}

usd_succeeded = [p for p in payments if p["currency"] == "USD" and p["status"] == "succeeded" and p["user_id"] in real_users_ids]
eur_succeeded = [p for p in payments if p["currency"] == "EUR" and p["status"] == "succeeded" and p["user_id"] in real_users_ids]
total_usd_gross = sum(p["amount"] for p in usd_succeeded)
total_usd_refunds = sum(p["refunded_amount"] for p in usd_succeeded)
total_usd_net = total_usd_gross - total_usd_refunds

stats = {
    "total_users": len(users),
    "real_users": len(users) - len(test_user_ids),
    "test_users": len(test_user_ids),
    "total_payments": len(payments),
    "payments_succeeded": sum(1 for p in payments if p["status"] == "succeeded"),
    "payments_failed": sum(1 for p in payments if p["status"] == "failed"),
    "payments_refunded": sum(1 for p in payments if p["status"] == "refunded"),
    "total_usd_net_revenue_real_users": float(total_usd_net),
    "total_eur_gross_real_users": float(sum(p["amount"] for p in eur_succeeded)),
    "total_events": len(events),
}

with open("ground_truth_stats.json", "w") as f:
    json.dump(stats, f, indent=2)

print("Saved 'askdata_dump.sql' and 'ground_truth_stats.json'.")
