import hashlib
from typing import Any, Dict, List, Optional, Tuple

from .base import AuditLog, BaseAgent


class PrivacyAgent(BaseAgent):
    """Redact PII fields and emit a stable pseudonymized citizen_id."""

    def __init__(
        self,
        redact_fields: List[str],
        pseudonym_field: str = "national_id",
        salt: str = "lablab-milan-2026",
        audit_log: Optional[AuditLog] = None,
    ) -> None:
        super().__init__(name="privacy", audit_log=audit_log)
        self.redact_fields = redact_fields
        self.pseudonym_field = pseudonym_field
        self.salt = salt

    def _pseudonym(self, value: str) -> str:
        if not value:
            return ""
        digest = hashlib.sha256(f"{self.salt}:{value}".encode("utf-8")).hexdigest()
        return f"cit_{digest[:12]}"

    def _execute(self, payload: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        records: List[Dict[str, Any]] = payload["records"]
        redacted: List[Dict[str, Any]] = []
        redacted_count = 0

        for record in records:
            current = dict(record)
            source_value = current.get(self.pseudonym_field, "")
            current["citizen_id"] = self._pseudonym(source_value)

            for field in self.redact_fields:
                if current.get(field):
                    current[field] = "[REDACTED]"
                    redacted_count += 1

            redacted.append(current)

        return (
            {"records": redacted},
            {"fields_redacted": redacted_count, "records_processed": len(redacted)},
        )
