import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class AuditEntry:
    agent: str
    started_at: str
    finished_at: str
    duration_ms: int
    input_count: int
    output_count: int
    notes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResult:
    name: str
    payload: Dict[str, Any]
    audit: Optional[AuditEntry] = None


class AuditLog:
    """In-memory audit trail. Each workflow run gets a fresh trace_id."""

    def __init__(self) -> None:
        self.trace_id = str(uuid.uuid4())
        self.entries: List[AuditEntry] = []

    def record(self, entry: AuditEntry) -> None:
        self.entries.append(entry)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "entries": [entry.__dict__ for entry in self.entries],
        }


class BaseAgent:
    def __init__(self, name: str, audit_log: Optional[AuditLog] = None) -> None:
        self.name = name
        self.audit_log = audit_log
        self.logger = logging.getLogger(f"agent.{name}")

    def run(self, payload: Dict[str, Any]) -> AgentResult:
        started = time.perf_counter()
        started_at = datetime.now(timezone.utc).isoformat()
        input_count = self._count(payload)

        result_payload, notes = self._execute(payload)

        finished_at = datetime.now(timezone.utc).isoformat()
        duration_ms = int((time.perf_counter() - started) * 1000)
        output_count = self._count(result_payload)

        entry = AuditEntry(
            agent=self.name,
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=duration_ms,
            input_count=input_count,
            output_count=output_count,
            notes=notes,
        )
        if self.audit_log is not None:
            self.audit_log.record(entry)

        self.logger.info(
            "agent=%s input=%d output=%d duration_ms=%d notes=%s",
            self.name,
            input_count,
            output_count,
            duration_ms,
            notes,
        )

        return AgentResult(name=self.name, payload=result_payload, audit=entry)

    def _execute(self, payload: Dict[str, Any]) -> tuple[Dict[str, Any], Dict[str, Any]]:
        raise NotImplementedError("Agent must implement _execute().")

    @staticmethod
    def _count(payload: Dict[str, Any]) -> int:
        for key in ("records", "actions", "messages"):
            value = payload.get(key) if isinstance(payload, dict) else None
            if isinstance(value, list):
                return len(value)
        return 0
