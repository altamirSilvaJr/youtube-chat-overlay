from modules.youtube_chat import YouTubeChatCollector


def test_connect_requires_credentials():
    empty_collector = YouTubeChatCollector("", "")
    assert empty_collector.connect() is False

    configured_collector = YouTubeChatCollector("live-id", "api-key")
    assert configured_collector.connect() is True


def test_normalize_message_extracts_expected_fields():
    raw_message = {
        "id": "msg-123",
        "snippet": {
            "authorChannelId": {"value": "channel-1"},
            "displayMessage": "Olá galera!",
            "publishedAt": "2026-09-12T12:00:00Z",
            "type": "textMessageEvent",
        },
        "authorDetails": {"displayName": "usuario1"},
    }

    normalized = YouTubeChatCollector.normalize_message(raw_message)

    assert normalized["message_id"] == "msg-123"
    assert normalized["author"] == "usuario1"
    assert normalized["text"] == "Olá galera!"
    assert normalized["event_type"] == "chat_message"
    assert normalized["timestamp"] == "2026-09-12T12:00:00Z"


def test_extract_video_id_from_youtube_urls():
    assert YouTubeChatCollector.extract_video_id("abc123") == "abc123"
    assert YouTubeChatCollector.extract_video_id("https://www.youtube.com/watch?v=abc123") == "abc123"
    assert YouTubeChatCollector.extract_video_id("https://youtu.be/abc123") == "abc123"
    assert YouTubeChatCollector.extract_video_id("https://www.youtube.com/live/abc123?feature=share") == "abc123"


def test_load_api_key_from_env_file(tmp_path, monkeypatch):
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
    env_path = tmp_path / ".env"
    env_path.write_text("YOUTUBE_API_KEY=test-key\n", encoding="utf-8")

    assert YouTubeChatCollector.load_api_key_from_env(str(env_path)) == "test-key"


def test_fetch_live_chat_id_uses_video_endpoint(monkeypatch):
    collector = YouTubeChatCollector("https://www.youtube.com/watch?v=video-1", "api-key")

    def fake_get_json(url):
        assert "videos" in url
        assert "video-1" in url
        return {"items": [{"liveStreamingDetails": {"activeLiveChatId": "chat-1"}}]}

    monkeypatch.setattr(collector, "_get_json", fake_get_json)

    assert collector.fetch_live_chat_id() == "chat-1"
