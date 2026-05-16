# Jakarta Public Health · Autonomous Agents

Built for **LabLab AI Milan**. Jakarta-powered, globally minded.

An autonomous multi-agent system that turns raw, messy public-health reports into
privacy-safe, prioritized citizen-service actions — with a human-in-the-loop
Streamlit dashboard, a multilingual citizen-messaging layer, an LLM-generated
daily briefing, and a full audit trail.

## Why this project
Public-health teams spend most of their time stitching together fragmented,
manual, and error-prone data workflows. By the time insights reach the field,
they are stale and the citizen experience suffers. This project ships an
end-to-end pipeline of cooperating agents that any city can adopt.

## Pipeline

```
ingestion → quality → privacy → insight → citizen_service → messaging → narrative
```

| Agent             | Role                                                                                  |
|-------------------|---------------------------------------------------------------------------------------|
| `IngestionAgent`  | Normalizes raw records (casing, whitespace, default language).                        |
| `QualityAgent`    | Flags missing required fields, invalid severities, unknown conditions; scores rows.   |
| `PrivacyAgent`    | Redacts PII (name/phone/address/national_id) and emits a stable pseudonymized `citizen_id`. |
| `InsightAgent`    | Computes per-record risk score + district / condition / priority trends.              |
| `CitizenServiceAgent` | Maps priorities to concrete playbooks (SLAs, channels, human-review flags).       |
| `MessagingAgent`  | Generates citizen-facing notification text in **Indonesian / English / Italian**.     |
| `NarrativeAgent`  | LLM-powered daily briefing (Anthropic Claude) — falls back to a template offline.     |

Every agent run is captured in an `AuditLog` with timing, IO counts, and a unique `trace_id`.

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# CLI run (template briefing, no API key needed)
python -m src.main

# Skip LLM briefing
python -m src.main --no-narrative

# Persist the full JSON result
python -m src.main --output out/result.json

# LLM briefing via Anthropic Claude
export ANTHROPIC_API_KEY=sk-ant-...
python -m src.main

# Human-in-the-loop dashboard
streamlit run src/dashboard.py
```

## Streamlit dashboard

- **Actions tab** — editable data grid with per-case approve / escalate toggles
  and a progress-bar risk visualizer.
- **Messages tab** — preview citizen messages in ID / EN / IT, download as CSV.
- **Briefing tab** — LLM-rendered daily briefing (or deterministic template).
- **Trends tab** — top districts, top conditions, priority distribution.
- **Audit tab** — full per-agent trace with timings and IO counts.

## Tests

```bash
python -m pytest tests/ -v
```

11 tests cover the agents individually and the workflow end-to-end (including
audit-log completeness and multilingual coverage).

## Configuration

All agent behavior is driven by [`config/agents.yaml`](config/agents.yaml):
required fields, acceptable severities, known conditions, PII redaction list,
high-risk conditions, supported languages, and LLM model.

## Repository layout

```
.
├── config/agents.yaml              # agent-level configuration
├── src/
│   ├── agents/
│   │   ├── base.py                 # BaseAgent + AuditLog + AgentResult
│   │   ├── ingestion.py
│   │   ├── quality.py
│   │   ├── privacy.py              # PII redaction + SHA-256 pseudonym
│   │   ├── insight.py              # risk score + trends
│   │   ├── citizen_service.py      # playbooks + SLAs
│   │   ├── messaging.py            # ID / EN / IT templates
│   │   └── narrative.py            # LLM briefing (Anthropic) + fallback
│   ├── data/public_health_sample.csv
│   ├── workflows/public_health_workflow.py
│   ├── dashboard.py                # Streamlit HITL UI
│   └── main.py                     # CLI entry point
├── tests/
│   ├── test_agents.py
│   └── test_workflow.py
├── docs/
│   ├── ARCHITECTURE.md
│   └── ROADMAP.md
├── requirements.txt
└── README.md
```

## Privacy by design

- PII fields are redacted *before* any analytics or messaging agent sees them.
- A SHA-256-with-salt `citizen_id` lets downstream systems join cases without
  ever handling raw national IDs.
- The audit log records *counts and timings only* — no record content.

## Roadmap highlights

See [`docs/ROADMAP.md`](docs/ROADMAP.md) for the full backlog. Highlights:

- Connect to city data APIs and health-information systems.
- Add retrieval-augmented policy guidance for interventions.
- Push messages via real SMS / WhatsApp providers.
- Add Prometheus metrics + structured JSON logs.
- Add evaluation benchmarks with synthetic adversarial cases.
