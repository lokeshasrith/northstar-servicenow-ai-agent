# Northstar — ServiceNow IT Incident AI Agent

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/API-FastAPI-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/UI-React%20%2B%20TypeScript-3178C6?logo=typescript&logoColor=white)

A local, human-supervised incident triage demo with a React operations dashboard, FastAPI orchestration API, PostgreSQL persistence, a ServiceNow adapter, source-attributed knowledge retrieval, deterministic safety policy, approval-gated actions, and auditable decisions.

Northstar demonstrates an end-to-end incident workflow: classify and prioritize a ticket, retrieve cited runbooks, explain the decision, request approval for risky actions, and retain an audit trail. The default setup is a safe local simulation; no external systems are changed.

## Portfolio summary

**Resume bullet:** Built a human-in-the-loop ServiceNow incident triage platform with a React/TypeScript dashboard and FastAPI backend; implemented source-attributed runbook retrieval, deterministic severity and escalation policies, approval-gated remediation workflows, auditable incident timelines, and a mock/real ServiceNow Table API adapter.

**Project highlights:** 10 automated backend checks; 11 hand-labeled evaluation examples; Docker Compose setup for PostgreSQL and the dashboard; API reference generated from FastAPI. The included evaluation is a small deterministic demo, not a claim of production model performance. See [evaluation results and caveats](docs/evaluation-report.md).

## Run the full stack

Prerequisites: Docker Desktop with Docker Compose. From this directory:

```powershell
Copy-Item .env.example .env
# Change POSTGRES_PASSWORD before using the stack beyond a local demo.
docker compose up --build
```

Open <http://localhost:5173> for the dashboard, <http://localhost:8000/docs> for the OpenAPI reference, and <http://localhost:8000/api/health> for service and database health. The API seeds eight example incidents the first time its database is empty. Compose stores PostgreSQL data in the `postgres_data` volume.

For a local backend without Docker/PostgreSQL, install `backend/requirements.txt` and run `uvicorn app.main:app --reload` from `backend`; the default local database is SQLite. Run the scenario demonstration with `python -m app.simulation` from `backend`.

## Configuration

Copy `.env.example` to `.env`. Defaults select the mock LLM and mock ServiceNow, so no credentials are needed for the demo.

- `CONFIDENCE_AUTO_THRESHOLD` and `CONFIDENCE_INVESTIGATE_THRESHOLD` tune the decision gates.
- `LLM_PROVIDER=mock|openai`; the OpenAI adapter needs `OPENAI_API_KEY` and optionally `OPENAI_MODEL`. LLM output remains a suggestion validated by deterministic policy.
- `SERVICENOW_MODE=mock|real`; real mode needs the instance URL, username, and password. Use a dedicated least-privilege developer instance account and keep credentials outside source control.
- `DASHBOARD_ADMIN_KEY` enables write access with an API key; `DASHBOARD_VIEWER_KEY` is read-only. The development default leaves authentication off; configure keys before exposing the API.
- Compose uses PostgreSQL. `DATABASE_URL` can be set for direct backend operation, otherwise local development uses SQLite.

## What works

- API endpoints: `POST /api/incidents/analyze`, create/list/get/process/escalate incidents, approval and action requests, timeline/audit, knowledge search, ServiceNow Table API proxy plus `POST /api/servicenow/sync`, evaluations, action registry, and health.
- Persistent local incident records and append-only audit events. No API endpoint edits or deletes audit rows.
- Deterministic category and impact/urgency priority assessment; low confidence, ambiguity, critical priority, security language, or provider/knowledge failure routes to a human.
- Source-attributed cosine retrieval over curated runbooks. Documents are local JSON and cited by their stable KB ID and source label; retrieved text is evidence, not an executable instruction.
- Explicit action registry with risk level, required permissions, input/output schemas, validation description, and audit entries. Read-only actions are simulated. Medium/high risk changes wait for a named approver.
- Local mock ServiceNow adapter and optional real Table API adapter for incidents, assignment, work notes/comments, and knowledge queries.
- Dashboard queue comes from the API and opens details for original description, decision explanation, confidence, retrieved sources, actions, escalation notes, timeline, and audit events.
- Basic request throttling and optional API-key roles. The UI never displays private chain-of-thought.

## Safety and demo limits

This is a runnable demonstration, not a production-approved autonomous remediation platform. The mock action executor does not change external systems; its simulated verification and “Resolved” status only demonstrate the workflow. It must not be interpreted as proof that a real incident is fixed. Even with `SERVICENOW_MODE=real`, this build will not close tickets because real action and verification connectors are not configured; it sends a human escalation instead. Real action connectors, enterprise identity integration, migrations, monitoring, and operational approval workflows need deployment-specific implementation and review. ServiceNow sync failures are durably marked on incident records and can be retried through the API; retry scheduling is operator-triggered. The local mock classifier is deterministic and should be replaced/evaluated against organization-specific data before use. Human approval is required for medium/high risk registry actions. Security incidents and P1 incidents are escalated.

Knowledge retrieval uses a transparent local normalized bag-of-words cosine score, not a hosted embedding model. It gives a working, inspectable retrieval pipeline with no external embedding credentials; an embedding-backed index can replace it behind `KnowledgeBase` as a deployment choice.

## Test and evaluation

From `backend` (install test dependencies with `pip install -r requirements-dev.txt`):

```powershell
python -m pytest -q
python -m app.simulation
```

`GET /api/evaluation` computes classification, priority, escalation accuracy, confidence Brier score, false-autonomous-resolution rate, and escalation rate over `knowledge/sample_incidents/evaluation.json`. Results and caveats are in [docs/evaluation-report.md](docs/evaluation-report.md). Resolution-time measurement is unavailable in the static labeled dataset. Never treat the zero false-autonomous count on 11 examples as a production safety guarantee.

## Layout

- `backend/app/ai`, `agents`, `policies`, `actions`: provider, explicit orchestration, gates, and action registry.
- `backend/app/integrations/servicenow`: mock and real adapters.
- `backend/app/knowledge`: local source-attributed retrieval.
- `backend/app/models`, `database`, `api`: persistence and typed HTTP contracts.
- `frontend/src`: React/TypeScript dashboard.
- `knowledge/runbooks`: curated demo troubleshooting documents.
- `knowledge/sample_incidents`: seed queue and labeled evaluation cases.
- `docs/architecture.md`: component and trust-boundary diagram.
