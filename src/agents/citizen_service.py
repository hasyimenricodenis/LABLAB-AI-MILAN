from typing import Any, Dict, List, Optional, Tuple

from .base import AuditLog, BaseAgent


class CitizenServiceAgent(BaseAgent):
    """Translate insights into concrete citizen-service actions + escalation hints."""

    def __init__(self, audit_log: Optional[AuditLog] = None) -> None:
        super().__init__(name="citizen_service", audit_log=audit_log)

    @staticmethod
    def _playbook(priority: str) -> Dict[str, Any]:
        if priority == "high":
            return {
                "recommended_action": "Dispatch rapid response team within 2 hours",
                "delivery_channel": "Field Team + Call Center",
                "sla_hours": 2,
                "requires_human_review": True,
            }
        if priority == "medium":
            return {
                "recommended_action": "Schedule follow-up and teleconsultation within 24 hours",
                "delivery_channel": "Primary Care + Telemedicine",
                "sla_hours": 24,
                "requires_human_review": False,
            }
        return {
            "recommended_action": "Send preventive guidance and monitor weekly",
            "delivery_channel": "Automated Citizen Messaging",
            "sla_hours": 168,
            "requires_human_review": False,
        }

    def _execute(self, payload: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        records: List[Dict[str, Any]] = payload["records"]
        actions: List[Dict[str, Any]] = []
        escalations = 0

        for record in records:
            priority = record.get("service_priority", "low")
            playbook = self._playbook(priority)
            if playbook["requires_human_review"]:
                escalations += 1

            actions.append(
                {
                    "report_id": record.get("report_id"),
                    "citizen_id": record.get("citizen_id"),
                    "district": record.get("district", "Unknown"),
                    "suspected_condition": record.get("suspected_condition", ""),
                    "symptom_severity": record.get("symptom_severity", ""),
                    "risk_score": record.get("risk_score"),
                    "service_priority": priority,
                    "preferred_language": record.get("preferred_language", "id"),
                    **playbook,
                }
            )

        return (
            {"actions": actions, "trends": payload.get("trends", {})},
            {"escalations": escalations, "actions_emitted": len(actions)},
        )
