from app.runtime import YouTubeOverlayApp


def test_app_builds_runtime_from_config():
    app = YouTubeOverlayApp(
        live_id="live-demo",
        api_key="api-demo",
        host="127.0.0.1",
        port=9001,
        mode="demo",
    )

    config = app.build_runtime_config()

    assert config["live_id"] == "live-demo"
    assert config["api_key"] == "api-demo"
    assert config["host"] == "127.0.0.1"
    assert config["port"] == 9001
    assert config["mode"] == "demo"
