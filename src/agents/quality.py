from typing import Any, Dict, List, Optional, Tuple

from .base import AuditLog, BaseAgent


class QualityAgent(BaseAgent):
    """Score record completeness + flag invalid categorical values."""

    def __init__(
        self,
        required_fields: List[str],
        acceptable_severity: List[str],
        known_conditions: Optional[List[str]] = None,
        audit_log: Optional[AuditLog] = None,
    ) -> None:
        super().__init__(name="quality", audit_log=audit_log)
        self.required_fields = required_fields
        self.acceptable_severity = set(acceptable_severity)
        self.known_conditions = set(known_conditions or [])

    def _execute(self, payload: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        records: List[Dict[str, Any]] = payload["records"]
        evaluated: List[Dict[str, Any]] = []
        failed = 0

        for record in records:
            issues: List[str] = []

            for field in self.required_fields:
                if not record.get(field):
                    issues.append(f"missing:{field}")

            severity = record.get("symptom_severity", "")
            if severity and severity not in self.acceptable_severity:
                issues.append("invalid:symptom_severity")

            condition = record.get("suspected_condition", "")
            if self.known_conditions and condition and condition not in self.known_conditions:
                issues.append("unknown:suspected_condition")

            quality_score = max(0, 100 - (len(issues) * 20))
            if quality_score < 60:
                failed += 1

            evaluated.append(
                {
                    **record,
                    "quality_issues": issues,
                    "quality_score": quality_score,
                }
            )

        notes = {
            "below_threshold": failed,
            "records_evaluated": len(evaluated),
        }
        return {"records": evaluated}, notes
