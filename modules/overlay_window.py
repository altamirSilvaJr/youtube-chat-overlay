"""Janela transparente para renderizar o overlay do chat em streaming."""

from __future__ import annotations

import html
import os
import tkinter as tk
from typing import Any

from modules.overlay import OverlayRenderer

# Evita forçar o PyQt em modo offscreen em janelas normais do desktop.
# O modo headless só deve ser ativado explicitamente em testes/CI.
if os.environ.get("PYTHONOVERLAY_HEADLESS") == "1":
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PyQt5.QtCore import Qt
    from PyQt5.QtGui import QColor
    from PyQt5.QtWidgets import QApplication, QFrame, QLabel, QSizePolicy, QVBoxLayout, QWidget
except Exception:  # pragma: no cover - fallback para ambientes sem PyQt
    QApplication = None
    Qt = None
    QColor = None
    QFrame = QLabel = QSizePolicy = QVBoxLayout = QWidget = None


class DummyRoot:
    """Stub mínimo para ambientes sem Tk funcional."""

    def __init__(self):
        self._destroyed = False
        self._width = 500
        self._height = 300

    def title(self, *_args, **_kwargs):
        return None

    def geometry(self, value=None, *_args, **_kwargs):
        if value is None:
            return f"{self._width}x{self._height}"
        if "x" in value:
            size, _, pos = value.partition("+")
            width, _, height = size.partition("x")
            self._width = int(width)
            self._height = int(height)
        return None

    def overrideredirect(self, *_args, **_kwargs):
        return None

    def attributes(self, *_args, **_kwargs):
        return None

    def configure(self, *_args, **_kwargs):
        return None

    def bind(self, *_args, **_kwargs):
        return None

    def protocol(self, *_args, **_kwargs):
        return None

    def update_idletasks(self, *_args, **_kwargs):
        return None

    def winfo_rootx(self):
        return 100

    def winfo_rooty(self):
        return 100

    def destroy(self):
        self._destroyed = True

    def mainloop(self):
        return None

    def winfo_exists(self):
        return not self._destroyed

    def winfo_width(self):
        return self._width

    def winfo_height(self):
        return self._height

    def winfo_x(self):
        return 100

    def winfo_y(self):
        return 100


class DummyWidget:
    """Widget mínimo para testes e ambientes headless."""

    def __init__(self, value=None):
        self._value = value
        self._children = []

    def __getitem__(self, key):
        return self._value if key == "text" else None

    def pack(self, *_args, **_kwargs):
        return None

    def place(self, *_args, **_kwargs):
        return None

    def grid(self, *_args, **_kwargs):
        return None

    def winfo_children(self):
        return list(self._children)

    def configure(self, *_args, **_kwargs):
        return None

    def destroy(self):
        return None


class ResizableOverlayWidget(QWidget):
    """Widget que permite arrastar e redimensionar a janela transparente do overlay."""

    def __init__(self, overlay):
        super().__init__()
        self.overlay = overlay
        self._dragging = False
        self._resizing = False
        self._drag_start_pos = None
        self._drag_start_geometry = None
        self._resize_start_pos = None
        self._resize_start_size = None
        self._resize_border = 18
        self.setMouseTracking(True)

    def _handle_mouse_press(self, event):
        if event.button() != Qt.LeftButton:
            return

        pos = event.pos()
        if pos.x() >= self.width() - self._resize_border or pos.y() >= self.height() - self._resize_border:
            self._resizing = True
            self._resize_start_pos = event.globalPos()
            self._resize_start_size = self.size()
            self.setCursor(Qt.SizeFDiagCursor)
            return

        self._dragging = True
        self._drag_start_pos = event.globalPos()
        self._drag_start_geometry = self.frameGeometry().topLeft()

    def _handle_mouse_move(self, event):
        if self._resizing and self._resize_start_pos is not None:
            delta = event.globalPos() - self._resize_start_pos
            new_width = max(220, self._resize_start_size.width() + delta.x())
            new_height = max(140, self._resize_start_size.height() + delta.y())
            self.resize(new_width, new_height)
            self.overlay.width = int(new_width)
            self.overlay.height = int(new_height)
            self.overlay.container.setGeometry(0, 0, new_width, new_height)
            self.overlay.messages_container.setGeometry(
                self.overlay.horizontal_padding,
                self.overlay.vertical_padding,
                max(120, new_width - self.overlay.horizontal_padding * 2),
                max(80, new_height - self.overlay.vertical_padding * 2),
            )
            self.overlay.refresh()
            return

        if self._dragging and self._drag_start_pos is not None:
            delta = event.globalPos() - self._drag_start_pos
            new_pos = self._drag_start_geometry + delta
            self.move(new_pos)
            return

        pos = event.pos()
        if pos.x() >= self.width() - self._resize_border or pos.y() >= self.height() - self._resize_border:
            self.setCursor(Qt.SizeFDiagCursor)
        else:
            self.setCursor(Qt.ArrowCursor)

    def _handle_mouse_release(self, event):
        self._dragging = False
        self._resizing = False
        self._drag_start_pos = None
        self._drag_start_geometry = None
        self._resize_start_pos = None
        self._resize_start_size = None
        self.setCursor(Qt.ArrowCursor)

    def mousePressEvent(self, event):
        self._handle_mouse_press(event)

    def mouseMoveEvent(self, event):
        self._handle_mouse_move(event)

    def mouseReleaseEvent(self, event):
        self._handle_mouse_release(event)


class PyQtOverlayWindow:
    """Backend do overlay em PyQt para permitir transparência real por widget."""

    def __init__(self, width=500, height=300, opacity=0.9, max_messages=10, x_offset=100, y_offset=100,
                 background_opacity=None, message_opacity=0.9, background_color="#0b0b0f",
                 message_box_color="#111827", message_border_color="#4b5563", message_border_width=1,
                 user_name_color="#f3f4f6", message_color="#e5e7eb", message_font_size=12,
                 message_order="top_down") -> None:
        self.width = width
        self.height = height
        self.opacity = opacity
        self.background_opacity = opacity if background_opacity is None else background_opacity
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
        self.x_offset = x_offset
        self.y_offset = y_offset
        self.horizontal_padding = 18
        self.vertical_padding = 12
        self._headless = False
        self._resize_active = False
        self._drag_active = False
        self._last_pointer = (0, 0)
        self._initial_size = (width, height)
        self._start_pointer = (0, 0)
        self._start_geometry = (x_offset, y_offset, width, height)
        self._drag_start = (0, 0)
        self._drag_origin = (x_offset, y_offset)
        self._resize_border_threshold = 14
        self._rendered_message_heights: list[int] = []
        self._app = QApplication.instance() or QApplication([])

        self.root = ResizableOverlayWidget(self)
        self.root.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.root.setAttribute(Qt.WA_TranslucentBackground, True)
        self.root.setGeometry(x_offset, y_offset, width, height)
        self.root.setStyleSheet("background: transparent; border: none;")
        self.root.setMouseTracking(True)

        self.container = QWidget(self.root)
        self.container.setGeometry(0, 0, width, height)
        self.container.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.container.setStyleSheet(
            f"background-color: rgba({self._hex_to_rgb(self.background_color)}, {max(0.0, min(1.0, self.background_opacity))}); border: none;"
        )

        self.messages_container = QWidget(self.container)
        self.messages_container.setGeometry(self.horizontal_padding, self.vertical_padding,
                                            max(120, width - self.horizontal_padding * 2),
                                            max(80, height - self.vertical_padding * 2))
        self.messages_container.setStyleSheet("background: transparent; border: none;")
        self.messages_container.setAttribute(Qt.WA_TranslucentBackground, True)
        self.messages_container.setAttribute(Qt.WA_TransparentForMouseEvents, True)

        self._messages_layout = QVBoxLayout(self.messages_container)
        self._messages_layout.setContentsMargins(0, 0, 0, 0)
        self._messages_layout.setSpacing(12)
        self._messages_layout.setAlignment(self._layout_alignment())
        self.messages_container.setLayout(self._messages_layout)

        self._message_box_style = (
            f"background-color: {self.set_color_with_alpha(self.message_box_color, max(0.18, min(1.0, self.message_opacity)))}; "
            f"border: {max(0, int(self.message_border_width))}px solid {self.message_border_color}; border-radius: 8px; margin: 0px; padding: 0px;"
        )
        self.resize_handle = None
        self.renderer = OverlayRenderer(width=width, height=height, opacity=opacity, max_messages=max_messages, message_order=message_order)
        self.root.winfo_rootx = lambda: self.root.x()
        self.root.winfo_rooty = lambda: self.root.y()
        self.root.winfo_width = lambda: self.root.width()
        self.root.winfo_height = lambda: self.root.height()
        self.root.winfo_x = lambda: self.root.x()
        self.root.winfo_y = lambda: self.root.y()
        self.root.winfo_exists = lambda: True
        self.root.update_idletasks = self.update_idletasks
        self.root.destroy = self.close
        self.root.show()

    @staticmethod
    def _hex_to_rgb(hex_color: str) -> str:
        value = (hex_color or "#000000").strip()
        if not value.startswith("#"):
            return "0, 0, 0, 255"
        value = value[1:]
        if len(value) == 3:
            value = "".join(ch * 2 for ch in value)
        if len(value) != 6:
            return "0, 0, 0, 255"
        r = int(value[0:2], 16)
        g = int(value[2:4], 16)
        b = int(value[4:6], 16)
        return f"{r}, {g}, {b}"

    def set_color_with_alpha(self, color: str, alpha: float) -> str:
        r, g, b = [int(part.strip()) for part in self._hex_to_rgb(color).split(",")[:3]]
        alpha_value = max(0, min(1.0, float(alpha)))
        return f"rgba({r}, {g}, {b}, {int(alpha_value * 255)})"

    def update_idletasks(self):
        self._app.processEvents()

    def _layout_alignment(self):
        return Qt.AlignTop if self.message_order == "down_top" else Qt.AlignBottom

    def _sync_dynamic_height(self):
        self._messages_layout.activate()
        self.update_idletasks()

        visible_count = len(self._rendered_message_heights)
        content_height = sum(self._rendered_message_heights)
        if visible_count > 1:
            content_height += self._messages_layout.spacing() * (visible_count - 1)

        desired_height = max(80, content_height + self.vertical_padding * 2)
        old_height = self.height
        self.height = int(desired_height)
        new_y = self.root.y()
        if self.message_order == "top_down":
            new_y = self.root.y() + old_height - self.height

        self.root.setGeometry(self.root.x(), new_y, self.width, self.height)
        self.container.setGeometry(0, 0, self.width, self.height)
        self.messages_container.setGeometry(
            self.horizontal_padding,
            self.vertical_padding,
            max(120, self.width - self.horizontal_padding * 2),
            max(40, self.height - self.vertical_padding * 2),
        )

    def apply_theme(self):
        transparent_background = self.set_color_with_alpha(self.background_color, self.background_opacity)
        transparent_box = self.set_color_with_alpha(self.message_box_color, self.message_opacity)
        self.root.setStyleSheet("background: rgba(0, 0, 0, 0); border: none;")
        self.container.setStyleSheet(
            f"background-color: {transparent_background}; border: none; border-radius: 10px;"
        )
        self.messages_container.setStyleSheet("background: transparent; border: none;")
        self._message_box_style = (
            f"background-color: {transparent_box}; "
            f"border: {max(0, int(self.message_border_width))}px solid {self.message_border_color}; "
            "border-radius: 8px; margin: 0px; padding: 0px;"
        )
        self.refresh()

    def _on_root_press(self, event=None):
        return None

    def _on_root_drag(self, event=None):
        return None

    def _on_root_release(self, event=None):
        return None

    def _on_border_motion(self, event=None):
        return None

    @staticmethod
    def format_message(message: dict[str, Any]) -> str:
        author = str(message.get("author", "Usuário"))
        text = str(message.get("text", ""))
        return f"{author}: {text}" if text else author

    def refresh(self):
        self._messages_layout.setAlignment(self._layout_alignment())
        self.messages_container.setGeometry(
            self.horizontal_padding,
            self.vertical_padding,
            max(120, self.width - self.horizontal_padding * 2),
            max(40, self.height - self.vertical_padding * 2),
        )

        while self._messages_layout.count():
            item = self._messages_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()
        self._rendered_message_heights.clear()
        self.update_idletasks()

        for message in self.renderer.render():
            author = str(message.get("author", "Usuário"))
            text = str(message.get("text", ""))

            message_block = QWidget(self.messages_container)
            message_block.setAttribute(Qt.WA_TranslucentBackground, False)
            message_block.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            message_block.setAutoFillBackground(True)
            message_block.setStyleSheet(self._message_box_style)
            message_block.setContentsMargins(0, 0, 0, 0)
            message_block.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)

            block_layout = QVBoxLayout(message_block)
            block_layout.setContentsMargins(5, 5, 5, 5)
            block_layout.setSpacing(0)

            author_html = html.escape(author)
            text_html = html.escape(text)
            content_label = QLabel(
                f"<span style='color:{self.user_name_color}; font-weight:700;'>{author_html}:</span>"
                f"<br><span style='color:{self.message_color};'>{text_html}</span>"
            )
            content_label.setStyleSheet(
                f"color: {self.message_color}; background: transparent; border: none; font-size: {max(9, int(self.message_font_size))}px; font-family: 'Segoe UI'; padding: 0px; margin: 0px; line-height: 1.25;"
            )
            content_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            content_label.setWordWrap(True)
            content_label.setContentsMargins(3, 0, 3, 0)
            content_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
            content_label.setFixedWidth(max(80, self.messages_container.width() - 16))
            block_layout.addWidget(content_label)
            content_label.adjustSize()
            label_height = content_label.sizeHint().height()
            message_height = label_height + block_layout.contentsMargins().top() + block_layout.contentsMargins().bottom()
            message_block.setFixedHeight(message_height)
            self._rendered_message_heights.append(message_height)

            self._messages_layout.addWidget(message_block)

        self._sync_dynamic_height()
        self.update_idletasks()

    def add_message(self, message: dict[str, Any]):
        self.renderer.add_message(message)
        self.refresh()

    def run(self):
        self.root.show()
        self.update_idletasks()

    def close(self):
        self.root.close()


class TransparentOverlayWindow:
    """Cria uma janela leve e transparente para exibição do chat em streaming."""

    def __init__(
        self,
        width: int = 500,
        height: int = 300,
        opacity: float = 0.9,
        max_messages: int = 10,
        x_offset: int = 100,
        y_offset: int = 100,
        background_opacity: float | None = None,
        message_opacity: float = 0.9,
        background_color: str = "#0b0b0f",
        message_box_color: str = "#111827",
        message_border_color: str = "#4b5563",
        message_border_width: int = 1,
        user_name_color: str = "#f3f4f6",
        message_color: str = "#e5e7eb",
        message_font_size: int = 12,
        message_order: str = "top_down",
    ) -> None:
        if QApplication is not None:
            try:
                self._qt_backend = True
                self._impl = PyQtOverlayWindow(
                    width=width,
                    height=height,
                    opacity=opacity,
                    max_messages=max_messages,
                    x_offset=x_offset,
                    y_offset=y_offset,
                    background_opacity=background_opacity,
                    message_opacity=message_opacity,
                    background_color=background_color,
                    message_box_color=message_box_color,
                    message_border_color=message_border_color,
                    message_border_width=message_border_width,
                    user_name_color=user_name_color,
                    message_color=message_color,
                    message_font_size=message_font_size,
                    message_order=message_order,
                )
                self._qt_backend = True
                self.width = width
                self.height = height
                self.root = self._impl.root
                self.background_opacity = self._impl.background_opacity
                self.message_opacity = self._impl.message_opacity
                self.background_color = self._impl.background_color
                self.message_box_color = self._impl.message_box_color
                self.message_border_color = self._impl.message_border_color
                self.message_border_width = self._impl.message_border_width
                self.user_name_color = self._impl.user_name_color
                self.message_color = self._impl.message_color
                self.message_font_size = self._impl.message_font_size
                self.message_order = self._impl.message_order
                self._headless = False
                self._resize_active = False
                self._drag_active = False
                self._last_pointer = (0, 0)
                self._initial_size = (width, height)
                self._start_pointer = (0, 0)
                self._start_geometry = (x_offset, y_offset, width, height)
                self._drag_start = (0, 0)
                self._drag_origin = (x_offset, y_offset)
                self._resize_border_threshold = 14
                self.apply_theme = self._impl.apply_theme
                self.refresh = self._impl.refresh
                self.add_message = self._impl.add_message
                self.close = self._impl.close
                self.run = self._impl.run
                self.root.update_idletasks = self._impl.update_idletasks
                self.root.winfo_rootx = lambda: self.root.x()
                self.root.winfo_rooty = lambda: self.root.y()
                self.root.winfo_width = lambda: self.root.width()
                self.root.winfo_height = lambda: self.root.height()
                self.root.winfo_x = lambda: self.root.x()
                self.root.winfo_y = lambda: self.root.y()
                self.root.winfo_exists = lambda: True
                return
            except Exception:
                pass

        self.width = width
        self.height = height
        self.opacity = opacity
        self.background_opacity = opacity if background_opacity is None else background_opacity
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
        self.x_offset = x_offset
        self.y_offset = y_offset
        self.horizontal_padding = 18
        self.vertical_padding = 12
        self._resize_active = False
        self._drag_active = False
        self._last_pointer = (0, 0)
        self._initial_size = (width, height)
        self._start_pointer = (0, 0)
        self._start_geometry = (x_offset, y_offset, width, height)
        self._drag_start = (0, 0)
        self._drag_origin = (x_offset, y_offset)
        self._resize_border_threshold = 14

        try:
            self.root = tk.Tk()
            self._headless = False
        except tk.TclError:
            self.root = DummyRoot()
            self._headless = True

        if not self._headless:
            self.root.title("YouTube Overlay")
            self.root.geometry(f"{width}x{height}+{x_offset}+{y_offset}")
            self.root.overrideredirect(True)
            self.root.attributes("-topmost", True)
            self.root.attributes("-alpha", self.background_opacity)
            self.root.configure(bg=self.background_color)
            self.root.protocol("WM_DELETE_WINDOW", self.close)

        self.apply_theme()

        self.renderer = OverlayRenderer(
            width=width,
            height=height,
            opacity=opacity,
            max_messages=max_messages,
            message_order=message_order,
        )

        if self._headless:
            self.container = DummyWidget()
            self.messages_container = DummyWidget()
            self.resize_handle = DummyWidget()
            return

        self.container = tk.Frame(self.root, bg="#0b0b0f", padx=self.horizontal_padding, pady=self.vertical_padding)
        self.container.pack(fill="both", expand=True)
        self.container.pack_propagate(False)

        self.messages_container = tk.Frame(self.container, bg="#0b0b0f")
        self.messages_container.pack(fill="both", expand=True)
        self.messages_container.pack_propagate(False)

        self.resize_handle = None

        self.root.bind("<ButtonPress-1>", self._on_root_press)
        self.root.bind("<B1-Motion>", self._on_root_drag)
        self.root.bind("<ButtonRelease-1>", self._on_root_release)
        self.root.bind("<Motion>", self._on_border_motion)

    @staticmethod
    def _normalize_opacity(value: float | int) -> float:
        """Normaliza a opacidade para 0.0 a 1.0, aceitando valores em percentual ou escala antiga."""
        opacity = float(value or 0.0)
        if opacity > 1.0:
            opacity = opacity / 100.0
        return max(0.0, min(1.0, opacity))

    @staticmethod
    def _hex_to_tk_color(hex_color: str, alpha: float, base_color: str = "#000000") -> str:
        """Mistura uma cor com um fundo base para simular transparência sem afetar o texto."""
        target = (hex_color or "#000000").strip()
        base = (base_color or "#000000").strip()
        if not target.startswith("#"):
            return target
        if not base.startswith("#"):
            base = "#000000"

        def parse_color(value: str) -> tuple[int, int, int]:
            value = value[1:]
            if len(value) == 3:
                value = "".join(ch * 2 for ch in value)
            if len(value) != 6:
                return 0, 0, 0
            return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))

        target_rgb = parse_color(target)
        base_rgb = parse_color(base)
        alpha_value = TransparentOverlayWindow._normalize_opacity(alpha)

        mixed = tuple(
            int(target_channel * alpha_value + base_channel * (1.0 - alpha_value))
            for target_channel, base_channel in zip(target_rgb, base_rgb)
        )
        return "#{:02x}{:02x}{:02x}".format(*mixed)

    def apply_theme(self) -> None:
        """Aplica a cor e a transparência separadamente para o fundo e para as caixas de mensagem."""
        if getattr(self, "_headless", False):
            return

        self.root.attributes("-alpha", 1.0)
        background_tint = self._hex_to_tk_color(self.background_color, self.background_opacity, "#000000")
        self.root.configure(bg=background_tint)
        if hasattr(self, "container"):
            self.container.configure(bg=background_tint)
        if hasattr(self, "messages_container"):
            self.messages_container.configure(bg=background_tint)
        if hasattr(self, "renderer"):
            self.refresh()

    @staticmethod
    def format_message(message: dict[str, Any]) -> str:
        """Gera texto legível para a renderização do chat."""
        author = str(message.get("author", "Usuário"))
        text = str(message.get("text", ""))
        return f"{author}: {text}" if text else author

    def _is_border_resize_hit(self, event) -> bool:
        """Indica se o ponteiro está na borda externa do overlay para iniciar o resize."""
        if event is None or getattr(self, "_headless", False):
            return False

        try:
            rel_x = event.x_root - self.root.winfo_rootx()
            rel_y = event.y_root - self.root.winfo_rooty()
        except AttributeError:
            return False

        width = self.root.winfo_width()
        height = self.root.winfo_height()
        threshold = self._resize_border_threshold

        on_right_edge = rel_x >= width - threshold
        on_bottom_edge = rel_y >= height - threshold
        on_left_edge = rel_x <= threshold
        on_top_edge = rel_y <= threshold

        return on_right_edge or on_bottom_edge or on_left_edge or on_top_edge

    def _on_border_motion(self, event=None) -> None:
        if not getattr(self, "_headless", False) and self._is_border_resize_hit(event):
            self.root.configure(cursor="sizing")
        elif not getattr(self, "_headless", False):
            self.root.configure(cursor="arrow")

    def _on_root_press(self, event=None) -> None:
        if getattr(self, "_headless", False):
            return
        if self._is_border_resize_hit(event):
            self._on_resize_start(event)
            return
        self._on_drag_start(event)

    def _on_root_drag(self, event=None) -> None:
        if getattr(self, "_headless", False):
            return
        if self._resize_active:
            self._on_resize_drag(event)
        elif self._drag_active:
            self._on_drag_move(event)

    def _on_root_release(self, event=None) -> None:
        if getattr(self, "_headless", False):
            return
        self._on_resize_end(event)
        self._on_drag_end(event)

    def _on_drag_start(self, event=None) -> None:
        if getattr(self, "_headless", False) or event is None:
            return
        self._drag_active = True
        self._drag_start = (event.x_root, event.y_root)
        self._drag_origin = (self.root.winfo_x(), self.root.winfo_y())

    def _on_drag_move(self, event=None) -> None:
        if getattr(self, "_headless", False) or event is None or not self._drag_active:
            return
        delta_x = event.x_root - self._drag_start[0]
        delta_y = event.y_root - self._drag_start[1]
        new_x = self._drag_origin[0] + delta_x
        new_y = self._drag_origin[1] + delta_y
        self.root.geometry(f"+{new_x}+{new_y}")

    def _on_drag_end(self, event=None) -> None:
        self._drag_active = False

    def _on_resize_hover(self, event=None) -> None:
        if not getattr(self, "_headless", False):
            self.root.configure(cursor="sizing")

    def _on_resize_leave(self, event=None) -> None:
        if not getattr(self, "_headless", False):
            self.root.configure(cursor="arrow")

    def _on_resize_start(self, event=None) -> None:
        if getattr(self, "_headless", False):
            return
        self._resize_active = True
        self._last_pointer = (event.x_root, event.y_root)
        self._start_pointer = (event.x_root, event.y_root)
        self._initial_size = (self.root.winfo_width(), self.root.winfo_height())
        self._start_geometry = (self.root.winfo_x(), self.root.winfo_y(), self.root.winfo_width(), self.root.winfo_height())

    def _on_resize_drag(self, event=None) -> None:
        if getattr(self, "_headless", False) or not self._resize_active:
            return

        delta_x = event.x_root - self._start_pointer[0]
        delta_y = event.y_root - self._start_pointer[1]

        new_width = max(200, self._initial_size[0] + delta_x)
        new_height = max(150, self._initial_size[1] + delta_y)

        self.width = int(new_width)
        self.height = int(new_height)
        self.root.geometry(f"{self.width}x{self.height}+{self._start_geometry[0]}+{self._start_geometry[1]}")
        self.root.update_idletasks()
        self._last_pointer = (event.x_root, event.y_root)

    def _on_resize_end(self, event=None) -> None:
        self._resize_active = False
        if not getattr(self, "_headless", False):
            self.root.configure(cursor="arrow")

    def _bind_overlay_mouse_events(self, widget) -> None:
        """Permite arrastar/redimensionar mesmo clicando sobre mensagens."""
        if getattr(self, "_headless", False):
            return
        widget.bind("<ButtonPress-1>", self._on_root_press)
        widget.bind("<B1-Motion>", self._on_root_drag)
        widget.bind("<ButtonRelease-1>", self._on_root_release)
        widget.bind("<Motion>", self._on_border_motion)

    def get_inner_width(self) -> int:
        """Retorna a largura útil do conteúdo interno, respeitando a margem lateral do retângulo externo."""
        return max(120, self.root.winfo_width() - (self.horizontal_padding * 2))

    def _sync_dynamic_height(self) -> None:
        if getattr(self, "_headless", False):
            return

        self.root.update_idletasks()
        children = self.messages_container.winfo_children()
        content_height = sum(widget.winfo_reqheight() for widget in children)
        if children:
            content_height += 10 * len(children)
        desired_height = max(80, content_height + self.vertical_padding * 2)
        if desired_height == self.height:
            return

        old_height = self.height
        self.height = int(desired_height)
        new_y = self.root.winfo_y()
        if self.message_order == "top_down":
            new_y = self.root.winfo_y() + old_height - self.height

        self.root.geometry(f"{self.width}x{self.height}+{self.root.winfo_x()}+{new_y}")
        self.container.configure(width=self.width, height=self.height)
        self.messages_container.configure(width=self.get_inner_width())

    def refresh(self) -> None:
        """Atualiza os widgets visuais com as mensagens atuais."""
        for widget in self.messages_container.winfo_children():
            widget.destroy()

        self.root.update_idletasks()
        inner_width = self.get_inner_width()
        self.container.configure(width=self.root.winfo_width(), height=self.root.winfo_height())
        self.messages_container.configure(width=inner_width)

        for message in self.renderer.render():
            raw_text = self.format_message(message)
            author_name, _, message_text = raw_text.partition(": ")
            bubble_background = self._hex_to_tk_color(self.message_box_color, self.message_opacity, self.background_color)
            bubble = tk.Frame(
                self.messages_container,
                bg=bubble_background,
                padx=8,
                pady=6,
                bd=0,
                relief="flat",
                highlightbackground=self.message_border_color,
                highlightcolor=self.message_border_color,
                highlightthickness=max(0, int(self.message_border_width)),
            )
            self._bind_overlay_mouse_events(bubble)
            bubble.pack(fill="x", pady=5)

            if author_name and ": " in raw_text:
                author_label = tk.Label(
                    bubble,
                    text=f"{author_name}:",
                    bg=bubble["bg"],
                    fg=self.user_name_color,
                    justify="left",
                    anchor="w",
                    wraplength=max(80, inner_width - 20),
                    font=("Segoe UI", max(9, int(self.message_font_size)), "bold"),
                    bd=0,
                    highlightthickness=0,
                )
                self._bind_overlay_mouse_events(author_label)
                author_label.pack(anchor="w", fill="x")

                text_label = tk.Label(
                    bubble,
                    text=message_text,
                    bg=bubble["bg"],
                    fg=self.message_color,
                    justify="left",
                    anchor="w",
                    wraplength=max(80, inner_width - 20),
                    font=("Segoe UI", max(9, int(self.message_font_size)), "normal"),
                    bd=0,
                    highlightthickness=0,
                )
                self._bind_overlay_mouse_events(text_label)
                text_label.pack(anchor="w", fill="x")
            else:
                text_label = tk.Label(
                    bubble,
                    text=raw_text,
                    bg=bubble["bg"],
                    fg=self.message_color,
                    justify="left",
                    anchor="w",
                    wraplength=max(80, inner_width - 20),
                    font=("Segoe UI", max(9, int(self.message_font_size)), "bold"),
                    bd=0,
                    highlightthickness=0,
                )
                self._bind_overlay_mouse_events(text_label)
                text_label.pack(anchor="w", fill="x")

        self._sync_dynamic_height()

    def add_message(self, message: dict[str, Any]) -> None:
        """Adiciona uma mensagem ao overlay e atualiza a tela."""
        self.renderer.add_message(message)
        self.refresh()

    def run(self) -> None:
        """Inicia o loop principal da janela."""
        self.root.mainloop()

    def close(self) -> None:
        """Fecha a janela do overlay."""
        self.root.destroy()
