"""Gerenciamento de configuração da aplicação."""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


@dataclass
class AppConfig:
    """Configuração principal do sistema."""
    role: str = "same_pc"
    youtube_live_id: str = ""
    youtube_api_key: str = ""
    save_api_key: bool = False
    enable_overlay: bool = True
    server_host: str = "127.0.0.1"
    server_port: int = 9000
    client_host: str = "127.0.0.1"
    client_port: int = 9000
    overlay_width: int = 500
    overlay_height: int = 300
    overlay_x: int = 100
    overlay_y: int = 100
    overlay_opacity: float = 0.9
    background_opacity: float = 0.9
    message_opacity: float = 0.9
    background_color: str = "#0b0b0f"
    message_box_color: str = "#111827"
    message_border_color: str = "#4b5563"
    message_border_width: int = 1
    user_name_color: str = "#f3f4f6"
    message_color: str = "#e5e7eb"
    message_font_size: int = 12
    max_messages: int = 10
    message_order: str = "top_down"
    theme_name: str = "dark"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ConfigManager:
    """Lê e salva a configuração em um arquivo JSON."""

    def __init__(self, file_path: str | Path) -> None:
        self.file_path = Path(file_path)
        self.config = AppConfig()
        self.load()

    def load(self) -> AppConfig:
        if not self.file_path.exists():
            return self.config

        with self.file_path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        valid_keys = AppConfig.__dataclass_fields__.keys()
        filtered_data = {key: value for key, value in data.items() if key in valid_keys}
        self.config = AppConfig(**filtered_data)
        return self.config

    def save(self, config: AppConfig | None = None) -> None:
        if config is not None:
            self.config = config
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        with self.file_path.open("w", encoding="utf-8") as file:
            json.dump(self.config.to_dict(), file, indent=2)
