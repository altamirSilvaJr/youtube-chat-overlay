"""Runtime orchestration for the YouTube overlay application."""

from __future__ import annotations

import queue

from modules.network_client import ChatClient
from modules.network_server import ChatServer
from modules.overlay import OverlayRenderer
from modules.overlay_window import TransparentOverlayWindow
from modules.youtube_chat import YouTubeChatCollector


class YouTubeOverlayApp:
    """Orquestra o fluxo principal do projeto com suporte a múltiplos modos de operação."""

    def __init__(
        self,
        live_id: str = "",
        api_key: str = "",
        host: str = "127.0.0.1",
        port: int = 9000,
        mode: str = "demo",
        overlay_enabled: bool = True,
        overlay_width: int = 500,
        overlay_height: int = 300,
        overlay_x: int = 100,
        overlay_y: int = 100,
        overlay_opacity: float = 0.9,
        background_opacity: float | None = None,
        message_opacity: float = 0.9,
        background_color: str = "#0b0b0f",
        message_box_color: str = "#111827",
        message_border_color: str = "#4b5563",
        message_border_width: int = 1,
        user_name_color: str = "#f3f4f6",
        message_color: str = "#e5e7eb",
        message_font_size: int = 12,
        max_messages: int = 10,
        message_order: str = "top_down",
    ) -> None:
        self.live_id = live_id
        self.api_key = api_key
        self.host = host
        self.port = port
        self.mode = mode
        self.overlay_enabled = overlay_enabled
        self.overlay_width = overlay_width
        self.overlay_height = overlay_height
        self.overlay_x = overlay_x
        self.overlay_y = overlay_y
        self.overlay_opacity = overlay_opacity
        self.background_opacity = overlay_opacity if background_opacity is None else background_opacity
        self.message_opacity = message_opacity
        self.background_color = background_color
        self.message_box_color = message_box_color
        self.message_border_color = message_border_color
        self.message_border_width = message_border_width
        self.user_name_color = user_name_color
        self.message_color = message_color
        self.message_font_size = message_font_size
        self.max_messages = max_messages
        self.message_order = message_order

        self.collector = YouTubeChatCollector(live_id, api_key)
        self.pending_messages: queue.Queue[dict] = queue.Queue()
        self.pending_statuses: queue.Queue[str] = queue.Queue()
        self.renderer = OverlayRenderer(
            width=overlay_width,
            height=overlay_height,
            opacity=overlay_opacity,
            max_messages=max_messages,
            message_order=message_order,
        )
        self.overlay_window: TransparentOverlayWindow | None = None
        self._runtime_started = False

        if mode == "server":
            self.server = ChatServer(host=host, port=port)
            self.client = None
        else:
            self.server = None
            self.client = ChatClient(host=host, port=port)

    def build_runtime_config(self) -> dict:
        """Retorna a configuração ativa do runtime da aplicação."""
        return {
            "live_id": self.live_id,
            "api_key": self.api_key,
            "host": self.host,
            "port": self.port,
            "mode": self.mode,
            "overlay_enabled": self.overlay_enabled,
            "overlay_width": self.overlay_width,
            "overlay_height": self.overlay_height,
            "overlay_x": self.overlay_x,
            "overlay_y": self.overlay_y,
            "overlay_opacity": self.overlay_opacity,
            "background_opacity": self.background_opacity,
            "message_opacity": self.message_opacity,
            "background_color": self.background_color,
            "message_box_color": self.message_box_color,
            "message_border_color": self.message_border_color,
            "message_border_width": self.message_border_width,
            "user_name_color": self.user_name_color,
            "message_color": self.message_color,
            "message_font_size": self.message_font_size,
            "max_messages": self.max_messages,
            "message_order": self.message_order,
        }

    def _set_status(self, message: str) -> None:
        self.pending_statuses.put(message)

    def create_overlay_window(self) -> TransparentOverlayWindow:
        """Cria a janela transparente do overlay para exibição no streaming."""
        self.overlay_window = TransparentOverlayWindow(
            width=self.overlay_width,
            height=self.overlay_height,
            opacity=self.background_opacity,
            max_messages=self.max_messages,
            x_offset=self.overlay_x,
            y_offset=self.overlay_y,
            background_opacity=self.background_opacity,
            message_opacity=self.message_opacity,
            background_color=self.background_color,
            message_box_color=self.message_box_color,
            message_border_color=self.message_border_color,
            message_border_width=self.message_border_width,
            user_name_color=self.user_name_color,
            message_color=self.message_color,
            message_font_size=self.message_font_size,
            message_order=self.message_order,
        )
        return self.overlay_window

    def run_preview(self) -> None:
        """Abre uma janela de preview do overlay com mensagens demo para simulação."""
        if not self.overlay_enabled:
            print("Overlay está desabilitado na configuração.")
            return

        if self.overlay_window is None:
            self.create_overlay_window()

        demo_messages = [
            {"author": "01 usuario1", "text": "Olá galera!"},
            {"author": "02 usuario2", "text": "Partida começando!"},
            {"author": "03 streamer", "text": "Acompanhem os próximos momentos!"},
            {"author": "04 moderação", "text": "Lembrem de manter o respeito no chat."},
            {"author": "05 speedfan", "text": "Esse trecho ficou muito bom."},
            {"author": "06 nightbot", "text": "Siga o canal para receber aviso das próximas lives."},
            {"author": "07 ana", "text": "Qual configuração você está usando hoje?"},
            {"author": "08 bruno", "text": "Overlay está bem legível agora."},
            {"author": "09 carlos", "text": "Manda salve para a galera do Discord!"},
            {"author": "10 streamer", "text": "Valeu demais por acompanharem a live."},
        ]

        for message in demo_messages:
            self.overlay_window.add_message(message)

        self.overlay_window.root.update_idletasks()
        print("Preview do overlay aberto com mensagens de demonstração.")

    def _handle_incoming_message(self, message: dict) -> None:
        self.pending_messages.put(message)

    def process_pending_messages(self) -> int:
        """Renderiza mensagens pendentes na thread da interface."""
        processed = 0
        while True:
            try:
                message = self.pending_messages.get_nowait()
            except queue.Empty:
                break

            self._render_message(message)
            processed += 1

        return processed

    def process_pending_statuses(self) -> str | None:
        """Retorna o status mais recente pendente."""
        latest_status = None
        while True:
            try:
                latest_status = self.pending_statuses.get_nowait()
            except queue.Empty:
                break
        return latest_status

    def _render_message(self, message: dict) -> None:
        if self.overlay_enabled:
            if self.overlay_window is None:
                self.create_overlay_window()
            self.overlay_window.add_message(message)
            self.overlay_window.root.update_idletasks()
        else:
            self.renderer.add_message(message)

    def _handle_collector_error(self, exc: Exception) -> None:
        message = self.translate_runtime_error(exc)
        self._set_status(message)
        print(message)

    @staticmethod
    def translate_runtime_error(exc: Exception) -> str:
        raw = str(exc)
        lowered = raw.lower()
        if "api key not valid" in lowered or "keyinvalid" in lowered or "forbidden" in lowered:
            return "API key inválida ou sem permissão para YouTube Data API."
        if "quota" in lowered:
            return "Cota da YouTube Data API excedida."
        if "chat ao vivo não encontrado" in lowered or "activeLiveChatId" in raw:
            return "Chat ao vivo não encontrado. Verifique se a live está ao vivo e com chat ativo."
        if "live não encontrada" in lowered:
            return "Live não encontrada. Confira o link ou ID informado."
        if "falha de rede" in lowered:
            return "Falha de rede ao consultar o YouTube. Tentando novamente."
        return f"Erro no coletor do YouTube: {exc}"

    def run_youtube_to_overlay(self) -> None:
        """Coleta chat do YouTube e renderiza localmente."""
        if not self.collector.connect():
            self._set_status("Live ID/URL e API key são obrigatórios.")
            return
        if self.overlay_enabled and self.overlay_window is None:
            self.create_overlay_window()
        self._set_status("Conectando ao chat do YouTube...")
        self.collector.start_polling(self._handle_incoming_message, self._handle_collector_error)
        self._runtime_started = True
        self._set_status("Coleta do chat do YouTube iniciada.")
        print("Coleta do chat do YouTube iniciada.")

    def run_youtube_to_network(self) -> None:
        """Coleta chat do YouTube e envia para outro computador via TCP."""
        if not self.collector.connect():
            self._set_status("Live ID/URL e API key são obrigatórios.")
            return
        connected = self.client.connect()
        if not connected:
            self._set_status(f"Não foi possível conectar ao servidor em {self.host}:{self.port}")
            return

        def send_message(message: dict) -> None:
            self.client.send_message(message)

        self._set_status("Conectado ao PC de destino. Iniciando YouTube...")
        self.collector.start_polling(send_message, self._handle_collector_error)
        self._runtime_started = True
        self._set_status(f"Cliente conectado em {self.host}:{self.port}; coleta iniciada.")
        print(f"Cliente conectado em {self.host}:{self.port}; coleta do YouTube iniciada.")

    def run(self) -> None:
        """Executa o modo ativo da aplicação."""
        if self.mode == "demo":
            self.run_preview()
            return

        if self.mode == "same_pc":
            if self.collector.connect():
                self.run_youtube_to_overlay()
            elif self.overlay_enabled:
                self.run_preview()
            else:
                print("Modo same_pc ativo sem overlay.")
            return

        if self.mode == "server":
            if self.overlay_enabled and self.overlay_window is None:
                self.create_overlay_window()
            self.server.on_message = self._handle_incoming_message
            self.server.start()
            self._runtime_started = True
            self._set_status(f"Servidor TCP escutando em {self.host}:{self.server.port}.")
            print(f"Servidor TCP inicializado em {self.host}:{self.port}")
            return

        if self.mode == "client" and self.collector.connect():
            self.run_youtube_to_network()
            return

        connected = self.client.connect()
        if not connected:
            self._set_status(f"Não foi possível conectar ao servidor em {self.host}:{self.port}")
            print(f"Não foi possível conectar ao servidor em {self.host}:{self.port}")
            return

        print(f"Cliente conectado em {self.host}:{self.port}")

        message_payload = {
            "message_id": "demo-message",
            "timestamp": "2026-09-12T12:00:00Z",
            "author": "streamer",
            "text": "Mensagem de teste do overlay",
            "event_type": "chat_message",
            "metadata": {},
        }
        self.client.send_message(message_payload)

        if self.overlay_enabled:
            if self.overlay_window is None:
                self.create_overlay_window()
            self.overlay_window.add_message(message_payload)
            self.overlay_window.root.update_idletasks()
        else:
            self.renderer.add_message(message_payload)

        print("Mensagem de teste enviada com sucesso.")

    def stop(self) -> None:
        """Encerra recursos ativos do runtime."""
        self.collector.stop_polling()
        if self.client is not None:
            self.client.close()
        if self.server is not None:
            self.server.stop()


