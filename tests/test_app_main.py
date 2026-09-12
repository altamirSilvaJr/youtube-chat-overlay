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


def test_runtime_can_collect_show_locally_and_send_to_network():
    app = YouTubeOverlayApp(mode="same_pc_and_client", overlay_enabled=False)
    sent_messages = []
    delivered_callbacks = []

    app.collector.connect = lambda: True
    app.client.connect = lambda: True
    app.client.send_message = sent_messages.append

    def start_polling(on_message, _on_error):
        delivered_callbacks.append(on_message)

    app.collector.start_polling = start_polling

    app.run()
    message = {"message_id": "msg-1", "author": "usuario1", "text": "Olá"}
    delivered_callbacks[0](message)

    assert app._runtime_started is True
    assert sent_messages == [message]
    assert app.process_pending_messages() == 1
    assert app.renderer.messages[0]["message_id"] == "msg-1"
