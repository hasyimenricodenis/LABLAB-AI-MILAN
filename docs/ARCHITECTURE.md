# Architecture

## Multi-agent design

```
┌────────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌──────────────────┐   ┌───────────┐   ┌────────────┐
│ Ingestion  │ → │ Quality │ → │ Privacy │ → │ Insight │ → │ Citizen Service  │ → │ Messaging │ → │ Narrative  │
└────────────┘   └─────────┘   └─────────┘   └─────────┘   └──────────────────┘   └───────────┘   └────────────┘
```

Every agent inherits from `BaseAgent` and implements `_execute(payload) -> (payload, notes)`.
`BaseAgent.run` wraps the call with timing, IO counts, and an entry in the shared `AuditLog`.

1. **IngestionAgent** — normalizes raw records (casing, whitespace, default language).
2. **QualityAgent** — validates required fields, severity values, and condition vocabulary.
3. **PrivacyAgent** — redacts PII; emits a salted SHA-256 `citizen_id` for joins.
4. **InsightAgent** — computes per-record `risk_score` + aggregate trends.
5. **CitizenServiceAgent** — maps `service_priority` to playbook (action, channel, SLA, human-review flag).
6. **MessagingAgent** — renders per-case citizen text in ID / EN / IT.
7. **NarrativeAgent** — generates a daily briefing via Anthropic Claude, falling back to a deterministic template when offline.

## Orchestration

`PublicHealthWorkflow` runs the agents sequentially. The output of each step is
fed into the next; the shared `AuditLog` provides a single `trace_id` and
per-agent entry for the full run.

Sequential execution is deliberate for a hackathon-scope demo: it is
deterministic, easy to audit, and trivially observable. The pattern generalizes
to event-driven or parallel execution where independent agents can run
concurrently on the same record stream.

## Data lifecycle

- **Raw zone** — restricted-access CSV / API payloads.
- **Validated zone** — quality-checked records with issue lists and scores.
- **Analytics zone** — privacy-redacted + pseudonymized records used by all
  downstream agents and dashboards.
- **Action zone** — citizen-service playbooks + multilingual messages.
- **Audit zone** — counts/timings/notes per agent run (no record content).

## Trust, safety & compliance

- Privacy-by-design: the Privacy agent is a *mandatory* gate before any analytics or messaging.
- Stable pseudonyms allow longitudinal analytics without re-exposing PII.
- High-priority cases default to `requires_human_review=True`.
- Audit log is content-free — safe to retain longer than raw records.

## Global scalability direction

- Schema adapters per city / country reporting standard.
- Language packs for citizen communication (currently ID / EN / IT — easy to extend).
- Per-jurisdiction policy packs (high-risk condition list, severity vocabulary).
- LLM model is configurable in `config/agents.yaml`.

## Testing

- Per-agent unit tests in `tests/test_agents.py`.
- End-to-end workflow test in `tests/test_workflow.py` (asserts audit
  completeness, multilingual coverage, and escalation policy).
