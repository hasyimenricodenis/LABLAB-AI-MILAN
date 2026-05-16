# Roadmap

## Phase 1: Foundation — DONE
- Multi-agent workflow scaffolding in Python (`BaseAgent`, `AuditLog`, sequential orchestrator).
- Sample Jakarta public-health dataset with edge cases.
- Ingestion, quality, privacy, insight, and citizen-service agents.
- Unit + end-to-end tests under `tests/`.

## Phase 2: Intelligence — DONE
- LLM-backed daily briefing via Anthropic Claude (`NarrativeAgent`), with a
  deterministic template fallback when no API key is configured.
- District / condition / priority aggregation (`InsightAgent.trends`).
- Pseudonymized `citizen_id` (SHA-256 + salt) for downstream analytics.

## Phase 3: Service delivery — DONE
- Multilingual citizen messaging (`MessagingAgent`) for **Indonesian / English / Italian**.
- Priority-aware playbooks with SLAs and human-review flags
  (`CitizenServiceAgent`).
- Streamlit human-in-the-loop dashboard with approve / escalate controls,
  trend charts, briefing viewer, and audit-trail tab.

## Phase 4: Integration (next)
- Connect ingestion to Jakarta DKI Health partner APIs.
- Push citizen messages via real SMS / WhatsApp providers (Twilio, Vonage).
- Pull policy documents into a retrieval-augmented intervention planner.
- Role-based access control on the dashboard (officer vs supervisor vs admin).

## Phase 5: Governance & scale
- Formal evaluation suite with synthetic adversarial cases (data quality + privacy + triage).
- Prometheus metrics + structured JSON logs.
- Explainability reports per triage decision.
- Multi-city deployment templates (Jakarta, Milan, Bangkok, Manila, ...).
