from typing import Any, Dict, List, Optional, Tuple

from .base import AuditLog, BaseAgent


class IngestionAgent(BaseAgent):
    """Normalize incoming public-health records to a canonical schema."""

    CANONICAL_FIELDS = (
        "report_id",
        "district",
        "suspected_condition",
        "symptom_severity",
        "reported_at",
        "citizen_name",
        "citizen_phone",
        "citizen_address",
        "national_id",
        "preferred_language",
    )

    def __init__(self, audit_log: Optional[AuditLog] = None) -> None:
        super().__init__(name="ingestion", audit_log=audit_log)

    def _execute(self, payload: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        records: List[Dict[str, Any]] = payload["records"]
        normalized: List[Dict[str, Any]] = []
        dropped = 0

        for record in records:
            if not record:
                dropped += 1
                continue
            normalized.append(
                {
                    "report_id": str(record.get("report_id", "")).strip(),
                    "district": str(record.get("district", "")).strip().title(),
                    "suspected_condition": str(record.get("suspected_condition", "")).strip().lower(),
                    "symptom_severity": str(record.get("symptom_severity", "")).strip().lower(),
                    "reported_at": str(record.get("reported_at", "")).strip(),
                    "citizen_name": str(record.get("citizen_name", "")).strip(),
                    "citizen_phone": str(record.get("citizen_phone", "")).strip(),
                    "citizen_address": str(record.get("citizen_address", "")).strip(),
                    "national_id": str(record.get("national_id", "")).strip(),
                    "preferred_language": (
                        str(record.get("preferred_language", "id")).strip().lower() or "id"
                    ),
                }
            )

        return (
            {"records": normalized},
            {"dropped_empty_rows": dropped, "ingested_rows": len(normalized)},
        )
