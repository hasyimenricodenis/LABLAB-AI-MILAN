import pytest

from src.agents.base import AuditLog
from src.agents.citizen_service import CitizenServiceAgent
from src.agents.ingestion import IngestionAgent
from src.agents.insight import InsightAgent
from src.agents.messaging import MessagingAgent
from src.agents.narrative import NarrativeAgent
from src.agents.privacy import PrivacyAgent
from src.agents.quality import QualityAgent


@pytest.fixture
def audit_log() -> AuditLog:
    return AuditLog()


@pytest.fixture
def raw_records():
    return [
        {
            "report_id": "JKT-A",
            "district": "central jakarta",
            "suspected_condition": "Dengue",
            "symptom_severity": "HIGH",
            "reported_at": "2026-05-12T08:14:00",
            "citizen_name": "Rani Putri",
            "citizen_phone": "081234567891",
            "citizen_address": "Jl. Merdeka 10",
            "national_id": "3174010101010001",
            "preferred_language": "ID",
        },
        {
            "report_id": "JKT-B",
            "district": "",
            "suspected_condition": "flu",
            "symptom_severity": "extreme",
            "reported_at": "",
            "citizen_name": "Budi",
            "citizen_phone": "081111111111",
            "citizen_address": "Jl. X",
            "national_id": "3174010101010002",
            "preferred_language": "it",
        },
    ]


def test_ingestion_normalizes_casing(audit_log, raw_records):
    agent = IngestionAgent(audit_log=audit_log)
    result = agent.run({"records": raw_records})
    records = result.payload["records"]

    assert len(records) == 2
    assert records[0]["district"] == "Central Jakarta"
    assert records[0]["suspected_condition"] == "dengue"
    assert records[0]["symptom_severity"] == "high"
    assert records[0]["preferred_language"] == "id"
    assert audit_log.entries[-1].agent == "ingestion"
    assert audit_log.entries[-1].input_count == 2


def test_quality_flags_missing_and_invalid(audit_log, raw_records):
    ingested = IngestionAgent().run({"records": raw_records}).payload
    agent = QualityAgent(
        required_fields=["report_id", "district", "symptom_severity", "suspected_condition"],
        acceptable_severity=["low", "medium", "high", "critical"],
        known_conditions=["dengue", "tuberculosis", "flu"],
        audit_log=audit_log,
    )
    out = agent.run(ingested).payload["records"]

    assert out[0]["quality_issues"] == []
    assert out[0]["quality_score"] == 100

    assert "missing:district" in out[1]["quality_issues"]
    assert "invalid:symptom_severity" in out[1]["quality_issues"]
    assert out[1]["quality_score"] < 100


def test_privacy_redacts_and_pseudonymizes():
    record = {
        "report_id": "X",
        "district": "Central Jakarta",
        "suspected_condition": "dengue",
        "symptom_severity": "high",
        "citizen_name": "Rani",
        "citizen_phone": "08123",
        "citizen_address": "Jl. Merdeka 10",
        "national_id": "3174010101010001",
        "quality_score": 100,
        "quality_issues": [],
    }
    agent = PrivacyAgent(
        redact_fields=["citizen_name", "citizen_phone", "citizen_address", "national_id"],
    )
    out = agent.run({"records": [record]}).payload["records"][0]

    assert out["citizen_name"] == "[REDACTED]"
    assert out["citizen_phone"] == "[REDACTED]"
    assert out["national_id"] == "[REDACTED]"
    assert out["citizen_id"].startswith("cit_") and len(out["citizen_id"]) == 16


def test_privacy_pseudonym_is_deterministic():
    agent = PrivacyAgent(redact_fields=["national_id"], salt="s")
    a = agent.run({"records": [{"national_id": "ID-1", "quality_score": 100}]}).payload["records"][0]
    b = agent.run({"records": [{"national_id": "ID-1", "quality_score": 100}]}).payload["records"][0]
    c = agent.run({"records": [{"national_id": "ID-2", "quality_score": 100}]}).payload["records"][0]
    assert a["citizen_id"] == b["citizen_id"]
    assert a["citizen_id"] != c["citizen_id"]


def test_insight_priority_buckets():
    agent = InsightAgent(high_risk_conditions=["dengue", "tuberculosis"])
    records = [
        {"suspected_condition": "dengue", "symptom_severity": "critical", "quality_score": 100, "district": "A"},
        {"suspected_condition": "flu", "symptom_severity": "low", "quality_score": 100, "district": "B"},
    ]
    out = agent.run({"records": records}).payload
    assert out["records"][0]["service_priority"] == "high"
    assert out["records"][0]["risk_score"] >= 80
    assert out["records"][1]["service_priority"] == "low"
    assert "priority_distribution" in out["trends"]


def test_citizen_service_actions():
    agent = CitizenServiceAgent()
    records = [
        {"report_id": "1", "service_priority": "high", "district": "A", "suspected_condition": "dengue", "symptom_severity": "critical", "risk_score": 90, "preferred_language": "id"},
        {"report_id": "2", "service_priority": "medium", "district": "B", "suspected_condition": "flu", "symptom_severity": "medium", "risk_score": 60, "preferred_language": "en"},
        {"report_id": "3", "service_priority": "low", "district": "C", "suspected_condition": "flu", "symptom_severity": "low", "risk_score": 20, "preferred_language": "it"},
    ]
    out = agent.run({"records": records}).payload
    actions = out["actions"]
    assert actions[0]["requires_human_review"] is True
    assert actions[0]["sla_hours"] == 2
    assert actions[1]["sla_hours"] == 24
    assert actions[2]["sla_hours"] == 168


def test_messaging_languages():
    agent = MessagingAgent()
    actions = [
        {"report_id": "1", "service_priority": "high", "district": "Central Jakarta", "suspected_condition": "dengue", "preferred_language": "id"},
        {"report_id": "2", "service_priority": "medium", "district": "South Jakarta", "suspected_condition": "flu", "preferred_language": "en"},
        {"report_id": "3", "service_priority": "low", "district": "North Jakarta", "suspected_condition": "tuberculosis", "preferred_language": "it"},
        {"report_id": "4", "service_priority": "high", "district": "East Jakarta", "suspected_condition": "dengue", "preferred_language": "fr"},
    ]
    out = agent.run({"actions": actions}).payload
    assert "Halo" in out["messages"][0]["text"]
    assert "Hello" in out["messages"][1]["text"]
    assert "Salve" in out["messages"][2]["text"]
    assert out["messages"][3]["language"] == "id"


def test_narrative_template_when_no_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    agent = NarrativeAgent(api_key=None)
    out = agent.run(
        {
            "actions": [
                {"report_id": "1", "service_priority": "high", "district": "A", "suspected_condition": "dengue", "symptom_severity": "high", "risk_score": 90}
            ],
            "trends": {
                "top_districts": [("A", 1)],
                "top_conditions": [("dengue", 1)],
                "priority_distribution": {"high": 1},
            },
        }
    ).payload
    assert "Public Health Daily Briefing" in out["briefing"]
    assert out["stats"]["high_priority"] == 1
