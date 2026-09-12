"""Janela transparente para renderizar o overlay do chat em streaming."""

from __future__ import annotations

import html
import os
from typing import Any

from modules.overlay import OverlayRenderer

# Evita forÃ§ar o PyQt em modo offscreen em janelas normais do desktop.
# O modo headless sÃ³ deve ser ativado explicitamente em testes/CI.
if os.environ.get("PYTHONOVERLAY_HEADLESS") == "1":
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QLabel, QSizePolicy, QVBoxLayout, QWidget


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

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not hasattr(self.overlay, "container"):
            return
        self.overlay.width = int(self.width())
        self.overlay.height = int(self.height())
        self.overlay.container.setGeometry(0, 0, self.width(), self.height())
        self.overlay.messages_container.setGeometry(
            self.overlay.horizontal_padding,
            self.overlay.vertical_padding,
            max(120, self.width() - self.overlay.horizontal_padding * 2),
            max(40, self.height() - self.overlay.vertical_padding * 2),
        )


class PyQtOverlayWindow:
    """Backend do overlay em PyQt para permitir transparÃªncia real por widget."""

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
        author = str(message.get("author", "UsuÃ¡rio"))
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
            author = str(message.get("author", "UsuÃ¡rio"))
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
    """Janela leve e transparente para exibição do chat em streaming, usando PyQt."""

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
        self.width = width
        self.height = height
        self.root = self._impl.root
        self.container = self._impl.container
        self.messages_container = self._impl.messages_container
        self.background_opacity = self._impl.background_opacity
        self.message_opacity = self._impl.message_opacity
        self.background_color = self._impl.background_color
        self.message_box_color = self._impl.message_box_color
        self.message_border_color = self._impl.message_border_color
        self.message_border_width = self._impl.message_border_width
        self.user_name_color = self._impl.user_name_color
        self.message_color = self._impl.message_color
        self.message_font_size = self._impl.message_font_size
        self.max_messages = self._impl.max_messages
        self.message_order = self._impl.message_order
        self.renderer = self._impl.renderer
        self._resize_border_threshold = 18

    def apply_theme(self) -> None:
        self._sync_to_impl()
        self._impl.apply_theme()
        self._sync_from_impl()

    def refresh(self) -> None:
        self._sync_to_impl()
        self._impl.refresh()
        self._sync_from_impl()

    def add_message(self, message: dict[str, Any]) -> None:
        self._sync_to_impl()
        self._impl.add_message(message)
        self._sync_from_impl()

    def run(self) -> None:
        self._impl.run()

    def close(self) -> None:
        self._impl.close()

    @staticmethod
    def format_message(message: dict[str, Any]) -> str:
        return PyQtOverlayWindow.format_message(message)

    def _is_border_resize_hit(self, event) -> bool:
        if event is None:
            return False
        rel_x = event.x_root - self.root.winfo_rootx()
        rel_y = event.y_root - self.root.winfo_rooty()
        threshold = self._resize_border_threshold
        return (
            rel_x >= self.root.winfo_width() - threshold
            or rel_y >= self.root.winfo_height() - threshold
            or rel_x <= threshold
            or rel_y <= threshold
        )

    def _sync_to_impl(self) -> None:
        self._impl.opacity = getattr(self, "opacity", self._impl.opacity)
        self._impl.background_opacity = self.background_opacity
        self._impl.message_opacity = self.message_opacity
        self._impl.background_color = self.background_color
        self._impl.message_box_color = self.message_box_color
        self._impl.message_border_color = self.message_border_color
        self._impl.message_border_width = self.message_border_width
        self._impl.user_name_color = self.user_name_color
        self._impl.message_color = self.message_color
        self._impl.message_font_size = self.message_font_size
        self._impl.max_messages = self.max_messages
        self._impl.message_order = self.message_order
        self._impl.renderer.max_messages = self.max_messages
        self._impl.renderer.message_order = self.message_order

    def _sync_from_impl(self) -> None:
        self.width = self._impl.width
        self.height = self._impl.height
        self.container = self._impl.container
        self.messages_container = self._impl.messages_container
        self.background_opacity = self._impl.background_opacity
        self.message_opacity = self._impl.message_opacity
        self.background_color = self._impl.background_color
        self.message_box_color = self._impl.message_box_color
        self.message_border_color = self._impl.message_border_color
        self.message_border_width = self._impl.message_border_width
        self.user_name_color = self._impl.user_name_color
        self.message_color = self._impl.message_color
        self.message_font_size = self._impl.message_font_size
        self.max_messages = self._impl.max_messages
        self.message_order = self._impl.message_order
        self.renderer = self._impl.renderer
