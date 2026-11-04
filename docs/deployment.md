# Production Deployment Guide: AskData

This guide details containerizing and deploying the AskData Text-to-SQL architecture to production cloud environments (AWS / GCP / Vercel).

---

## 1. Local Containerized Run (Docker Compose)

The fastest way to run the entire system locally or in staging:

```powershell
# 1. Ensure your .env has your SUPABASE_* and GEMINI_API_KEY credentials
cd AskData

# 2. Build and launch both services
docker-compose up --build
```

- **Java Query Guard:** `http://localhost:8081` (AST validation & database execution)
- **Python Agent & Web UI:** `http://localhost:8000` (FastAPI streaming endpoint + browser chat UI)

Verify health checks:
```powershell
curl http://localhost:8081/health
curl http://localhost:8000/health
```

---

## 2. Cloud Architecture (Defense-in-Depth)

```
[Users / Next.js on Vercel]
             │
             ▼ (HTTPS / SSE)
[Python Agent API (AWS ECS Fargate / App Runner)]
             │
             ▼ (Private VPC HTTP)
[Java Query Guard (AWS ECS Fargate)]
             │ (AST Verified SELECTs only)
             ▼ (SSL / Port 6543)
[Supabase PostgreSQL (Read-Only Views + RLS + 5s Timeout)]
```

### Key Security Guardrails:
1. **Network Isolation:** In production, place the Java Query Guard in a private subnet. Only the Python Agent has network access to port 8081.
2. **Database Permissions:** The database connection uses the `askdata_readonly` role with `statement_timeout = 5000ms`, granting SELECT access **only** on sanitized views (`v_users`, `v_subscriptions`, `v_payments`, `v_events`). Direct table access is completely revoked.
3. **AST Inspection:** Even if the LLM attempts SQL injection, comment-based evasion, CTE subqueries, or blocked columns (`email`, `full_name`), JSqlParser intercepts and terminates the query before database transmission.

---

## 3. Deploying to AWS App Runner / ECS

### Step A: Push Images to Amazon Elastic Container Registry (ECR)
```powershell
# Authenticate Docker to AWS ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <aws_account_id>.dkr.ecr.us-east-1.amazonaws.com

# Build & Push Guard
docker build -t askdata-guard ./guard
docker tag askdata-guard:latest <aws_account_id>.dkr.ecr.us-east-1.amazonaws.com/askdata-guard:latest
docker push <aws_account_id>.dkr.ecr.us-east-1.amazonaws.com/askdata-guard:latest

# Build & Push Agent
docker build -t askdata-agent -f agent/Dockerfile .
docker tag askdata-agent:latest <aws_account_id>.dkr.ecr.us-east-1.amazonaws.com/askdata-agent:latest
docker push <aws_account_id>.dkr.ecr.us-east-1.amazonaws.com/askdata-agent:latest
```

### Step B: Deploy Services
- **Option 1 (AWS App Runner):** Point App Runner directly to your ECR images with automatic autoscaling (1 to 10 instances). Set environment variables from AWS Secrets Manager.
- **Option 2 (ECS Fargate):** Deploy a task definition with two containers (`guard` and `agent`) sharing a localhost network bridge.

---

## 4. Deploying Web UI to Vercel
To deploy the Next.js frontend to Vercel:
```powershell
cd web
npm install
vercel
```
Set the environment variable:
- `NEXT_PUBLIC_API_URL`: Your deployed Python Agent API URL (e.g. `https://api.askdata.yourcompany.com`).
