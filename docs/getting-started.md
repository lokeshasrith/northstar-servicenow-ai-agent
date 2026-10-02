# Northstar getting started

Northstar is a human-supervised incident triage demo. You can try the hosted public demo, deploy a separate copy from GitHub, or run it locally. The public demo uses mock AI and mock ServiceNow adapters; it does not connect to or repair real systems.

## Try the hosted demo

Open [Northstar Incident Operations](https://northstar-incident-agent.onrender.com/). On the Overview page:

1. Select **Try your incident**.
2. Choose **Recovered** or **Still failing** to see the example outcomes, or enter a fictional issue of your own.
3. Select **Create and run AI test**. Northstar records the incident, classifies and prioritizes it, searches the included runbooks, and processes the simulated workflow.
4. Review the opened incident detail for its decision, sources, actions, verification, and audit history. The queue refreshes while the page is open.

The mock agent reports a simulated resolution when the description already says recovery was observed. If the issue is still failing, recovery is uncertain, or policy requires oversight, the workflow routes it for human review. A simulated resolution is not proof that a real issue was fixed.

**Public demo privacy:** submissions are kept in the shared demo database and visible to other visitors. Enter fictional, anonymized examples only. Do not enter company incident data, credentials, personal information, or secrets.

## Dashboard tour

- **Overview:** queue, counts, filters, search, sort, incident details, and the test drive.
- **Agent activity:** persisted analysis, escalation, and action events in time order.
- **Knowledge base:** search the local runbooks used to ground recommendations.
- **Approvals:** inspect and approve eligible mock actions as a separate operator.
- **Evaluations:** view the small labeled sample metrics and their limits.
- **Settings:** inspect runtime and safety settings, and try the mock ServiceNow sync controls.
- **Dark / Light:** use the theme button in the top bar. Northstar remembers the choice in this browser.
- **Quick start guide:** use the question-mark button in the top bar or the sidebar help card for these main steps and deployment links.

## Deploy your own copy from GitHub

This creates a separate demo attached to your GitHub fork. You need GitHub and Render accounts. The no-cost demo needs no OpenAI key and no ServiceNow credentials.

1. Sign in to GitHub and open the [Northstar repository](https://github.com/lokeshasrith/northstar-servicenow-ai-agent).
2. Select **Fork** and create a copy under your GitHub account.
3. Sign in to [Render](https://render.com/) using the GitHub account that can access your fork.
4. In Render, choose **New + → Blueprint**. Connect GitHub if asked, then select your forked `northstar-servicenow-ai-agent` repository.
5. Review the services in `render.yaml` and create the Blueprint. For a portfolio demo, keep the mock configuration and free plans. Wait for the web service to become **Live**.
6. Open the service in the Render dashboard and use its `onrender.com` URL. That is the public app link; GitHub repository pages do not host this interactive app. Check `<your-service-url>/api/health` for `{"status":"ok","database":"ok"}`.

Render may ask for access to the repository so it can build and deploy commits. The Blueprint configures a mock-only app and a database. The free web service sleeps when idle, so its first request can be slow; the free database expires after 30 days and demo data is disposable. Use a paid, backed-up service for a continuously available portfolio or production environment. If a new GitHub commit does not trigger a Render deployment, open the service and choose **Manual Deploy → Deploy latest commit**.

GitHub Actions runs the project checks when code is pushed. Check the **Actions** tab for CI results; use the Render dashboard to see deployment status and copy the public service URL.

## Run it on your computer

Install Docker Desktop, clone your fork, then from the repository directory run:

```powershell
git clone https://github.com/YOUR_GITHUB_USERNAME/northstar-servicenow-ai-agent.git
cd northstar-servicenow-ai-agent
Copy-Item .env.example .env
docker compose up --build
```

Open:

- Dashboard: <http://localhost:5173>
- API health: <http://localhost:8000/api/health>
- Interactive API reference: <http://localhost:8000/docs>

The default `.env` uses mock adapters. The agent seeds sample incidents into an empty local database. To stop the stack, press `Ctrl+C`; to start it again, run `docker compose up`. Local PostgreSQL data is kept in the `postgres_data` Docker volume.

## Use the complete workflow

1. Create and process a fictional incident from the Overview page.
2. Open its detail to read the classification explanation, confidence, cited knowledge, status, verification, action list, timeline, and audit records.
3. Search the Knowledge base for terms such as `VPN`, `DNS`, or `account locked`.
4. Open Approvals to review eligible approval-gated actions. The public demo records simulated actions only.
5. Open Agent activity to inspect the incident event timeline, Evaluations to inspect the labeled demo metrics, and Settings to see the selected providers and mock sync tools.
6. Use queue filters, priority sorting, search, pagination, and manual refresh on Overview. The page also refreshes the queue every seven seconds while visible.

## Connect optional providers on a private deployment

Keep the public portfolio deployment mock-only. To configure providers, use a private instance that you control, store secrets in the hosting provider's environment settings, and do not commit them to GitHub.

- **OpenAI:** set `LLM_PROVIDER=openai`, `OPENAI_API_KEY`, and optionally `OPENAI_MODEL`.
- **ServiceNow:** set `SERVICENOW_MODE=real`, `SERVICENOW_INSTANCE_URL`, `SERVICENOW_USERNAME`, and `SERVICENOW_PASSWORD` for a dedicated least-privilege developer instance account.
- **Dashboard access:** set `DASHBOARD_ADMIN_KEY` and/or `DASHBOARD_VIEWER_KEY` on a private deployment before exposing write or read endpoints.
- Set `PUBLIC_DEMO_MODE=false` for provider credentials. Public demo mode rejects credentials and requires both providers to remain mocked.

The real ServiceNow adapter supports incident sync and selected ticket operations. This project does not include a real remediation executor or independent real-world recovery verification; it will not claim that it repaired or closed a real incident. Read the [README](../README.md), [architecture notes](architecture.md), and [evaluation caveats](evaluation-report.md) before changing the mock configuration.

## Troubleshooting

- **The hosted page takes a while:** the free web service may be waking after idle. Wait for the backend indicator; check the `/api/health` link.
- **The dashboard says API needs attention:** refresh after the service wakes and confirm `/api/health` reports the database as healthy.
- **A push did not deploy:** confirm GitHub Actions completed, then use Render **Manual Deploy → Deploy latest commit**.
- **The demo queue contains visitor examples:** this is expected for the shared public deployment. Keep submitted data fictional and anonymous.
