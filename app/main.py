"""Ponto de entrada principal da aplicação."""

from __future__ import annotations

import queue
import sys
import tkinter as tk
from pathlib import Path
from tkinter import colorchooser, ttk

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import AppConfig, ConfigManager
from modules.network_client import ChatClient
from modules.network_server import ChatServer
from modules.overlay import OverlayRenderer
from modules.overlay_window import TransparentOverlayWindow
from modules.youtube_chat import YouTubeChatCollector


class DummyVar:
    """Estrutura mínima para simular StringVar/BooleanVar em ambientes sem Tk completo."""

    def __init__(self, value=None):
        self._value = value

    def set(self, value):
        self._value = value

    def get(self):
        return self._value


class DummyRoot:
    """Implementa um stub leve para permitir testes headless de UI e overlay."""

    def __init__(self):
        self._destroyed = False

    def title(self, *_args, **_kwargs):
        return None

    def geometry(self, *_args, **_kwargs):
        return None

    def overrideredirect(self, *_args, **_kwargs):
        return None

    def attributes(self, *_args, **_kwargs):
        return None

    def configure(self, *_args, **_kwargs):
        return None

    def protocol(self, *_args, **_kwargs):
        return None

    def update_idletasks(self, *_args, **_kwargs):
        return None

    def destroy(self):
        self._destroyed = True

    def mainloop(self):
        return None

    def winfo_exists(self):
        return not self._destroyed


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
        status_callback=None,
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
        self.status_callback = status_callback

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
        if self.status_callback is not None:
            self.status_callback(message)

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

        self._set_status("Conectado ao PC de stream. Iniciando YouTube...")
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


class ConfigurationWindow:
    """Janela padrão de configuração do projeto com suporte a modos de operação."""

    def __init__(self, master: tk.Tk | None = None, config_path: str | Path | None = None) -> None:
        try:
            self.master = master or tk.Tk()
            self._headless = False
        except tk.TclError:
            self.master = master or DummyRoot()
            self._headless = True

        self.config_manager = ConfigManager(config_path or ROOT / "config" / "settings.json")
        saved_config = self.config_manager.config
        saved_api_key = saved_config.youtube_api_key or YouTubeChatCollector.load_api_key_from_env(str(ROOT / ".env"))

        if not self._headless:
            self.master.title("YouTube Overlay - Configuração")
            self.master.geometry("760x560")
            self.master.minsize(720, 520)

        self.role_var = tk.StringVar(value=saved_config.role) if not self._headless else DummyVar(saved_config.role)
        self.live_id_var = tk.StringVar(value=saved_config.youtube_live_id) if not self._headless else DummyVar(saved_config.youtube_live_id)
        self.api_key_var = tk.StringVar(value=saved_api_key) if not self._headless else DummyVar(saved_api_key)
        self.save_api_key_var = tk.BooleanVar(value=saved_config.save_api_key) if not self._headless else DummyVar(saved_config.save_api_key)
        self.enable_overlay_var = tk.BooleanVar(value=saved_config.enable_overlay) if not self._headless else DummyVar(saved_config.enable_overlay)
        self.background_transparency_var = tk.DoubleVar(value=saved_config.background_opacity * 100) if not self._headless else DummyVar(saved_config.background_opacity * 100)
        self.overlay_transparency_var = self.background_transparency_var
        self.message_transparency_var = tk.DoubleVar(value=saved_config.message_opacity * 100) if not self._headless else DummyVar(saved_config.message_opacity * 100)
        self.background_opacity_var = self.background_transparency_var
        self.overlay_opacity_var = self.background_transparency_var
        self.message_opacity_var = self.message_transparency_var
        self.background_color_var = tk.StringVar(value=saved_config.background_color) if not self._headless else DummyVar(saved_config.background_color)
        self.message_box_color_var = tk.StringVar(value=saved_config.message_box_color) if not self._headless else DummyVar(saved_config.message_box_color)
        self.message_border_color_var = tk.StringVar(value=saved_config.message_border_color) if not self._headless else DummyVar(saved_config.message_border_color)
        self.message_border_width_var = tk.IntVar(value=saved_config.message_border_width) if not self._headless else DummyVar(saved_config.message_border_width)
        self.user_name_color_var = tk.StringVar(value=saved_config.user_name_color) if not self._headless else DummyVar(saved_config.user_name_color)
        self.message_color_var = tk.StringVar(value=saved_config.message_color) if not self._headless else DummyVar(saved_config.message_color)
        self.message_font_size_var = tk.IntVar(value=saved_config.message_font_size) if not self._headless else DummyVar(saved_config.message_font_size)
        self.max_messages_var = tk.IntVar(value=saved_config.max_messages) if not self._headless else DummyVar(saved_config.max_messages)
        self.message_order_var = tk.StringVar(value=self._display_message_order(saved_config.message_order)) if not self._headless else DummyVar(self._display_message_order(saved_config.message_order))
        self.server_host_var = tk.StringVar(value=saved_config.server_host) if not self._headless else DummyVar(saved_config.server_host)
        self.server_port_var = tk.StringVar(value=str(saved_config.server_port)) if not self._headless else DummyVar(str(saved_config.server_port))
        self.client_host_var = tk.StringVar(value=saved_config.client_host) if not self._headless else DummyVar(saved_config.client_host)
        self.client_port_var = tk.StringVar(value=str(saved_config.client_port)) if not self._headless else DummyVar(str(saved_config.client_port))
        self.background_opacity_label_var = tk.StringVar(value=f"{int(saved_config.background_opacity * 100)}%") if not self._headless else DummyVar(f"{int(saved_config.background_opacity * 100)}%")
        self.message_opacity_label_var = tk.StringVar(value=f"{int(saved_config.message_opacity * 100)}%") if not self._headless else DummyVar(f"{int(saved_config.message_opacity * 100)}%")
        self.status_var = tk.StringVar(value="Pronto.") if not self._headless else DummyVar("Pronto.")

        self.active_overlay_app: YouTubeOverlayApp | None = None
        self._message_pump_id = None

        if not self._headless:
            self._build_form()
            self.master.protocol("WM_DELETE_WINDOW", self.close_window)

    def _build_form(self) -> None:
        if self._headless:
            return

        self.master.columnconfigure(0, weight=1)
        self.master.rowconfigure(0, weight=1)

        notebook = ttk.Notebook(self.master)
        notebook.grid(row=0, column=0, padx=12, pady=12, sticky="nsew")
        self.notebook = notebook

        live_tab = ttk.Frame(notebook, padding=14)
        appearance_tab = ttk.Frame(notebook, padding=14)
        network_tab = ttk.Frame(notebook, padding=14)
        notebook.add(live_tab, text="Live")
        notebook.add(appearance_tab, text="Aparencia")
        notebook.add(network_tab, text="Rede")

        footer = ttk.Frame(self.master, padding=(12, 0, 12, 12))
        footer.grid(row=1, column=0, sticky="ew")
        footer.columnconfigure(0, weight=1)
        footer.columnconfigure(1, weight=1)
        footer.columnconfigure(2, weight=1)

        for tab in (live_tab, appearance_tab, network_tab):
            tab.columnconfigure(1, weight=1)

        ttk.Label(live_tab, text="Modo de operação:").grid(row=0, column=0, padx=0, pady=8, sticky="w")
        role_combo = ttk.Combobox(
            live_tab,
            textvariable=self.role_var,
            values=["same_pc", "gamer", "stream", "demo"],
            state="readonly",
        )
        role_combo.set("same_pc")
        role_combo.grid(row=0, column=1, padx=(12, 0), pady=8, sticky="ew")

        ttk.Label(live_tab, text="Live ID do YouTube:").grid(row=1, column=0, padx=0, pady=8, sticky="w")
        ttk.Entry(live_tab, textvariable=self.live_id_var).grid(row=1, column=1, padx=(12, 0), pady=8, sticky="ew")

        ttk.Label(live_tab, text="API Key:").grid(row=2, column=0, padx=0, pady=8, sticky="w")
        ttk.Entry(live_tab, textvariable=self.api_key_var, show="*").grid(row=2, column=1, padx=(12, 0), pady=8, sticky="ew")

        ttk.Checkbutton(
            live_tab,
            text="Salvar API key no JSON",
            variable=self.save_api_key_var,
            onvalue=True,
            offvalue=False,
        ).grid(row=3, column=0, columnspan=2, padx=0, pady=8, sticky="w")

        ttk.Checkbutton(
            live_tab,
            text="Ativar overlay na tela de transmissão",
            variable=self.enable_overlay_var,
            onvalue=True,
            offvalue=False,
        ).grid(row=4, column=0, columnspan=2, padx=0, pady=12, sticky="w")

        ttk.Label(appearance_tab, text="Opacidade do fundo:").grid(row=0, column=0, padx=0, pady=8, sticky="w")
        background_transparency_slider = ttk.Scale(
            appearance_tab,
            from_=0,
            to_=100,
            orient="horizontal",
            variable=self.background_transparency_var,
            command=lambda value: self._on_opacity_slider_changed(value),
        )
        background_transparency_slider.grid(row=0, column=1, padx=(12, 8), pady=8, sticky="ew")
        ttk.Label(appearance_tab, textvariable=self.background_opacity_label_var, width=5).grid(row=0, column=2, pady=8, sticky="e")
        self.background_transparency_slider = background_transparency_slider

        ttk.Label(appearance_tab, text="Opacidade das caixas:").grid(row=1, column=0, padx=0, pady=8, sticky="w")
        message_transparency_slider = ttk.Scale(
            appearance_tab,
            from_=0,
            to_=100,
            orient="horizontal",
            variable=self.message_transparency_var,
            command=lambda value: self._on_opacity_slider_changed(value),
        )
        message_transparency_slider.grid(row=1, column=1, padx=(12, 8), pady=8, sticky="ew")
        ttk.Label(appearance_tab, textvariable=self.message_opacity_label_var, width=5).grid(row=1, column=2, pady=8, sticky="e")
        self.message_transparency_slider = message_transparency_slider

        self._add_color_row(appearance_tab, 2, "Cor do fundo:", self.background_color_var)
        self._add_color_row(appearance_tab, 3, "Cor das caixas:", self.message_box_color_var)
        self._add_color_row(appearance_tab, 4, "Cor da borda:", self.message_border_color_var)

        ttk.Label(appearance_tab, text="Espessura da borda:").grid(row=5, column=0, padx=0, pady=8, sticky="w")
        ttk.Spinbox(appearance_tab, from_=0, to_=10, textvariable=self.message_border_width_var, width=8).grid(row=5, column=1, padx=(12, 0), pady=8, sticky="w")
        self.message_border_width_var.trace_add("write", lambda *_: self._on_style_changed())

        self._add_color_row(appearance_tab, 6, "Cor do usuário:", self.user_name_color_var)
        self._add_color_row(appearance_tab, 7, "Cor da mensagem:", self.message_color_var)

        ttk.Label(appearance_tab, text="Tamanho da fonte:").grid(row=8, column=0, padx=0, pady=8, sticky="w")
        ttk.Spinbox(appearance_tab, from_=9, to_=28, textvariable=self.message_font_size_var, width=8).grid(row=8, column=1, padx=(12, 0), pady=8, sticky="w")
        self.message_font_size_var.trace_add("write", lambda *_: self._on_style_changed())

        ttk.Label(appearance_tab, text="Mensagens visíveis:").grid(row=9, column=0, padx=0, pady=8, sticky="w")
        ttk.Spinbox(appearance_tab, from_=1, to_=50, textvariable=self.max_messages_var, width=8).grid(row=9, column=1, padx=(12, 0), pady=8, sticky="w")
        self.max_messages_var.trace_add("write", lambda *_: self._on_style_changed())

        ttk.Label(appearance_tab, text="Novas mensagens:").grid(row=10, column=0, padx=0, pady=8, sticky="w")
        order_combo = ttk.Combobox(
            appearance_tab,
            textvariable=self.message_order_var,
            values=["No topo", "Embaixo"],
            state="readonly",
        )
        order_combo.grid(row=10, column=1, padx=(12, 0), pady=8, sticky="ew")
        self.message_order_var.trace_add("write", lambda *_: self._on_style_changed())

        self.stream_network_frame = ttk.LabelFrame(network_tab, text="Computador de stream", padding=12)
        self.stream_network_frame.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 12))
        self.stream_network_frame.columnconfigure(1, weight=1)
        ttk.Label(self.stream_network_frame, text="Host do servidor:").grid(row=0, column=0, pady=6, sticky="w")
        ttk.Entry(self.stream_network_frame, textvariable=self.server_host_var).grid(row=0, column=1, padx=(12, 0), pady=6, sticky="ew")
        ttk.Label(self.stream_network_frame, text="Porta do servidor:").grid(row=1, column=0, pady=6, sticky="w")
        ttk.Entry(self.stream_network_frame, textvariable=self.server_port_var).grid(row=1, column=1, padx=(12, 0), pady=6, sticky="ew")

        self.gamer_network_frame = ttk.LabelFrame(network_tab, text="Computador gamer", padding=12)
        self.gamer_network_frame.grid(row=1, column=0, columnspan=3, sticky="ew")
        self.gamer_network_frame.columnconfigure(1, weight=1)
        ttk.Label(self.gamer_network_frame, text="Host do stream:").grid(row=0, column=0, pady=6, sticky="w")
        ttk.Entry(self.gamer_network_frame, textvariable=self.client_host_var).grid(row=0, column=1, padx=(12, 0), pady=6, sticky="ew")
        ttk.Label(self.gamer_network_frame, text="Porta do stream:").grid(row=1, column=0, pady=6, sticky="w")
        ttk.Entry(self.gamer_network_frame, textvariable=self.client_port_var).grid(row=1, column=1, padx=(12, 0), pady=6, sticky="ew")

        ttk.Label(footer, textvariable=self.status_var, anchor="w").grid(row=0, column=0, columnspan=3, pady=(0, 8), sticky="ew")
        self.start_button = ttk.Button(footer, text="Iniciar overlay", command=self.start_app)
        self.start_button.grid(row=1, column=0, padx=(0, 8), sticky="ew")
        ttk.Button(footer, text="Salvar configuração", command=self.save_settings).grid(row=1, column=1, padx=4, sticky="ew")
        ttk.Button(footer, text="Recarregar configuração", command=self.load_settings).grid(row=1, column=2, padx=(8, 0), sticky="ew")

        self.role_var.trace_add("write", lambda *_: self._update_mode_fields())
        self._update_opacity_labels()
        self._update_color_swatches()
        self._update_mode_fields()

    def _add_color_row(self, parent: ttk.Frame, row: int, label: str, var: tk.StringVar) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, padx=0, pady=8, sticky="w")
        swatch = tk.Button(
            parent,
            width=3,
            relief="solid",
            borderwidth=1,
            bg=var.get(),
            activebackground=var.get(),
            command=lambda: self._pick_color(var),
        )
        swatch.grid(row=row, column=1, padx=(12, 8), pady=8, sticky="w")
        ttk.Entry(parent, textvariable=var).grid(row=row, column=1, padx=(54, 0), pady=8, sticky="ew")
        if not hasattr(self, "color_swatches"):
            self.color_swatches = []
        self.color_swatches.append((var, swatch))
        var.trace_add("write", lambda *_: self._on_color_changed())

    def _on_color_changed(self) -> None:
        self._update_color_swatches()
        self._on_style_changed()

    def _update_color_swatches(self) -> None:
        for var, swatch in getattr(self, "color_swatches", []):
            color = var.get().strip() or "#000000"
            try:
                swatch.configure(bg=color, activebackground=color)
            except tk.TclError:
                swatch.configure(bg="#000000", activebackground="#000000")

    def _on_opacity_slider_changed(self, value) -> None:
        self._update_opacity_labels()
        self._on_style_changed(float(value))

    def _update_opacity_labels(self) -> None:
        self.background_opacity_label_var.set(f"{int(float(self.background_transparency_var.get()))}%")
        self.message_opacity_label_var.set(f"{int(float(self.message_transparency_var.get()))}%")

    def _update_mode_fields(self) -> None:
        role = self.role_var.get()
        if role == "gamer":
            self.stream_network_frame.grid_remove()
            self.gamer_network_frame.grid()
        elif role == "stream":
            self.gamer_network_frame.grid_remove()
            self.stream_network_frame.grid()
        else:
            self.stream_network_frame.grid()
            self.gamer_network_frame.grid_remove()

    def _pick_color(self, var: tk.StringVar) -> None:
        """Abre o seletor de cores e atualiza a variável correspondente."""
        if self._headless:
            return
        color = colorchooser.askcolor(title="Escolha uma cor", color=var.get())
        if color and color[1]:
            var.set(color[1])

    def collect_values(self) -> dict:
        """Coleta os valores de configuração do formulário."""
        background_transparency = self._normalize_transparency_value(self.background_transparency_var.get())
        message_transparency = self._normalize_transparency_value(self.message_transparency_var.get())
        return {
            "role": self.role_var.get(),
            "live_id": self.live_id_var.get().strip(),
            "api_key": self.api_key_var.get().strip(),
            "enable_overlay": self.enable_overlay_var.get(),
            "overlay_transparency": background_transparency,
            "background_transparency": background_transparency,
            "message_transparency": message_transparency,
            "overlay_opacity": background_transparency,
            "background_opacity": background_transparency,
            "message_opacity": message_transparency,
            "background_color": self.background_color_var.get().strip() or "#0b0b0f",
            "message_box_color": self.message_box_color_var.get().strip() or "#111827",
            "message_border_color": self.message_border_color_var.get().strip() or "#4b5563",
            "message_border_width": int(self.message_border_width_var.get() or 1),
            "user_name_color": self.user_name_color_var.get().strip() or "#f3f4f6",
            "message_color": self.message_color_var.get().strip() or "#e5e7eb",
            "message_font_size": int(self.message_font_size_var.get() or 12),
            "max_messages": int(self.max_messages_var.get() or 10),
            "message_order": self._normalize_message_order(self.message_order_var.get()),
            "server_host": self.server_host_var.get().strip() or "127.0.0.1",
            "server_port": int(self.server_port_var.get() or 9000),
            "client_host": self.client_host_var.get().strip() or "127.0.0.1",
            "client_port": int(self.client_port_var.get() or 9000),
        }

    def _normalize_transparency_value(self, value) -> float:
        """Aceita valor em porcentagem 0-100 ou escala 0-1 e retorna 0-1 para o runtime."""
        transparency = float(value or 0.0)
        if transparency > 1.0:
            transparency = transparency / 100.0
        return max(0.0, min(1.0, transparency))

    def _normalize_message_order(self, value: str) -> str:
        """Converte a escolha visual de posição das mensagens novas para o valor interno."""
        if value in ("No topo", "down_top"):
            return "down_top"
        return "top_down"

    def _display_message_order(self, value: str) -> str:
        return "No topo" if value == "down_top" else "Embaixo"

    def _build_app_config(self) -> AppConfig:
        values = self.collect_values()
        self._capture_active_overlay_geometry()
        return AppConfig(
            role=values["role"],
            youtube_live_id=values["live_id"],
            youtube_api_key=values["api_key"] if self.save_api_key_var.get() else "",
            save_api_key=bool(self.save_api_key_var.get()),
            enable_overlay=values["enable_overlay"],
            server_host=values["server_host"],
            server_port=values["server_port"],
            client_host=values["client_host"],
            client_port=values["client_port"],
            overlay_width=self.config_manager.config.overlay_width,
            overlay_height=self.config_manager.config.overlay_height,
            overlay_x=self.config_manager.config.overlay_x,
            overlay_y=self.config_manager.config.overlay_y,
            overlay_opacity=values["background_opacity"],
            background_opacity=values["background_opacity"],
            message_opacity=values["message_opacity"],
            background_color=values["background_color"],
            message_box_color=values["message_box_color"],
            message_border_color=values["message_border_color"],
            message_border_width=values["message_border_width"],
            user_name_color=values["user_name_color"],
            message_color=values["message_color"],
            message_font_size=values["message_font_size"],
            max_messages=values["max_messages"],
            message_order=values["message_order"],
        )

    def _apply_app_config(self, config: AppConfig) -> None:
        self.role_var.set(config.role)
        self.live_id_var.set(config.youtube_live_id)
        self.save_api_key_var.set(config.save_api_key)
        if config.youtube_api_key:
            self.api_key_var.set(config.youtube_api_key)
        elif not self.api_key_var.get():
            self.api_key_var.set(YouTubeChatCollector.load_api_key_from_env(str(ROOT / ".env")))
        self.enable_overlay_var.set(config.enable_overlay)
        self.background_transparency_var.set(config.background_opacity * 100)
        self.message_transparency_var.set(config.message_opacity * 100)
        self.background_color_var.set(config.background_color)
        self.message_box_color_var.set(config.message_box_color)
        self.message_border_color_var.set(config.message_border_color)
        self.message_border_width_var.set(config.message_border_width)
        self.user_name_color_var.set(config.user_name_color)
        self.message_color_var.set(config.message_color)
        self.message_font_size_var.set(config.message_font_size)
        self.max_messages_var.set(config.max_messages)
        self.message_order_var.set(self._display_message_order(config.message_order))
        self.server_host_var.set(config.server_host)
        self.server_port_var.set(str(config.server_port))
        self.client_host_var.set(config.client_host)
        self.client_port_var.set(str(config.client_port))
        self._update_opacity_labels()
        if not self._headless:
            self._update_color_swatches()
            self._update_mode_fields()
        self._on_style_changed()

    def save_settings(self) -> None:
        """Salva a configuração atual em JSON."""
        self.config_manager.save(self._build_app_config())
        self._set_status("Configuração salva.")

    def load_settings(self) -> None:
        """Recarrega o JSON salvo e aplica os valores na interface."""
        self._apply_app_config(self.config_manager.load())
        self._set_status("Configuração recarregada.")

    def _set_status(self, message: str) -> None:
        self.status_var.set(message)

    def _capture_active_overlay_geometry(self) -> None:
        if self.active_overlay_app is None or self.active_overlay_app.overlay_window is None:
            return

        overlay_window = self.active_overlay_app.overlay_window
        root = overlay_window.root
        try:
            overlay_x = int(root.winfo_x())
            overlay_y = int(root.winfo_y())
            overlay_width = int(root.winfo_width())
            overlay_height = int(root.winfo_height())
        except Exception:
            try:
                overlay_x = int(root.x())
                overlay_y = int(root.y())
                overlay_width = int(root.width())
                overlay_height = int(root.height())
            except Exception:
                return

        self.config_manager.config.overlay_x = overlay_x
        self.config_manager.config.overlay_y = overlay_y
        self.config_manager.config.overlay_width = overlay_width
        self.config_manager.config.overlay_height = overlay_height
        self.active_overlay_app.overlay_x = overlay_x
        self.active_overlay_app.overlay_y = overlay_y
        self.active_overlay_app.overlay_width = overlay_width
        self.active_overlay_app.overlay_height = overlay_height

    def _schedule_message_pump(self) -> None:
        if self._headless or self.active_overlay_app is None:
            return
        if self._message_pump_id is None:
            self._message_pump_id = self.master.after(100, self._pump_pending_messages)

    def _pump_pending_messages(self) -> None:
        self._message_pump_id = None
        if self.active_overlay_app is None:
            return
        latest_status = self.active_overlay_app.process_pending_statuses()
        if latest_status:
            self._set_status(latest_status)
        self.active_overlay_app.process_pending_messages()
        self._schedule_message_pump()

    def _on_style_changed(self, value=None) -> None:
        """Atualiza os estilos do overlay em tempo real quando os controles mudarem."""
        if self.active_overlay_app is None:
            return

        config = self.collect_values()
        app = self.active_overlay_app
        app.overlay_opacity = self._normalize_transparency_value(config["background_transparency"])
        app.background_opacity = self._normalize_transparency_value(config["background_transparency"])
        app.message_opacity = self._normalize_transparency_value(config["message_transparency"])
        app.background_color = config["background_color"]
        app.message_box_color = config["message_box_color"]
        app.message_border_color = config["message_border_color"]
        app.message_border_width = config["message_border_width"]
        app.user_name_color = config["user_name_color"]
        app.message_color = config["message_color"]
        app.message_font_size = config["message_font_size"]
        app.max_messages = config["max_messages"]
        app.message_order = config["message_order"]

        if app.overlay_window is None:
            return

        overlay = app.overlay_window
        overlay.opacity = app.overlay_opacity
        overlay.background_opacity = app.background_opacity
        overlay.message_opacity = app.message_opacity
        overlay.background_color = app.background_color
        overlay.message_box_color = app.message_box_color
        overlay.message_border_color = app.message_border_color
        overlay.message_border_width = app.message_border_width
        overlay.user_name_color = app.user_name_color
        overlay.message_color = app.message_color
        overlay.message_font_size = app.message_font_size
        overlay.max_messages = app.max_messages
        overlay.message_order = app.message_order
        if hasattr(overlay, "renderer"):
            overlay.renderer.max_messages = app.max_messages
            overlay.renderer.message_order = app.message_order
            overlay.refresh()
        if hasattr(overlay, "_impl"):
            overlay._impl.opacity = app.overlay_opacity
            overlay._impl.background_opacity = app.background_opacity
            overlay._impl.message_opacity = app.message_opacity
            overlay._impl.background_color = app.background_color
            overlay._impl.message_box_color = app.message_box_color
            overlay._impl.message_border_color = app.message_border_color
            overlay._impl.message_border_width = app.message_border_width
            overlay._impl.user_name_color = app.user_name_color
            overlay._impl.message_color = app.message_color
            overlay._impl.message_font_size = app.message_font_size
            overlay._impl.max_messages = app.max_messages
            overlay._impl.message_order = app.message_order
            overlay._impl.renderer.max_messages = app.max_messages
            overlay._impl.renderer.message_order = app.message_order
            overlay._impl.refresh()
        overlay.apply_theme()

    def apply_transparency_from_slider(self) -> None:
        """Aplica a transparência atual da barra ao overlay ativo."""
        value = float(self.background_transparency_var.get())
        if self.active_overlay_app is not None:
            self.active_overlay_app.overlay_opacity = self._normalize_transparency_value(value)
            self.active_overlay_app.background_opacity = self._normalize_transparency_value(value)
        self._on_style_changed(value)

    def apply_opacity_from_slider(self) -> None:
        """Alias de compatibilidade para a nomenclatura anterior."""
        self.apply_transparency_from_slider()

    def close_window(self) -> None:
        """Fecha o overlay vinculado e encerra a janela de configuração."""
        self._close_active_overlay()
        if not self._headless and hasattr(self.master, "destroy"):
            self.master.destroy()

    def _close_active_overlay(self) -> None:
        """Fecha a janela do overlay se ela estiver aberta."""
        if self.active_overlay_app is None:
            return

        self._capture_active_overlay_geometry()
        self.active_overlay_app.stop()
        overlay_window = self.active_overlay_app.overlay_window
        if overlay_window is not None and overlay_window.root.winfo_exists():
            overlay_window.close()

        self.active_overlay_app = None
        self._message_pump_id = None
        self.config_manager.save(self._build_app_config())
        if not self._headless and hasattr(self, "start_button"):
            self.start_button.configure(text="Iniciar overlay")

    def start_app(self) -> None:
        """Alterna a abertura do overlay: abre se estiver fechado e fecha se já estiver aberto."""
        if self.active_overlay_app is not None:
            self._close_active_overlay()
            return

        config = self.collect_values()
        role = config["role"]

        if role == "stream":
            mode = "server"
            host = config["server_host"]
            port = config["server_port"]
        elif role == "gamer":
            mode = "client"
            host = config["client_host"]
            port = config["client_port"]
        elif role == "same_pc":
            mode = "same_pc"
            host = config["server_host"]
            port = config["server_port"]
        else:
            mode = "demo"
            host = config["server_host"]
            port = config["server_port"]

        app = YouTubeOverlayApp(
            live_id=config["live_id"],
            api_key=config["api_key"],
            host=host,
            port=port,
            mode=mode,
            overlay_enabled=config["enable_overlay"],
            overlay_width=self.config_manager.config.overlay_width,
            overlay_height=self.config_manager.config.overlay_height,
            overlay_x=self.config_manager.config.overlay_x,
            overlay_y=self.config_manager.config.overlay_y,
            overlay_opacity=config["background_opacity"],
            background_opacity=config["background_opacity"],
            message_opacity=config["message_opacity"],
            background_color=config["background_color"],
            message_box_color=config["message_box_color"],
            message_border_color=config["message_border_color"],
            message_border_width=config["message_border_width"],
            user_name_color=config["user_name_color"],
            message_color=config["message_color"],
            message_font_size=config["message_font_size"],
            max_messages=config["max_messages"],
            message_order=config["message_order"],
        )
        app.run()
        latest_status = app.process_pending_statuses()
        if latest_status:
            self._set_status(latest_status)

        if app.overlay_window is not None or app._runtime_started:
            self.active_overlay_app = app
            if not self._headless and hasattr(self, "start_button"):
                self.start_button.configure(text="Fechar overlay")
            if app.overlay_window is not None:
                app.overlay_window.root.update_idletasks()
            self._schedule_message_pump()
            return

        self.active_overlay_app = None
        if not self._headless and hasattr(self, "start_button"):
            self.start_button.configure(text="Iniciar overlay")


def launch_config_window() -> None:
    """Abre a janela principal de configuração."""
    root = tk.Tk()
    ConfigurationWindow(root)
    root.mainloop()


def main() -> None:
    """Inicializa a janela de configuração da aplicação."""
    launch_config_window()


if __name__ == "__main__":
    main()
