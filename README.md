# Behavioral Pattern Engine

A small, growing API of statistical/ML models for detecting behavioral
patterns in personal-development app data — starting with drift detection,
built toward sentiment, forecasting, clustering, churn, and CLV models.

Built as shared infrastructure: [The Reinvention Edit](#) is the first
client, not the only one. See `PROJECT_PLAN.md` (or the project plan doc)
for the full phased roadmap.

## Status

**Phase 0 — Foundation: done.** `/health` and `/drift/evaluate` are live,
tested, and deployable.

## Quickstart

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up your local environment
cp .env.example .env

# 3. Run tests
pytest tests/ -v

# 4. Lint
ruff check app tests

# 5. Run the server locally
uvicorn app.main:app --reload
```

Visit `http://localhost:8000/docs` for interactive API docs (auto-generated
by FastAPI from the route/schema definitions).

## API

All endpoints except `/health` require an `X-API-Key` header. Set valid
keys via the `API_KEYS` environment variable (comma-separated).

### `GET /health`
Returns `{"status": "ok"}`. No auth required — used for uptime checks.

### `POST /drift/evaluate`
Compares a user's recent behavioral entries (mood, task completion,
journaling) against their own rolling baseline. Returns a status of
`insufficient-data`, `steady`, `gentle-dip`, or `check-in`, plus the
per-signal breakdown.

Example request body:
```json
{
  "entries": [
    {
      "date": "2026-07-01",
      "mood": "Grounded",
      "tasks_completed": 2,
      "tasks_total": 3,
      "journal_length": 180
    }
  ],
  "reference_date": "2026-07-12"
}
```

Design notes:
- Compares each user only against their **own** history — never against
  other users.
- Uses a CUSUM-style cumulative deviation statistic on mood, which catches
  a sustained quiet decline that a single-day z-score would miss.
- Requires at least two of three signals (mood, completion, journaling) to
  dip together before returning `check-in`, to avoid flagging a single
  ordinary bad day.
- Stays at `insufficient-data` until there's enough baseline history
  (default: 10+ data points over 21 days) to know what's normal for that
  specific person.

## Deployment

This repo includes a `Procfile`, so it deploys cleanly to Railway or
Fly.io with minimal config:

**Railway**: connect the GitHub repo, set the `API_KEYS` environment
variable in the dashboard, deploy. Railway auto-detects the `Procfile`.

**Fly.io**: run `fly launch` in this directory, follow the prompts, then
`fly secrets set API_KEYS=your-real-key`.

Either way, confirm it's live with:
```bash
curl https://your-deployed-url/health
```

## Project structure

```
app/
  main.py           # FastAPI app entry point
  api/routes/        # HTTP endpoints
  models/            # The actual ML/statistics logic, one module per model
  schemas/            # Pydantic request/response models
  core/               # Config and auth
tests/                # pytest suite
.github/workflows/    # CI: lint + test on every push
```

## Roadmap

See the project plan for the full seven-model roadmap (drift, sentiment,
forecasting, clustering, churn, CLV, topic modeling) and integration
milestones with The Reinvention Edit. Next up: **Model 2, sentiment
classification** on journal entries.
