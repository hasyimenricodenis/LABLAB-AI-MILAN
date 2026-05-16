from pathlib import Path

import pandas as pd
import yaml

from src.workflows.public_health_workflow import PublicHealthWorkflow

ROOT = Path(__file__).resolve().parent.parent


def load_config():
    with open(ROOT / "config" / "agents.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_records():
    df = pd.read_csv(ROOT / "src" / "data" / "public_health_sample.csv")
    df = df.where(pd.notna(df), "")
    return df.to_dict(orient="records")


def test_workflow_end_to_end(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    workflow = PublicHealthWorkflow(config=load_config())
    result = workflow.run(raw_records=load_records())

    assert len(result["citizen_actions"]) == 15
    assert len(result["messages"]) == 15
    assert result["audit"]["trace_id"]
    assert len(result["audit"]["entries"]) >= 6
    assert result["stats"]["total_cases"] == 15
    assert result["briefing"]

    high = [a for a in result["citizen_actions"] if a["service_priority"] == "high"]
    assert len(high) >= 1
    assert all(a["requires_human_review"] for a in high)

    languages = {m["language"] for m in result["messages"]}
    assert {"id", "en", "it"}.issubset(languages)


def test_workflow_no_narrative():
    workflow = PublicHealthWorkflow(config=load_config(), enable_narrative=False)
    result = workflow.run(raw_records=load_records())
    assert result["briefing"] == ""
    assert result["stats"] == {}


def test_workflow_audit_records_each_agent(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    workflow = PublicHealthWorkflow(config=load_config())
    result = workflow.run(raw_records=load_records())
    agents = [entry["agent"] for entry in result["audit"]["entries"]]
    for expected in ["ingestion", "quality", "privacy", "insight", "citizen_service", "messaging", "narrative"]:
        assert expected in agents
