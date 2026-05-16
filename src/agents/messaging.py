"""Multilingual citizen-messaging agent.

Generates citizen-facing notification text per case in the citizen's preferred
language. Currently supports Indonesian (id), English (en), and Italian (it).
"""

from typing import Any, Dict, List, Optional, Tuple

from .base import AuditLog, BaseAgent


TEMPLATES: Dict[str, Dict[str, str]] = {
    "id": {
        "high": (
            "Halo, laporan #{report_id} di {district} terdeteksi prioritas TINGGI "
            "untuk dugaan {condition}. Tim respon cepat akan menghubungi dalam 2 jam. "
            "Tetap di lokasi dan ikuti instruksi petugas."
        ),
        "medium": (
            "Halo, laporan #{report_id} di {district} dijadwalkan konsultasi lanjutan "
            "untuk dugaan {condition} dalam 24 jam. Tim Puskesmas akan menghubungi via telemedicine."
        ),
        "low": (
            "Halo, laporan #{report_id} di {district} dipantau berkala. "
            "Silakan ikuti panduan pencegahan dan hubungi 119 jika gejala memburuk."
        ),
    },
    "en": {
        "high": (
            "Hello, report #{report_id} in {district} has been flagged HIGH priority for "
            "suspected {condition}. A rapid response team will contact you within 2 hours. "
            "Please stay at the location and follow officer instructions."
        ),
        "medium": (
            "Hello, report #{report_id} in {district} has been scheduled for follow-up "
            "consultation for suspected {condition} within 24 hours via telemedicine."
        ),
        "low": (
            "Hello, report #{report_id} in {district} is being monitored. "
            "Please follow the prevention guidelines and call 119 if symptoms worsen."
        ),
    },
    "it": {
        "high": (
            "Salve, la segnalazione #{report_id} a {district} è stata classificata come "
            "priorità ALTA per sospetta {condition}. Una squadra di pronto intervento la "
            "contatterà entro 2 ore. Resti sul posto e segua le istruzioni."
        ),
        "medium": (
            "Salve, la segnalazione #{report_id} a {district} è stata programmata per una "
            "consulenza di follow-up per sospetta {condition} entro 24 ore via telemedicina."
        ),
        "low": (
            "Salve, la segnalazione #{report_id} a {district} è in monitoraggio. "
            "Segua le linee guida di prevenzione e chiami il 119 se i sintomi peggiorano."
        ),
    },
}


class MessagingAgent(BaseAgent):
    def __init__(
        self,
        default_language: str = "id",
        supported_languages: Optional[List[str]] = None,
        audit_log: Optional[AuditLog] = None,
    ) -> None:
        super().__init__(name="messaging", audit_log=audit_log)
        self.default_language = default_language
        self.supported_languages = supported_languages or list(TEMPLATES.keys())

    def _execute(self, payload: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        actions: List[Dict[str, Any]] = payload.get("actions", [])
        messages: List[Dict[str, Any]] = []
        per_language: Dict[str, int] = {}

        for action in actions:
            language = action.get("preferred_language") or self.default_language
            if language not in self.supported_languages:
                language = self.default_language

            priority = action.get("service_priority", "low")
            template = TEMPLATES[language].get(priority, TEMPLATES[language]["low"])
            condition = (action.get("suspected_condition") or "unknown").replace("_", " ")
            district = action.get("district") or "Unknown"
            text = template.format(
                report_id=action.get("report_id", "?"),
                district=district,
                condition=condition,
            )

            messages.append(
                {
                    "report_id": action.get("report_id"),
                    "citizen_id": action.get("citizen_id"),
                    "language": language,
                    "channel": action.get("delivery_channel", "Automated Citizen Messaging"),
                    "priority": priority,
                    "text": text,
                }
            )
            per_language[language] = per_language.get(language, 0) + 1

        return (
            {"messages": messages, "actions": actions, "trends": payload.get("trends", {})},
            {"languages": per_language, "messages_emitted": len(messages)},
        )
