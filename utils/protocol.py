"""Protocolos e utilitários gerais de rede."""

from __future__ import annotations

import json


def encode_message(message: dict) -> bytes:
    """Serializa a mensagem em JSON."""
    return json.dumps(message, ensure_ascii=False).encode("utf-8")


def decode_message(raw: bytes) -> dict:
    """Desserializa uma mensagem recebida."""
    return json.loads(raw.decode("utf-8"))
