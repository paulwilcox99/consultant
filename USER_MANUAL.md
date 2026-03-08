# Organizational Efficiency Consultant — User Manual

## Getting Started

### Prerequisites
- Python 3.11+
- An Anthropic API key (https://console.anthropic.com)

### Running Locally

```bash
cd /home/paul/code/consultant
cp .env.example .env
# Edit .env and set: ANTHROPIC_API_KEY=sk-ant-...
venv/bin/python run.py
```

Open http://localhost:8000 in your browser.

**Live deployment:** https://consultant-app-production.up.railway.app

---

## Navigation

The left sidebar is always visible and gives you access to every section:

- **Setup** — Initial org setup (run once)
- **Step 1: Discovery** — Intake and process inventory
- **Step 2: Workflow Mapping** — Department workflow diagrams
- **Step 3: Opportunity Audit** — Automation opportunities ranked by ROI
- **Step 4: Architecture** — System architecture diagram
- **Step 5: Build** — Platform-specific workflow configs
- **Dashboard** — All outputs in one place

Complete the steps in order. Each step feeds context into the next.

---

## Step 1 — Organization Setup

**URL:** `/`

Fill in the setup form:

| Field | What to enter |
|---|---|
| Organization Name | Your company or team name |
| Industry | e.g., B2B SaaS, Healthcare, Logistics |
| Org Chart | Paste a text description of departments and reporting structure |
| Tool Stack | List every tool your org uses (CRM, project mgmt, comms, etc.) |
| Top 3 Bottlenecks | Brief descriptions of your biggest pain points |

Click **Start Analysis**. You'll be redirected to Step 1.

---

## Step 2 — Discovery (Step 1 in the app)

**URL:** `/discovery`

This step runs a structured interview with the AI consultant.

1. **Review the initial questions** — Claude will ask 5–7 clarifying questions about your processes, team sizes, tool integrations, and automation history.

2. **Answer each question** — Type your answers in the chat input and click **Send**. The conversation streams in real time.

3. **Finalize** — Once you've answered all questions, click **Finalize & Extract Processes**. Claude will analyze the full conversation and extract a ranked process inventory.

**Output:** A table of business processes with department, weekly hours, and priority rank. These become the foundation for all subsequent steps.

> **Tip:** Be specific. Mentioning exact tool names (e.g., "we copy rows from Google Sheets into Salesforce manually every Monday") leads to much better automation suggestions later.

---

## Step 3 — Workflow Mapping (Step 2 in the app)

**URL:** `/workflow`

Map workflows department by department.

1. **Select a department** from the dropdown (populated from your process inventory).

2. **Describe the workflow** in plain English in the text area. Example:
   > "Sales rep gets a new lead in HubSpot. They manually check Salesforce for duplicates, then copy the lead data into a spreadsheet and email the account manager. The AM reviews it in the next team meeting and decides whether to pursue."

3. Click **Map Workflow**. Claude generates:
   - An interactive Mermaid flowchart
   - Color-coded nodes: **orange** = manual handoff, **red** = redundant step, **green** = automation trigger
   - A list of flagged issues below the diagram

4. **Repeat for each department** you want to analyze.

**Output:** `WorkflowMap` records stored per department. All maps are used as context in the Opportunity Audit.

---

## Step 4 — Opportunity Audit (Step 3 in the app)

**URL:** `/audit`

Identify the best automation opportunities across your entire organization.

1. Review the workflow maps shown as context at the top of the page.

2. Click **Run Audit**. Claude analyzes all your workflow maps and identifies exactly 10 automation opportunities.

3. Results appear as cards sorted by **ROI Score** (0–100), highest first. Each card shows:
   - Opportunity title and description
   - ROI score
   - Complexity (Low / Medium / High)
   - Estimated build time (days)
   - Annual hours saved
   - Recommended platform (n8n, Zapier, Make, or Python)

**ROI Score formula:**
```
roi_score = (annual_hours_saved × 100) / (build_time_days × complexity_multiplier)
```
Where complexity multipliers are: Low = 1.0×, Medium = 2.0×, High = 4.0×.

> **Tip:** You don't need to act on all 10. Use the ROI score and complexity to prioritize what to build first.

---

## Step 5 — Architecture Design (Step 4 in the app)

**URL:** `/architecture`

Design the technical architecture for your automation system.

1. Click **Design Architecture**. Claude receives your tool stack and all 10 opportunities as context.

2. The result includes:
   - An interactive Mermaid architecture diagram showing how your tools connect
   - An **Agents** table — opportunities that need multi-step decision logic
   - A **Linear Flows** table — simpler trigger-and-action automations

3. Each agent entry includes: name, purpose, inputs/outputs, recommended framework (Python, LangChain, etc.).

**Output:** One `SystemArchitecture` record with the diagram and structured data used in the dashboard.

---

## Step 6 — Build (Step 5 in the app)

**URL:** `/build`

Generate ready-to-use workflow configurations for any opportunity.

1. **Select an opportunity** from the dropdown.

2. Click **Generate Workflows**. Claude generates configurations for all 4 platforms simultaneously.

3. Use the **tabs** to switch between platforms:
   - **n8n** — Node.js workflow JSON (import directly into n8n)
   - **Zapier** — Zap structure description
   - **Make** — Scenario blueprint
   - **Python** — Standalone automation script

4. Click **Copy** on any tab to copy the config to your clipboard.

> **Note:** Configs are intentionally concise (3–6 nodes) to give you a working starting point. Extend them in your automation platform as needed.

**Output:** `WorkflowBuild` records stored per opportunity per platform, accessible any time in the dashboard.

---

## Dashboard

**URL:** `/dashboard`

The dashboard is read-only and gives you a unified view of all analysis outputs.

### Overview
- Total processes mapped
- Total automation opportunities identified
- Projected annual hours saved
- Number of builds completed
- KPI completion percentage

### Process Maps
Select a department from the dropdown to view its Mermaid workflow diagram and flagged issues.

### Opportunities
Full card grid of all 10 automation opportunities, sorted by ROI score. Click any card to see its associated build artifacts.

### Architecture
The full system architecture diagram, agents table, and linear flows table.

### Builds
Browse workflow configs by opportunity. Use the platform tabs to switch between n8n, Zapier, Make, and Python. Copy button available on each tab.

### KPIs

Track key performance indicators for your automation program.

**Adding a KPI:**
1. Click **Add KPI**
2. Fill in: Name, Unit (e.g., "hours/week"), Target, Department, Category
3. Click **Save**

**Updating a KPI value:**
1. Click **Update** on any KPI card
2. Enter the new current value
3. Click **Save** — the value is recorded to history

Each KPI card shows:
- Current value vs. target
- Progress bar
- Sparkline chart (history trend, if multiple values recorded)

### Implementation Phases
A panel on the right side of all dashboard pages (when phases exist) shows three auto-generated phases:
- **Phase 1: Quick Wins** — Low complexity, high ROI opportunities
- **Phase 2: Medium Term** — Medium complexity items
- **Phase 3: Complex** — High complexity, high-value items

Use the progress slider on each phase to track implementation status.

---

## Tips and Best Practices

**Be detailed in Discovery.** The more context you give in Step 1 (team sizes, tool names, process frequencies), the more actionable the audit results will be.

**Map your most painful workflows first.** Step 2 lets you map multiple departments. Focus on the ones you mentioned as bottlenecks in Setup.

**Run the audit once, build incrementally.** The audit runs against all your workflow maps at once. Run it after you've mapped at least 3–4 departments for the best results.

**Use the ROI score as a starting point, not gospel.** The formula is based on Claude's estimates of hours saved and build time. Adjust your prioritization based on your team's actual capacity and tool access.

**Extend the generated configs.** The platform configs are intentionally minimal (3–6 nodes) to be easy to understand. Import them into your automation tool and build on top of them.

**Re-run steps freely.** You can re-run any step. Workflow maps and builds are additive — each run creates a new record. The audit and architecture steps replace their previous result.

---

## Troubleshooting

**Streaming output stops mid-response**
This usually means the Claude API hit a token limit. Refresh the page and try again. If it happens consistently, the prompt may be receiving too much context — try mapping fewer departments before running the audit.

**Mermaid diagram doesn't render**
The diagram may contain a syntax error from Claude's output. Check the raw text at the bottom of the page. You can paste it into https://mermaid.live to debug.

**Process inventory shows zeros for hours**
This can happen if the Discovery conversation was very short. Go back to `/discovery`, answer the clarifying questions in more detail (mentioning specific time estimates), then click Finalize again.

**Database errors after deployment**
Ensure `DATABASE_URL` is set to the public proxy URL (not the internal Railway DNS hostname). The internal hostname (`*.railway.internal`) is not resolvable from application code at runtime.
