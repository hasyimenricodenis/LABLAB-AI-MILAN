from typing import Any, Dict, List, Optional

from src.agents.base import AuditLog
from src.agents.citizen_service import CitizenServiceAgent
from src.agents.ingestion import IngestionAgent
from src.agents.insight import InsightAgent
from src.agents.messaging import MessagingAgent
from src.agents.narrative import NarrativeAgent
from src.agents.privacy import PrivacyAgent
from src.agents.quality import QualityAgent


class PublicHealthWorkflow:
    """Sequential orchestration of the public-health multi-agent pipeline."""

    def __init__(
        self,
        config: Dict[str, Any],
        audit_log: Optional[AuditLog] = None,
        enable_narrative: bool = True,
    ) -> None:
        self.config = config
        self.audit_log = audit_log or AuditLog()

        quality_cfg = config["agents"]["quality"]
        privacy_cfg = config["agents"]["privacy"]
        insight_cfg = config["agents"]["insight"]
        messaging_cfg = config["agents"].get("messaging", {})
        narrative_cfg = config["agents"].get("narrative", {})

        self.ingestion = IngestionAgent(audit_log=self.audit_log)
        self.quality = QualityAgent(
            required_fields=quality_cfg["required_fields"],
            acceptable_severity=quality_cfg["acceptable_severity"],
            known_conditions=quality_cfg.get("known_conditions"),
            audit_log=self.audit_log,
        )
        self.privacy = PrivacyAgent(
            redact_fields=privacy_cfg["redact_fields"],
            pseudonym_field=privacy_cfg.get("pseudonym_field", "national_id"),
            salt=privacy_cfg.get("salt", "lablab-milan-2026"),
            audit_log=self.audit_log,
        )
        self.insight = InsightAgent(
            high_risk_conditions=insight_cfg["high_risk_conditions"],
            audit_log=self.audit_log,
        )
        self.citizen_service = CitizenServiceAgent(audit_log=self.audit_log)
        self.messaging = MessagingAgent(
            default_language=messaging_cfg.get("default_language", "id"),
            supported_languages=messaging_cfg.get("supported_languages"),
            audit_log=self.audit_log,
        )
        self.enable_narrative = enable_narrative
        self.narrative = (
            NarrativeAgent(
                model=narrative_cfg.get("model"),
                max_tokens=narrative_cfg.get("max_tokens", 512),
                audit_log=self.audit_log,
            )
            if enable_narrative
            else None
        )

    def run(self, raw_records: List[Dict[str, Any]]) -> Dict[str, Any]:
        step1 = self.ingestion.run({"records": raw_records}).payload
        step2 = self.quality.run(step1).payload
        step3 = self.privacy.run(step2).payload
        step4 = self.insight.run(step3).payload
        step5 = self.citizen_service.run(step4).payload
        step6 = self.messaging.run(step5).payload

        briefing_payload: Dict[str, Any] = {}
        if self.narrative is not None:
            briefing_payload = self.narrative.run(step6).payload

        return {
            "processed_records": step4["records"],
            "citizen_actions": step5["actions"],
            "messages": step6["messages"],
            "trends": step4.get("trends", {}),
            "briefing": briefing_payload.get("briefing", ""),
            "stats": briefing_payload.get("stats", {}),
            "audit": self.audit_log.to_dict(),
        }
