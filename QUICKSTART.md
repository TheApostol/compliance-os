# ⚡ ComplianceOS — Quickstart

## Prerequisites

- Docker Desktop installed and running
- Make installed (Mac: `brew install make`)
- An NVIDIA API key (free at https://build.nvidia.com — takes 2 minutes)

---

## Step 1 — Configure (1 min)

```bash
cd complianceos
cp .env.example .env
```

Now open `.env` and add your NVIDIA API key:

```
NVIDIA_API_KEY=nvapi-XXXXXXXXXXXXXXXX
```

**⚠️ Never commit `.env` to git. Never paste your key in chat.**

---

## Step 2 — Launch (2 min)

```bash
make up
```

This will:
- Build the backend Docker image
- Pull Postgres, Qdrant, Redis images
- Build the frontend
- Start everything in the background

Watch the boot logs:

```bash
make logs
```

Wait for `Application startup complete` on the backend.

---

## Step 3 — Verify (1 min)

Open these URLs:

| URL | What it shows |
|---|---|
| http://localhost:3000 | Frontend dashboard with Compliance Copilot |
| http://localhost:8000/docs | Swagger API docs (interactive) |
| http://localhost:8000/api/v1/health | Should return `{"status":"ok"}` |
| http://localhost:8000/api/v1/meta/models | List of routed AI models |
| http://localhost:6333/dashboard | Qdrant UI |

---

## Step 4 — Validate AI (1 min)

```bash
make seed       # creates demo tenant + 3 regulations (AR/BR)
make benchmark  # tests all 5 modules with your NVIDIA key
```

Expected output:
```
[M1] Regulatory parsing...   ✓ OK    model=meta/llama-3.3-70b-instruct  latency=21000ms
[M2] Compliance Copilot...   ✓ OK    model=moonshotai/kimi-k2-instruct  latency=30000ms
[M3] KYC screening...        ✓ OK    model=nvidia/llama-3.3-nemotron-super-49b-v1  ...
[M4] Transaction monitoring  ✓ OK    ...
[M5] Self-audit              ✓ OK    ...

Modules passing: 5/5
```

If any module fails, check `make logs` for the error.

---

## Day 2 — Use Claude Code from here

This repo has `CLAUDE.md` at the root. Claude Code will read it and have full context.

```bash
claude
```

Then say something like:

> *"Implementá el módulo M6 Evidence usando OCR. Mirá `backend/app/modules/evidence/engine.py` para el design sketch."*

or

> *"Corré `make benchmark` y arreglá lo que falle. Actualizá `CLAUDE.md` con los resultados."*

---

## Common commands

```bash
make help        # show all commands
make up          # start
make down        # stop
make logs        # follow logs
make restart     # restart all containers
make ps          # show running containers
make clean       # WIPES all data (volumes too)

make seed        # load demo data
make benchmark   # run AI benchmark
make test        # run pytest

make backend-shell    # bash inside backend container
make db-shell         # psql into the database
```

---

## Troubleshooting

### "NVIDIA_API_KEY not configured"
Edit `.env`, add your key (starts with `nvapi-`), then `make restart`.

### Backend container won't start
```bash
make logs
```
Most likely: missing `.env` or invalid format. Check `.env.example` for reference.

### "Address already in use" on port 3000/8000/5432
Stop other services using those ports, or edit `docker-compose.yml` to change them.

### Frontend shows "Failed to fetch"
Backend isn't ready yet. Wait 10s and retry. If persistent: `make logs` → look for backend errors.

### "ModuleNotFoundError: pydantic_settings" or similar
Rebuild the backend image:
```bash
docker compose build --no-cache backend
make up
```

---

## Architecture cheatsheet

```
Frontend (3000)  ──→  Backend (8000)  ──→  AI Orchestrator  ──→  NVIDIA NIM
                          │                       │
                          ▼                       ▼
                   Postgres (5432)         Audit log (hash chain)
                   Qdrant (6333)
                   Redis (6379)
```

All AI calls go through `app/services/ai_orchestrator.py`. That's the single source of truth for model selection, fallbacks, rate limiting, and audit.

---

🚀 **Start with `make up` and you're live in 2 minutes.**
