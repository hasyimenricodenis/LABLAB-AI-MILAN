"""LLM-powered briefing agent with deterministic fallback.

Uses Anthropic Claude when ANTHROPIC_API_KEY is set; otherwise renders a
template-based briefing so the workflow remains runnable offline.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple

from .base import AuditLog, BaseAgent


class NarrativeAgent(BaseAgent):
    DEFAULT_MODEL = "claude-haiku-4-5-20251001"

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        max_tokens: int = 512,
        audit_log: Optional[AuditLog] = None,
    ) -> None:
        super().__init__(name="narrative", audit_log=audit_log)
        self.model = model or self.DEFAULT_MODEL
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.max_tokens = max_tokens

    def _execute(self, payload: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        actions: List[Dict[str, Any]] = payload.get("actions", [])
        trends: Dict[str, Any] = payload.get("trends", {})

        high_priority = [a for a in actions if a.get("service_priority") == "high"]
        medium_priority = [a for a in actions if a.get("service_priority") == "medium"]

        stats = {
            "total_cases": len(actions),
            "high_priority": len(high_priority),
            "medium_priority": len(medium_priority),
            "low_priority": len(actions) - len(high_priority) - len(medium_priority),
            "top_districts": trends.get("top_districts", []),
            "top_conditions": trends.get("top_conditions", []),
        }

        if self.api_key:
            briefing, source = self._llm_briefing(stats, high_priority)
        else:
            briefing, source = self._template_briefing(stats, high_priority), "template"

        return (
            {"briefing": briefing, "stats": stats, "actions": actions, "trends": trends},
            {"source": source, "high_priority": stats["high_priority"]},
        )

    def _template_briefing(self, stats: Dict[str, Any], high_priority: List[Dict[str, Any]]) -> str:
        lines = [
            "Public Health Daily Briefing",
            "============================",
            f"Total reports processed: {stats['total_cases']}",
            f"High priority: {stats['high_priority']}  |  Medium: {stats['medium_priority']}  |  Low: {stats['low_priority']}",
            "",
            "Top districts by volume:",
        ]
        for district, count in stats["top_districts"]:
            lines.append(f"  - {district}: {count} reports")

        lines.append("")
        lines.append("Top suspected conditions:")
        for condition, count in stats["top_conditions"]:
            lines.append(f"  - {condition}: {count} reports")

        if high_priority:
            lines.append("")
            lines.append("URGENT cases requiring rapid response:")
            for action in high_priority[:5]:
                lines.append(
                    f"  - {action['report_id']} | {action['district']} | "
                    f"{action['suspected_condition']} | severity={action['symptom_severity']} | "
                    f"risk={action['risk_score']}"
                )

        lines.append("")
        lines.append("Recommendation: dispatch field teams for all high-priority cases within 2 hours.")
        return "\n".join(lines)

    def _llm_briefing(
        self, stats: Dict[str, Any], high_priority: List[Dict[str, Any]]
    ) -> Tuple[str, str]:
        try:
            from anthropic import Anthropic
        except ImportError:
            return self._template_briefing(stats, high_priority), "template-fallback-missing-sdk"

        client = Anthropic(api_key=self.api_key)
        prompt = (
            "You are a public-health analyst writing a 1-page daily briefing for Jakarta city "
            "service teams. Be concise, factual, and action-oriented. No personally identifying data is present.\n\n"
            f"Statistics: {stats}\n\n"
            f"High-priority cases ({len(high_priority)}): {high_priority[:5]}\n\n"
            "Write the briefing in plain English with a short bulleted summary and 3 concrete next actions."
        )

        try:
            message = client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            text = "".join(block.text for block in message.content if getattr(block, "type", "") == "text")
            return text.strip() or self._template_briefing(stats, high_priority), "anthropic"
        except Exception as exc:
            self.logger.warning("LLM call failed, falling back to template: %s", exc)
            return self._template_briefing(stats, high_priority), f"template-fallback-error"
