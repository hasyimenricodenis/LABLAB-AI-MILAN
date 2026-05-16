from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

from .base import AuditLog, BaseAgent


class InsightAgent(BaseAgent):
    """Compute per-record risk score + aggregate district trends."""

    SEVERITY_WEIGHTS = {
        "low": 0,
        "medium": 10,
        "high": 25,
        "critical": 40,
    }

    def __init__(
        self,
        high_risk_conditions: List[str],
        audit_log: Optional[AuditLog] = None,
    ) -> None:
        super().__init__(name="insight", audit_log=audit_log)
        self.high_risk_conditions = set(high_risk_conditions)

    def _score(self, record: Dict[str, Any]) -> int:
        condition = record.get("suspected_condition", "")
        severity = record.get("symptom_severity", "")
        quality_score = int(record.get("quality_score", 0))

        risk_score = 20
        if condition in self.high_risk_conditions:
            risk_score += 35
        risk_score += self.SEVERITY_WEIGHTS.get(severity, 0)
        risk_score += max(0, (80 - quality_score) // 2)
        return min(100, risk_score)

    @staticmethod
    def _priority(score: int) -> str:
        if score >= 80:
            return "high"
        if score >= 50:
            return "medium"
        return "low"

    def _execute(self, payload: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        records: List[Dict[str, Any]] = payload["records"]
        enriched: List[Dict[str, Any]] = []
        district_counter: Counter[str] = Counter()
        condition_counter: Counter[str] = Counter()
        priority_counter: Counter[str] = Counter()

        for record in records:
            score = self._score(record)
            priority = self._priority(score)
            enriched.append(
                {
                    **record,
                    "risk_score": score,
                    "service_priority": priority,
                }
            )
            district_counter[record.get("district", "Unknown")] += 1
            condition_counter[record.get("suspected_condition", "unknown")] += 1
            priority_counter[priority] += 1

        trends = {
            "top_districts": district_counter.most_common(5),
            "top_conditions": condition_counter.most_common(5),
            "priority_distribution": dict(priority_counter),
        }

        return {"records": enriched, "trends": trends}, trends
