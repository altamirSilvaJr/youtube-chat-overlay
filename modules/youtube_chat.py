"""Módulo responsável pela coleta de mensagens do chat do YouTube."""

from __future__ import annotations

import json
import os
import threading
import time
from typing import Any
from urllib import parse
from urllib import error, request


class YouTubeChatCollector:
    """Classe base para coleta do chat da live do YouTube."""

    API_BASE_URL = "https://www.googleapis.com/youtube/v3/liveChat/messages"
    VIDEO_API_URL = "https://www.googleapis.com/youtube/v3/videos"

    def __init__(self, live_id: str, api_key: str) -> None:
        self.live_id = live_id
        self.api_key = api_key or self.load_api_key_from_env()
        self.live_chat_id: str | None = None
        self.next_page_token: str | None = None
        self._seen_message_ids: set[str] = set()
        self._polling_thread: threading.Thread | None = None
        self._shutdown = threading.Event()

    def connect(self) -> bool:
        """Valida se a configuração mínima da live e da API foi informada."""
        return bool(self.live_id and self.api_key)

    @staticmethod
    def load_api_key_from_env(env_path: str = ".env") -> str:
        """Lê a API key do ambiente ou de um arquivo .env simples."""
        if os.environ.get("YOUTUBE_API_KEY"):
            return os.environ["YOUTUBE_API_KEY"]

        try:
            with open(env_path, "r", encoding="utf-8") as file:
                for line in file:
                    key, separator, value = line.strip().partition("=")
                    if separator and key == "YOUTUBE_API_KEY":
                        return value.strip().strip('"').strip("'")
        except OSError:
            return ""

        return ""

    @staticmethod
    def extract_video_id(value: str) -> str:
        """Extrai o video_id de uma URL do YouTube ou retorna o valor informado."""
        candidate = (value or "").strip()
        if not candidate:
            return ""

        parsed_url = parse.urlparse(candidate)
        if not parsed_url.netloc:
            return candidate

        query = parse.parse_qs(parsed_url.query)
        if query.get("v"):
            return query["v"][0]

        path_parts = [part for part in parsed_url.path.split("/") if part]
        if parsed_url.netloc.endswith("youtu.be") and path_parts:
            return path_parts[0]
        if "youtube" in parsed_url.netloc and path_parts:
            if path_parts[0] in {"live", "shorts", "embed"} and len(path_parts) > 1:
                return path_parts[1]

        return candidate

    def _get_json(self, url: str) -> dict[str, Any]:
        try:
            with request.urlopen(url, timeout=20) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else str(exc)
            raise RuntimeError(f"Erro ao consultar YouTube: {details}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"Falha de rede ao consultar YouTube: {exc}") from exc

    def fetch_live_chat_id(self) -> str:
        """Resolve o liveChatId a partir do ID/URL do vídeo da live."""
        if not self.connect():
            raise ValueError("Live ID/URL e API key são obrigatórios.")

        video_id = self.extract_video_id(self.live_id)
        params = {
            "part": "liveStreamingDetails",
            "id": video_id,
            "key": self.api_key,
        }
        url = f"{self.VIDEO_API_URL}?{parse.urlencode(params)}"
        payload = self._get_json(url)
        items = payload.get("items", [])
        if not items:
            raise RuntimeError("Live não encontrada pelo YouTube.")

        live_details = items[0].get("liveStreamingDetails", {}) or {}
        live_chat_id = live_details.get("activeLiveChatId")
        if not live_chat_id:
            raise RuntimeError("Chat ao vivo não encontrado. A live pode estar offline ou com chat desativado.")

        self.live_chat_id = str(live_chat_id)
        return self.live_chat_id

    def resolve_live_chat_id(self) -> str:
        """Retorna o liveChatId resolvido e guarda em cache."""
        if self.live_chat_id:
            return self.live_chat_id
        return self.fetch_live_chat_id()

    @staticmethod
    def normalize_message(raw_message: dict[str, Any]) -> dict[str, Any]:
        """Converte uma mensagem bruta da API em um formato padronizado do projeto."""
        if not isinstance(raw_message, dict):
            raise ValueError("A mensagem bruta deve ser um dicionário.")

        snippet = raw_message.get("snippet", {}) or {}
        author_details = raw_message.get("authorDetails", {}) or {}

        message_id = raw_message.get("id") or snippet.get("id") or "unknown-id"
        author = author_details.get("displayName") or "unknown-user"
        text = snippet.get("displayMessage") or ""
        timestamp = snippet.get("publishedAt") or ""
        event_type = snippet.get("type") or "chat_message"

        return {
            "message_id": str(message_id),
            "timestamp": str(timestamp),
            "author": str(author),
            "text": str(text),
            "event_type": "chat_message" if event_type == "textMessageEvent" else str(event_type),
            "metadata": {
                "channel_id": author_details.get("channelId"),
                "message_type": event_type,
            },
        }

    def fetch_messages(self, page_token: str | None = None, live_chat_id: str | None = None) -> dict[str, Any]:
        """Consulta a API do YouTube Live Chat e retorna os itens e metadados da resposta."""
        if not self.connect():
            raise ValueError("Live ID e API key são obrigatórios para buscar mensagens.")

        chat_id = live_chat_id or self.resolve_live_chat_id()
        params = {
            "part": "id,snippet,authorDetails",
            "liveChatId": chat_id,
            "key": self.api_key,
            "maxResults": 200,
        }
        if page_token:
            params["pageToken"] = page_token

        query_string = parse.urlencode(params)
        url = f"{self.API_BASE_URL}?{query_string}"

        payload = self._get_json(url)

        items = payload.get("items", [])
        normalized_items = [self.normalize_message(item) for item in items]

        return {
            "items": normalized_items,
            "next_page_token": payload.get("nextPageToken"),
            "polling_interval_millis": payload.get("pollingIntervalMillis"),
        }

    def poll_once(self) -> list[dict[str, Any]]:
        """Executa uma consulta incremental e retorna somente mensagens ainda não vistas."""
        payload = self.fetch_messages(self.next_page_token)
        self.next_page_token = payload.get("next_page_token")
        messages = []
        for message in payload.get("items", []):
            message_id = message.get("message_id")
            if message_id in self._seen_message_ids:
                continue
            if message_id:
                self._seen_message_ids.add(message_id)
            messages.append(message)
        return messages

    def start_polling(self, on_message, on_error=None) -> None:
        """Inicia polling em thread separada e chama on_message para cada mensagem nova."""
        if self._polling_thread and self._polling_thread.is_alive():
            return

        self._shutdown.clear()

        def run_loop() -> None:
            while not self._shutdown.is_set():
                try:
                    payload = self.fetch_messages(self.next_page_token)
                    self.next_page_token = payload.get("next_page_token")
                    for message in payload.get("items", []):
                        message_id = message.get("message_id")
                        if message_id and message_id in self._seen_message_ids:
                            continue
                        if message_id:
                            self._seen_message_ids.add(message_id)
                        on_message(message)
                    interval = (payload.get("polling_interval_millis") or 3000) / 1000
                except Exception as exc:
                    if on_error is not None:
                        on_error(exc)
                    interval = 5
                self._shutdown.wait(max(1.0, float(interval)))

        self._polling_thread = threading.Thread(target=run_loop, daemon=True)
        self._polling_thread.start()

    def stop_polling(self) -> None:
        """Para o polling de mensagens."""
        self._shutdown.set()
