"""Schema de mensagem do chat e utilitários de validação."""

from __future__ import annotations

from datetime import datetime, timezone


def build_message(author: str, text: str, event_type: str = "chat_message") -> dict:
    """Cria um payload de mensagem padronizado."""
    return {
        "message_id": f"msg-{datetime.now(timezone.utc).timestamp():.0f}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "author": author,
        "text": text,
        "event_type": event_type,
        "metadata": {},
    }


def validate_message(message: dict) -> bool:
    """Valida campos mínimos da mensagem."""
    required = {"message_id", "timestamp", "author", "text", "event_type"}
    return isinstance(message, dict) and required.issubset(message.keys())
