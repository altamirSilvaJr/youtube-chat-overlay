from modules.overlay import OverlayRenderer


def test_renderer_keeps_latest_messages_only():
    renderer = OverlayRenderer(max_messages=2)

    renderer.add_message({"author": "usuario1", "text": "primeira"})
    renderer.add_message({"author": "usuario2", "text": "segunda"})
    renderer.add_message({"author": "usuario3", "text": "terceira"})

    rendered = renderer.render()

    assert len(rendered) == 2
    assert rendered[0]["author"] == "usuario2"
    assert rendered[1]["author"] == "usuario3"
    assert rendered[1]["text"] == "terceira"


def test_renderer_ignores_duplicate_message_ids():
    renderer = OverlayRenderer(max_messages=5)

    message = {
        "message_id": "msg-123",
        "author": "usuario1",
        "text": "Olá galera!",
        "timestamp": "2026-09-12T12:00:00Z",
    }

    renderer.add_message(message)
    renderer.add_message(dict(message))
    renderer.add_message({
        "message_id": "msg-456",
        "author": "usuario2",
        "text": "Nova mensagem",
        "timestamp": "2026-09-12T12:00:01Z",
    })

    rendered = renderer.render()

    assert len(rendered) == 2
    assert [item["message_id"] for item in rendered] == ["msg-123", "msg-456"]


def test_renderer_restores_recent_messages_when_limit_increases():
    renderer = OverlayRenderer(max_messages=4)

    for index in range(1, 5):
        renderer.add_message({"author": f"usuario{index}", "text": f"mensagem {index}"})

    renderer.max_messages = 2
    assert [item["author"] for item in renderer.render()] == ["usuario3", "usuario4"]

    renderer.max_messages = 4
    assert [item["author"] for item in renderer.render()] == [
        "usuario1",
        "usuario2",
        "usuario3",
        "usuario4",
    ]


def test_renderer_can_render_newest_messages_first():
    renderer = OverlayRenderer(max_messages=3, message_order="down_top")

    for index in range(1, 4):
        renderer.add_message({"author": f"usuario{index}", "text": f"mensagem {index}"})

    assert [item["author"] for item in renderer.render()] == [
        "usuario3",
        "usuario2",
        "usuario1",
    ]
