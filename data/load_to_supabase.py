"""
load_to_supabase.py
Streams schema.sql and askdata_dump.sql directly to Supabase with live progress reporting.
"""

import os
import sys
from pathlib import Path
import psycopg2

def find_env_url():
    """Look for SUPABASE_DB_URL in environment or .env files."""
    if "SUPABASE_DB_URL" in os.environ and os.environ["SUPABASE_DB_URL"]:
        return os.environ["SUPABASE_DB_URL"]

    # Check root .env and current dir .env
    possible_paths = [
        Path(__file__).parent / ".env",
        Path(__file__).parent.parent / ".env",
    ]
    for p in possible_paths:
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("SUPABASE_DB_URL=") and not line.startswith("#"):
                        val = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if val and "YOUR-PASSWORD" not in val and "YOUR-PROJECT-REF" not in val:
                            return val
    return None

def main():
    db_url = find_env_url()
    if not db_url:
        print("\n[!] Error: SUPABASE_DB_URL not found or still contains placeholders.")
        print("    Please set SUPABASE_DB_URL in your root .env file, for example:")
        print("    SUPABASE_DB_URL=\"postgresql://postgres.xxx:[PASSWORD]@aws-0-xxx.pooler.supabase.com:6543/postgres\"\n")
        sys.exit(1)

    print("\n--- Connecting to Supabase Database ---")
    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = False
        cursor = conn.cursor()
        print("[✓] Connected successfully to PostgreSQL database!")
    except Exception as e:
        print(f"[!] Database connection failed: {e}")
        sys.exit(1)

    data_dir = Path(__file__).parent
    schema_file = data_dir / "schema.sql"
    dump_file = data_dir / "askdata_dump.sql"

    # Step 1: Execute schema.sql if present
    if schema_file.exists():
        print(f"\n[1/2] Applying {schema_file.name} (creating tables & indexes)...")
        with open(schema_file, "r", encoding="utf-8") as f:
            schema_sql = f.read()
        try:
            cursor.execute(schema_sql)
            conn.commit()
            print("[✓] Schema applied successfully.")
        except Exception as e:
            conn.rollback()
            print(f"[!] Error applying schema: {e}")
            cursor.close()
            conn.close()
            sys.exit(1)
    else:
        print(f"[i] {schema_file.name} not found, skipping schema creation.")

    # Step 2: Stream askdata_dump.sql
    if not dump_file.exists():
        print(f"\n[!] Dump file {dump_file.name} not found! Run generate_data.py first.")
        cursor.close()
        conn.close()
        sys.exit(1)

    print(f"\n[2/2] Ingesting {dump_file.name} (~20MB, 100k+ rows)...")
    try:
        statement_count = 0
        with open(dump_file, "r", encoding="utf-8") as f:
            current_stmt = []
            for line in f:
                stripped = line.strip()
                if not stripped or stripped.startswith("--"):
                    continue
                current_stmt.append(line)
                if stripped.endswith(";"):
                    stmt = "".join(current_stmt)
                    cursor.execute(stmt)
                    current_stmt = []
                    statement_count += 1
                    if statement_count % 2000 == 0:
                        print(f"    ... processed {statement_count} statements")

        conn.commit()
        print(f"[✓] Data ingestion complete! Total statements processed: {statement_count}")
    except Exception as e:
        conn.rollback()
        print(f"[!] Ingestion failed: {e}")
        cursor.close()
        conn.close()
        sys.exit(1)

    # Step 3: Run quick count verification
    print("\n--- Verifying Row Counts in Supabase ---")
    cursor.execute("""
        SELECT 
          (SELECT COUNT(*) FROM users) AS users,
          (SELECT COUNT(*) FROM subscriptions) AS subscriptions,
          (SELECT COUNT(*) FROM payments) AS payments,
          (SELECT COUNT(*) FROM events) AS events;
    """)
    row = cursor.fetchone()
    print(f"Users:         {row[0]:,}")
    print(f"Subscriptions: {row[1]:,}")
    print(f"Payments:      {row[2]:,}")
    print(f"Events:        {row[3]:,}")
    print("\n[✓] Category 1 Done!")

    cursor.close()
    conn.close()

if __name__ == "__main__":
    main()
