"""Módulo responsável pela renderização do overlay."""

from __future__ import annotations

from typing import Any


class OverlayRenderer:
    """Renderiza mensagens em uma área de overlay."""

    def __init__(
        self,
        width: int = 500,
        height: int = 300,
        opacity: float = 0.9,
        max_messages: int = 10,
        message_order: str = "top_down",
    ) -> None:
        self.width = width
        self.height = height
        self.opacity = opacity
        self.max_messages = max_messages
        self.message_order = message_order
        self.history_limit = max(200, max_messages)
        self.messages: list[dict[str, Any]] = []

    def add_message(self, message: dict[str, Any]) -> None:
        """Adiciona uma mensagem ao final da fila e mantém só as mais recentes."""
        if not isinstance(message, dict):
            return

        message_id = message.get("message_id")
        fingerprint = (
            str(message.get("author", "")),
            str(message.get("text", "")),
            str(message.get("timestamp", "")),
        )

        for index, existing in enumerate(self.messages):
            existing_id = existing.get("message_id") if isinstance(existing, dict) else None
            if message_id is not None and existing_id == message_id:
                self.messages[index] = message
                return

            if isinstance(existing, dict):
                existing_fingerprint = (
                    str(existing.get("author", "")),
                    str(existing.get("text", "")),
                    str(existing.get("timestamp", "")),
                )
                if existing_fingerprint == fingerprint:
                    self.messages[index] = message
                    return

        self.messages.append(message)
        if len(self.messages) > self.history_limit:
            self.messages = self.messages[-self.history_limit :]

    def render(self) -> list[dict[str, Any]]:
        """Retorna as mensagens atuais para renderização."""
        visible_messages = list(self.messages[-self.max_messages :])
        if self.message_order == "down_top":
            return list(reversed(visible_messages))
        return visible_messages

    def clear(self) -> None:
        """Limpa o overlay."""
        self.messages.clear()
