"""Ponto de entrada principal da aplicação."""

from __future__ import annotations

import sys
from pathlib import Path

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import AppConfig, ConfigManager
from app.runtime import YouTubeOverlayApp
from modules.youtube_chat import YouTubeChatCollector


MODE_OPTIONS = {
    "demo": "Demo",
    "local_overlay": "Coletar YouTube e mostrar neste PC",
    "send_network": "Coletar YouTube e enviar pela rede",
    "receive_network": "Receber da rede e mostrar neste PC",
}

LEGACY_ROLES = {
    "same_pc": "local_overlay",
    "gamer": "send_network",
    "stream": "receive_network",
}


def normalize_role(role: str) -> str:
    normalized = LEGACY_ROLES.get(role, role)
    return normalized if normalized in MODE_OPTIONS else "local_overlay"


class ValueVar:
    """Adaptador pequeno para manter a API get/set usada pelos testes."""

    def __init__(self, value=None):
        self._value = value
        self._callbacks = []

    def set(self, value):
        self._value = value
        for callback in list(self._callbacks):
            callback()

    def get(self):
        return self._value

    def trace_add(self, _mode, callback):
        self._callbacks.append(lambda: callback())


class ConfigurationWindow(QWidget):
    """Janela PyQt de configuração do projeto com suporte a modos de operação."""

    def __init__(self, master: QWidget | None = None, config_path: str | Path | None = None) -> None:
        self._qt_app = QApplication.instance() or QApplication([])
        super().__init__(master)
        self.master = self

        self.config_manager = ConfigManager(config_path or ROOT / "config" / "settings.json")
        saved_config = self.config_manager.config
        saved_api_key = saved_config.youtube_api_key or YouTubeChatCollector.load_api_key_from_env(str(ROOT / ".env"))

        self.role_var = ValueVar(normalize_role(saved_config.role))
        self.live_id_var = ValueVar(saved_config.youtube_live_id)
        self.api_key_var = ValueVar(saved_api_key)
        self.save_api_key_var = ValueVar(saved_config.save_api_key)
        self.enable_overlay_var = ValueVar(saved_config.enable_overlay)
        self.background_transparency_var = ValueVar(saved_config.background_opacity * 100)
        self.overlay_transparency_var = self.background_transparency_var
        self.message_transparency_var = ValueVar(saved_config.message_opacity * 100)
        self.background_opacity_var = self.background_transparency_var
        self.overlay_opacity_var = self.background_transparency_var
        self.message_opacity_var = self.message_transparency_var
        self.background_color_var = ValueVar(saved_config.background_color)
        self.message_box_color_var = ValueVar(saved_config.message_box_color)
        self.message_border_color_var = ValueVar(saved_config.message_border_color)
        self.message_border_width_var = ValueVar(saved_config.message_border_width)
        self.user_name_color_var = ValueVar(saved_config.user_name_color)
        self.message_color_var = ValueVar(saved_config.message_color)
        self.message_font_size_var = ValueVar(saved_config.message_font_size)
        self.max_messages_var = ValueVar(saved_config.max_messages)
        self.message_order_var = ValueVar(self._display_message_order(saved_config.message_order))
        self.server_host_var = ValueVar(saved_config.server_host)
        self.server_port_var = ValueVar(str(saved_config.server_port))
        self.client_host_var = ValueVar(saved_config.client_host)
        self.client_port_var = ValueVar(str(saved_config.client_port))
        self.background_opacity_label_var = ValueVar(f"{int(saved_config.background_opacity * 100)}%")
        self.message_opacity_label_var = ValueVar(f"{int(saved_config.message_opacity * 100)}%")
        self.status_var = ValueVar("Pronto.")

        self.active_overlay_app: YouTubeOverlayApp | None = None
        self._message_pump_active = False
        self._field_bindings: dict[ValueVar, list] = {}
        self.color_swatches: list[tuple[ValueVar, QPushButton]] = []

        self.setWindowTitle("YouTube Overlay - Configuração")
        self.resize(760, 560)
        self.setMinimumSize(720, 520)
        self._build_form()

    def _bind_var(self, var: ValueVar, setter) -> None:
        self._field_bindings.setdefault(var, []).append(setter)

    def _sync_bound_widgets(self, var: ValueVar) -> None:
        for setter in self._field_bindings.get(var, []):
            setter(var.get())

    def _set_var(self, var: ValueVar, value, sync: bool = True) -> None:
        var.set(value)
        if sync:
            self._sync_bound_widgets(var)

    def _build_form(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        self.notebook = QTabWidget(self)
        layout.addWidget(self.notebook, 1)

        live_tab = QWidget()
        appearance_tab = QWidget()
        network_tab = QWidget()
        self.notebook.addTab(live_tab, "Live")
        self.notebook.addTab(appearance_tab, "Aparência")
        self.notebook.addTab(network_tab, "Rede")

        self._build_live_tab(live_tab)
        self._build_appearance_tab(appearance_tab)
        self._build_network_tab(network_tab)

        footer = QGridLayout()
        layout.addLayout(footer)
        self.status_label = QLabel(self.status_var.get())
        footer.addWidget(self.status_label, 0, 0, 1, 3)
        self._bind_var(self.status_var, self.status_label.setText)

        self.start_button = QPushButton("Iniciar overlay")
        self.start_button.clicked.connect(self.start_app)
        save_button = QPushButton("Salvar configuração")
        save_button.clicked.connect(self.save_settings)
        reload_button = QPushButton("Recarregar configuração")
        reload_button.clicked.connect(self.load_settings)
        footer.addWidget(self.start_button, 1, 0)
        footer.addWidget(save_button, 1, 1)
        footer.addWidget(reload_button, 1, 2)

        self._update_opacity_labels()
        self._update_color_swatches()
        self._update_mode_fields()

    def _build_live_tab(self, tab: QWidget) -> None:
        form = QFormLayout(tab)
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        self.role_combo = QComboBox()
        for role, label in MODE_OPTIONS.items():
            self.role_combo.addItem(label, role)
        self.role_combo.setCurrentIndex(max(0, self.role_combo.findData(self.role_var.get())))
        self.role_combo.currentIndexChanged.connect(self._on_role_changed)
        form.addRow("Modo de operação:", self.role_combo)

        self.live_id_input = QLineEdit(self.live_id_var.get())
        self.live_id_input.textChanged.connect(self.live_id_var.set)
        form.addRow("Live ID do YouTube:", self.live_id_input)

        self.api_key_input = QLineEdit(self.api_key_var.get())
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.api_key_input.textChanged.connect(self.api_key_var.set)
        form.addRow("API Key:", self.api_key_input)

        self.save_api_key_check = QCheckBox("Salvar API key no JSON")
        self.save_api_key_check.setChecked(bool(self.save_api_key_var.get()))
        self.save_api_key_check.toggled.connect(self.save_api_key_var.set)
        form.addRow("", self.save_api_key_check)

        self.enable_overlay_check = QCheckBox("Ativar overlay na tela de transmissão")
        self.enable_overlay_check.setChecked(bool(self.enable_overlay_var.get()))
        self.enable_overlay_check.toggled.connect(self.enable_overlay_var.set)
        form.addRow("", self.enable_overlay_check)

        self._bind_var(self.role_var, self._set_role_combo_value)
        self._bind_var(self.live_id_var, self.live_id_input.setText)
        self._bind_var(self.api_key_var, self.api_key_input.setText)
        self._bind_var(self.save_api_key_var, self.save_api_key_check.setChecked)
        self._bind_var(self.enable_overlay_var, self.enable_overlay_check.setChecked)

    def _build_appearance_tab(self, tab: QWidget) -> None:
        form = QFormLayout(tab)
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        self.background_opacity_spin = self._add_percent_spin(form, "Opacidade do fundo:", self.background_transparency_var)
        self.message_opacity_spin = self._add_percent_spin(form, "Opacidade das caixas:", self.message_transparency_var)
        self._add_color_row(form, "Cor do fundo:", self.background_color_var)
        self._add_color_row(form, "Cor das caixas:", self.message_box_color_var)
        self._add_color_row(form, "Cor da borda:", self.message_border_color_var)

        self.message_border_width_spin = self._add_int_spin(form, "Espessura da borda:", self.message_border_width_var, 0, 10)
        self._add_color_row(form, "Cor do usuário:", self.user_name_color_var)
        self._add_color_row(form, "Cor da mensagem:", self.message_color_var)
        self.message_font_size_spin = self._add_int_spin(form, "Tamanho da fonte:", self.message_font_size_var, 9, 28)
        self.max_messages_spin = self._add_int_spin(form, "Mensagens visíveis:", self.max_messages_var, 1, 50)

        self.order_combo = QComboBox()
        self.order_combo.addItems(["No topo", "Embaixo"])
        self.order_combo.setCurrentText(self.message_order_var.get())
        self.order_combo.currentTextChanged.connect(lambda value: (self.message_order_var.set(value), self._on_style_changed()))
        form.addRow("Novas mensagens:", self.order_combo)
        self._bind_var(self.message_order_var, self.order_combo.setCurrentText)

    def _build_network_tab(self, tab: QWidget) -> None:
        layout = QVBoxLayout(tab)

        self.stream_network_frame = QGroupBox("Receber mensagens neste PC")
        stream_form = QFormLayout(self.stream_network_frame)
        self.server_host_input = QLineEdit(self.server_host_var.get())
        self.server_host_input.textChanged.connect(self.server_host_var.set)
        self.server_port_input = QLineEdit(self.server_port_var.get())
        self.server_port_input.textChanged.connect(self.server_port_var.set)
        stream_form.addRow("Host para escutar:", self.server_host_input)
        stream_form.addRow("Porta para escutar:", self.server_port_input)

        self.gamer_network_frame = QGroupBox("Enviar mensagens para outro PC")
        gamer_form = QFormLayout(self.gamer_network_frame)
        self.client_host_input = QLineEdit(self.client_host_var.get())
        self.client_host_input.textChanged.connect(self.client_host_var.set)
        self.client_port_input = QLineEdit(self.client_port_var.get())
        self.client_port_input.textChanged.connect(self.client_port_var.set)
        gamer_form.addRow("Host de destino:", self.client_host_input)
        gamer_form.addRow("Porta de destino:", self.client_port_input)

        layout.addWidget(self.stream_network_frame)
        layout.addWidget(self.gamer_network_frame)
        layout.addStretch(1)

        self._bind_var(self.server_host_var, self.server_host_input.setText)
        self._bind_var(self.server_port_var, self.server_port_input.setText)
        self._bind_var(self.client_host_var, self.client_host_input.setText)
        self._bind_var(self.client_port_var, self.client_port_input.setText)

    def _add_percent_spin(self, form: QFormLayout, label: str, var: ValueVar) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(0, 100)
        spin.setDecimals(0)
        spin.setSuffix("%")
        spin.setValue(float(var.get()))
        spin.valueChanged.connect(lambda value: (var.set(value), self._on_opacity_slider_changed(value)))
        form.addRow(label, spin)
        self._bind_var(var, lambda value, widget=spin: widget.setValue(float(value)))
        return spin

    def _add_int_spin(self, form: QFormLayout, label: str, var: ValueVar, minimum: int, maximum: int) -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(minimum, maximum)
        spin.setValue(int(var.get()))
        spin.valueChanged.connect(lambda value: (var.set(value), self._on_style_changed()))
        form.addRow(label, spin)
        self._bind_var(var, lambda value, widget=spin: widget.setValue(int(value)))
        return spin

    def _add_color_row(self, form: QFormLayout, label: str, var: ValueVar) -> None:
        row = QHBoxLayout()
        swatch = QPushButton()
        swatch.setFixedSize(32, 26)
        swatch.clicked.connect(lambda: self._pick_color(var))
        entry = QLineEdit(var.get())
        entry.textChanged.connect(lambda value: (var.set(value), self._on_color_changed()))
        row.addWidget(swatch)
        row.addWidget(entry, 1)
        wrapper = QFrame()
        wrapper.setLayout(row)
        form.addRow(label, wrapper)
        self.color_swatches.append((var, swatch))
        self._bind_var(var, entry.setText)

    def _on_color_changed(self) -> None:
        self._update_color_swatches()
        self._on_style_changed()

    def _update_color_swatches(self) -> None:
        for var, swatch in self.color_swatches:
            color = var.get().strip() or "#000000"
            swatch.setStyleSheet(f"background-color: {color}; border: 1px solid #4b5563;")

    def _on_opacity_slider_changed(self, value) -> None:
        self._update_opacity_labels()
        self._on_style_changed(float(value))

    def _update_opacity_labels(self) -> None:
        self.background_opacity_label_var.set(f"{int(float(self.background_transparency_var.get()))}%")
        self.message_opacity_label_var.set(f"{int(float(self.message_transparency_var.get()))}%")

    def _update_mode_fields(self) -> None:
        role = normalize_role(self.role_var.get())
        self.stream_network_frame.setVisible(role == "receive_network")
        self.gamer_network_frame.setVisible(role == "send_network")

    def _on_role_changed(self, index: int) -> None:
        self.role_var.set(self.role_combo.itemData(index))
        self._update_mode_fields()

    def _set_role_combo_value(self, role: str) -> None:
        index = self.role_combo.findData(normalize_role(role))
        if index >= 0:
            self.role_combo.setCurrentIndex(index)

    def _pick_color(self, var: ValueVar) -> None:
        color = QColorDialog.getColor()
        if color.isValid():
            self._set_var(var, color.name())
            self._on_color_changed()

    def collect_values(self) -> dict:
        """Coleta os valores de configuração do formulário."""
        background_transparency = self._normalize_transparency_value(self.background_transparency_var.get())
        message_transparency = self._normalize_transparency_value(self.message_transparency_var.get())
        return {
            "role": normalize_role(self.role_var.get()),
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
        self._set_var(self.role_var, normalize_role(config.role))
        self._set_var(self.live_id_var, config.youtube_live_id)
        self._set_var(self.save_api_key_var, config.save_api_key)
        if config.youtube_api_key:
            self._set_var(self.api_key_var, config.youtube_api_key)
        elif not self.api_key_var.get():
            self._set_var(self.api_key_var, YouTubeChatCollector.load_api_key_from_env(str(ROOT / ".env")))
        self._set_var(self.enable_overlay_var, config.enable_overlay)
        self._set_var(self.background_transparency_var, config.background_opacity * 100)
        self._set_var(self.message_transparency_var, config.message_opacity * 100)
        self._set_var(self.background_color_var, config.background_color)
        self._set_var(self.message_box_color_var, config.message_box_color)
        self._set_var(self.message_border_color_var, config.message_border_color)
        self._set_var(self.message_border_width_var, config.message_border_width)
        self._set_var(self.user_name_color_var, config.user_name_color)
        self._set_var(self.message_color_var, config.message_color)
        self._set_var(self.message_font_size_var, config.message_font_size)
        self._set_var(self.max_messages_var, config.max_messages)
        self._set_var(self.message_order_var, self._display_message_order(config.message_order))
        self._set_var(self.server_host_var, config.server_host)
        self._set_var(self.server_port_var, str(config.server_port))
        self._set_var(self.client_host_var, config.client_host)
        self._set_var(self.client_port_var, str(config.client_port))
        self._update_opacity_labels()
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
        self._set_var(self.status_var, message)

    def _capture_active_overlay_geometry(self) -> None:
        if self.active_overlay_app is None or self.active_overlay_app.overlay_window is None:
            return

        root = self.active_overlay_app.overlay_window.root
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
        if self.active_overlay_app is None or self._message_pump_active:
            return
        self._message_pump_active = True
        QTimer.singleShot(100, self._pump_pending_messages)

    def _pump_pending_messages(self) -> None:
        self._message_pump_active = False
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
        self.close()

    def closeEvent(self, event) -> None:
        self._close_active_overlay()
        event.accept()

    def _close_active_overlay(self) -> None:
        """Fecha a janela do overlay se ela estiver aberta."""
        if self.active_overlay_app is None:
            return

        self._capture_active_overlay_geometry()
        self.active_overlay_app.stop()
        overlay_window = self.active_overlay_app.overlay_window
        if overlay_window is not None:
            overlay_window.close()

        self.active_overlay_app = None
        self._message_pump_active = False
        self.config_manager.save(self._build_app_config())
        self.start_button.setText("Iniciar overlay")

    def start_app(self) -> None:
        """Alterna a abertura do overlay: abre se estiver fechado e fecha se já estiver aberto."""
        if self.active_overlay_app is not None:
            self._close_active_overlay()
            return

        config = self.collect_values()
        role = normalize_role(config["role"])

        if role == "receive_network":
            mode = "server"
            host = config["server_host"]
            port = config["server_port"]
        elif role == "send_network":
            mode = "client"
            host = config["client_host"]
            port = config["client_port"]
        elif role == "local_overlay":
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
            self.start_button.setText("Fechar overlay")
            if app.overlay_window is not None:
                app.overlay_window.root.update_idletasks()
            self._schedule_message_pump()
            return

        self.active_overlay_app = None
        self.start_button.setText("Iniciar overlay")


def launch_config_window() -> None:
    """Abre a janela principal de configuração."""
    app = QApplication.instance() or QApplication(sys.argv)
    window = ConfigurationWindow()
    window.show()
    app.exec_()


def main() -> None:
    """Inicializa a janela de configuração da aplicação."""
    launch_config_window()


if __name__ == "__main__":
    main()
