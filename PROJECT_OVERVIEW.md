# Organizational Efficiency Consultant — Project Overview

## Summary

A single-tenant, localhost-first web application that acts as an AI-powered organizational efficiency consultant. It guides users through a structured 6-step analysis using the Claude API: collecting organizational data, mapping workflows, ranking automation opportunities by ROI, designing a system architecture, generating platform-specific workflow configs, and presenting everything in a live dashboard.

**Live deployment:** https://consultant-app-production.up.railway.app

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11+, FastAPI, Uvicorn |
| Frontend | Jinja2 templates, HTMX, Mermaid.js, Chart.js |
| Database | SQLite (local), PostgreSQL (Railway) |
| AI | Anthropic SDK (`claude-sonnet-4-6`), streaming SSE |
| Deployment | Railway (Nixpacks builder) |

---

## Project Structure

```
consultant/
├── run.py                          # Local dev entry point
├── Procfile                        # Railway/Heroku web process
├── railway.toml                    # Railway deploy config
├── requirements.txt
├── .env                            # ANTHROPIC_API_KEY, DATABASE_URL
├── app/
│   ├── main.py                     # FastAPI app, router mounts, static config
│   ├── config.py                   # Pydantic Settings (reads .env)
│   ├── database.py                 # SQLAlchemy engine, SessionLocal, get_db()
│   ├── models.py                   # 10 ORM models
│   ├── schemas.py                  # Pydantic request/response schemas
│   ├── routers/
│   │   ├── home.py                 # GET / — org setup
│   │   ├── discovery.py            # Step 1 — intake + Q&A + process inventory
│   │   ├── workflow.py             # Step 2 — workflow mapping per department
│   │   ├── audit.py                # Step 3 — automation opportunity audit
│   │   ├── architecture.py         # Step 4 — system architecture design
│   │   ├── build.py                # Step 5 — platform config generation
│   │   ├── dashboard.py            # Step 6 — master dashboard
│   │   └── kpis.py                 # KPI CRUD + history
│   ├── services/
│   │   ├── claude_client.py        # Anthropic SDK, streaming, retry
│   │   ├── context_builder.py      # Assembles prior-step DB context for prompts
│   │   └── parsers.py              # Extracts JSON/Mermaid from Claude responses
│   ├── prompts/
│   │   ├── discovery.py
│   │   ├── workflow.py
│   │   ├── audit.py
│   │   ├── architecture.py
│   │   └── build.py
│   ├── templates/
│   │   ├── base.html               # Sidebar nav layout
│   │   ├── home.html
│   │   ├── steps/                  # One template per analysis step
│   │   ├── dashboard/              # Six dashboard sub-page templates
│   │   └── partials/               # HTMX swap targets
│   └── static/
│       ├── css/style.css           # Dark theme component library
│       └── js/app.js               # Mermaid init, SSE handler, Chart.js
```

---

## Database Models

| Model | Purpose |
|---|---|
| `Organization` | Org name, industry, org chart text, tool stack, bottlenecks |
| `ConversationMessage` | Full chat history per step (role + content) |
| `Process` | Individual business processes with department, hours/week, rank |
| `WorkflowMap` | Mermaid diagram + flagged handoffs/redundancies/triggers per department |
| `AutomationOpportunity` | Ranked automation items with ROI score, complexity, platform recommendation |
| `SystemArchitecture` | Mermaid architecture diagram, agents list, linear flows list |
| `WorkflowBuild` | Generated configs per opportunity per platform (n8n/Zapier/Make/Python) |
| `KPI` | KPI name, current value, target, unit, department, category |
| `KPIHistory` | Time-series values for each KPI (sparkline data) |
| `ImplementationPhase` | Auto-generated phases (Quick Wins / Medium / Complex) with progress tracking |

---

## The 6-Step Analysis Flow

### Step 1 — Discovery (`/discovery`)
Collects organization context via a structured intake form, then runs a streaming multi-turn conversation with Claude to ask 5–7 clarifying questions. On finalization, Claude outputs a JSON process inventory that is parsed and saved as `Process` rows.

**Claude output format:**
```json
{"processes": [{"name": "...", "department": "...", "time_cost_hours_per_week": N, "description": "...", "rank": N}]}
```

### Step 2 — Workflow Mapping (`/workflow`)
User selects a department and describes the workflow in plain English. Claude generates a `flowchart TD` Mermaid diagram with CSS class annotations (`:::handoff`, `:::redundant`, `:::trigger`) plus a JSON block flagging each issue type. Saved as `WorkflowMap`.

### Step 3 — Opportunity Audit (`/audit`)
Claude receives all workflow maps as context and identifies exactly 10 automation opportunities, ranked by ROI score. Each opportunity includes `roi_score` (0–100), `complexity` (low/medium/high), `build_time_days`, `annual_hours_saved`, and `platform_recommendation`.

**ROI formula:**
```
roi_score = (annual_hours_saved × 100) / (build_time_days × complexity_multiplier)
complexity_multiplier: low=1.0, medium=2.0, high=4.0
```

### Step 4 — Architecture Design (`/architecture`)
Claude receives the org tool stack and all opportunities, then produces a `graph TB` Mermaid architecture diagram plus a JSON block listing agents (multi-step decision logic) and linear flows (trigger + action chains).

### Step 5 — Build (`/build`)
For a selected opportunity, Claude generates concise workflow configurations for all 4 platforms simultaneously in a single response. Each config is returned in a named fenced code block (`n8n`, `zapier`, `make`, `python`). Saved as `WorkflowBuild` rows.

### Step 6 — Dashboard (`/dashboard`)
Read-only view of all analysis outputs with 6 sub-pages: Overview, Process Maps, Opportunities, Architecture, Builds, KPIs.

---

## Claude API Integration

**Model:** `claude-sonnet-4-6`

**Streaming pattern (all analysis steps):**
```python
async def generate():
    full_response = []
    async for chunk in stream_claude(SYSTEM_PROMPT, messages, max_tokens=N):
        full_response.append(chunk)
        yield f"data: {chunk.replace(chr(10), chr(92)+'n')}\n\n"
    yield "data: [DONE]\n\n"
    # parse full_response and save to DB

return StreamingResponse(generate(), media_type="text/event-stream")
```

**Browser SSE reader (`app.js`):**
```javascript
readSSEStream(response, targetElement, onDoneCallback)
```
Appends chunks to a `<div>` in real time; calls `onDone` (usually `location.reload()`) when `[DONE]` is received.

**Context chaining:** `context_builder.py` queries the DB to assemble all prior-step data into each new prompt, giving Claude full organizational context at every stage.

**Structured output:** Every prompt instructs Claude to wrap JSON in ` ```json ``` ` fences. `parsers.py` uses regex to extract and parse them. Mermaid diagrams are similarly extracted from ` ```mermaid ``` ` blocks.

---

## Deployment (Railway)

The app is deployed on Railway with a Nixpacks build. Environment variables required:

| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `DATABASE_URL` | PostgreSQL connection string (Railway Postgres add-on) |

The Railway Postgres public proxy URL must be used (not the internal DNS hostname).

Local development uses SQLite automatically when `DATABASE_URL` is not set to a `postgresql://` URL.

---

## Local Development

```bash
cd /home/paul/code/consultant
cp .env.example .env      # add your ANTHROPIC_API_KEY
venv/bin/python run.py    # starts at http://localhost:8000
```
