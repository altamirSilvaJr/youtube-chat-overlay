from types import SimpleNamespace

from modules.overlay_window import TransparentOverlayWindow


def test_overlay_window_formats_messages():
    message = {"author": "usuario1", "text": "Olá galera"}

    formatted = TransparentOverlayWindow.format_message(message)

    assert formatted == "usuario1: Olá galera"


def test_overlay_window_detects_border_resize_hit():
    window = TransparentOverlayWindow(width=400, height=200, opacity=0.8)
    event = SimpleNamespace(x_root=window.root.winfo_rootx() + window.root.winfo_width() - 5, y_root=window.root.winfo_rooty() + window.root.winfo_height() - 5)

    assert window._is_border_resize_hit(event) is True


def test_overlay_window_renders_all_messages_in_queue():
    window = TransparentOverlayWindow(width=400, height=200, opacity=0.8)
    messages = [
        {"author": "usuario1", "text": "Olá galera!"},
        {"author": "usuario2", "text": "Partida começando!"},
        {"author": "streamer", "text": "Acompanhem os próximos momentos!"},
    ]

    for message in messages:
        window.add_message(message)

    assert len(window._impl.renderer.messages) == 3
    assert window._impl.messages_container.layout().count() == 3


def test_overlay_window_resize_keeps_content_inside_window():
    window = TransparentOverlayWindow(width=400, height=200, opacity=0.8)

    if hasattr(window, "root") and hasattr(window.root, "resize"):
        window.root.resize(700, 350)

    assert window.root.width() == 700
    assert window.root.height() == 350
    if hasattr(window, "container"):
        assert window.container.width() == 700
        assert window.container.height() == 350


def test_overlay_window_has_no_close_button():
    window = TransparentOverlayWindow(width=400, height=200, opacity=0.8)

    assert not hasattr(window, "close_button")
    window.close()
