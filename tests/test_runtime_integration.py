from app.main import YouTubeOverlayApp


def test_runtime_creates_overlay_window_for_client_mode():
    app = YouTubeOverlayApp(
        live_id="live-demo",
        api_key="key-demo",
        host="127.0.0.1",
        port=9005,
        mode="client",
    )

    overlay = app.create_overlay_window()

    assert overlay is not None
    assert overlay.width == 500
    assert overlay.height == 300
    assert app.overlay_window is overlay
