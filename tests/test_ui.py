from app.main import ConfigurationWindow


def make_window(tmp_path):
    return ConfigurationWindow(master=None, config_path=tmp_path / "settings.json")


def test_settings_window_collects_fields(tmp_path):
    window = make_window(tmp_path)
    window.live_id_var.set("live-1")
    window.api_key_var.set("key-1")
    window.server_host_var.set("10.0.0.2")
    window.server_port_var.set("9100")
    window.client_host_var.set("10.0.0.3")
    window.client_port_var.set("9200")
    window.role_var.set("stream")
    window.enable_overlay_var.set(True)

    values = window.collect_values()

    assert values["live_id"] == "live-1"
    assert values["api_key"] == "key-1"
    assert values["server_host"] == "10.0.0.2"
    assert values["server_port"] == 9100
    assert values["client_host"] == "10.0.0.3"
    assert values["client_port"] == 9200
    assert values["role"] == "stream"
    assert values["enable_overlay"] is True


def test_configuration_window_does_not_expose_overlay_size_fields(tmp_path):
    window = make_window(tmp_path)

    assert not hasattr(window, "overlay_width_var")
    assert not hasattr(window, "overlay_height_var")

    values = window.collect_values()
    assert "overlay_width" not in values
    assert "overlay_height" not in values


def test_configuration_window_collects_style_settings(tmp_path):
    window = make_window(tmp_path)
    window.background_opacity_var.set(0.45)
    window.message_opacity_var.set(0.75)
    window.background_color_var.set("#101010")
    window.message_box_color_var.set("#1f2937")
    window.user_name_color_var.set("#facc15")
    window.message_color_var.set("#d1d5db")
    window.message_border_width_var.set(3)
    window.message_border_color_var.set("#94a3b8")
    window.message_font_size_var.set(16)
    window.max_messages_var.set(7)
    window.message_order_var.set("No topo")

    values = window.collect_values()

    assert values["background_opacity"] == 0.45
    assert values["message_opacity"] == 0.75
    assert values["background_color"] == "#101010"
    assert values["message_box_color"] == "#1f2937"
    assert values["user_name_color"] == "#facc15"
    assert values["message_color"] == "#d1d5db"
    assert values["message_border_width"] == 3
    assert values["message_border_color"] == "#94a3b8"
    assert values["message_font_size"] == 16
    assert values["max_messages"] == 7
    assert values["message_order"] == "down_top"


def test_configuration_window_saves_and_loads_settings(tmp_path):
    config_path = tmp_path / "settings.json"
    window = ConfigurationWindow(master=None, config_path=config_path)
    window.live_id_var.set("live-saved")
    window.api_key_var.set("key-saved")
    window.save_api_key_var.set(True)
    window.background_color_var.set("#202020")
    window.message_font_size_var.set(18)
    window.max_messages_var.set(6)
    window.message_order_var.set("No topo")

    window.save_settings()

    loaded_window = ConfigurationWindow(master=None, config_path=config_path)
    assert loaded_window.live_id_var.get() == "live-saved"
    assert loaded_window.api_key_var.get() == "key-saved"
    assert loaded_window.save_api_key_var.get() is True
    assert loaded_window.background_color_var.get() == "#202020"
    assert loaded_window.message_font_size_var.get() == 18
    assert loaded_window.max_messages_var.get() == 6
    assert loaded_window.collect_values()["message_order"] == "down_top"


def test_configuration_window_does_not_save_api_key_by_default(tmp_path):
    config_path = tmp_path / "settings.json"
    window = ConfigurationWindow(master=None, config_path=config_path)
    window.api_key_var.set("secret-key")

    window.save_settings()

    loaded_window = ConfigurationWindow(master=None, config_path=config_path)
    assert loaded_window.config_manager.config.youtube_api_key == ""
    assert loaded_window.config_manager.config.save_api_key is False


def test_configuration_window_updates_status_text(tmp_path):
    window = make_window(tmp_path)

    window._set_status("Chat ativo.")

    assert window.status_var.get() == "Chat ativo."


def test_configuration_window_saves_overlay_position(tmp_path):
    config_path = tmp_path / "settings.json"
    window = ConfigurationWindow(master=None, config_path=config_path)
    window.role_var.set("demo")
    window.enable_overlay_var.set(True)

    window.start_app()
    overlay = window.active_overlay_app.overlay_window
    if hasattr(overlay.root, "move"):
        overlay.root.move(321, 234)
    if hasattr(overlay.root, "resize"):
        overlay.root.resize(640, 360)

    window.save_settings()

    loaded_window = ConfigurationWindow(master=None, config_path=config_path)
    assert loaded_window.config_manager.config.overlay_x == 321
    assert loaded_window.config_manager.config.overlay_y == 234
    assert loaded_window.config_manager.config.overlay_width == 640
    assert loaded_window.config_manager.config.overlay_height == 360


def test_configuration_window_toggles_overlay_window(tmp_path):
    window = make_window(tmp_path)
    window.role_var.set("demo")
    window.enable_overlay_var.set(True)

    window.start_app()
    first_app = window.active_overlay_app
    assert first_app is not None
    assert first_app.overlay_window is not None

    window.start_app()
    assert window.active_overlay_app is None


def test_configuration_window_updates_overlay_opacity_live(tmp_path):
    window = make_window(tmp_path)
    window.role_var.set("demo")
    window.enable_overlay_var.set(True)

    window.start_app()
    assert window.active_overlay_app is not None

    window.overlay_opacity_var.set(0.55)
    window.apply_opacity_from_slider()

    assert window.active_overlay_app.overlay_opacity == 0.55
    assert window.active_overlay_app.overlay_window.opacity == 0.55


def test_configuration_window_updates_message_opacity_live(tmp_path):
    window = make_window(tmp_path)
    window.role_var.set("demo")
    window.enable_overlay_var.set(True)

    window.start_app()
    assert window.active_overlay_app is not None

    window.message_opacity_var.set(0.35)
    window._on_style_changed()

    overlay = window.active_overlay_app.overlay_window
    assert window.active_overlay_app.message_opacity == 0.35
    assert overlay.message_opacity == 0.35
    if hasattr(overlay, "_impl"):
        assert overlay._impl.message_opacity == 0.35


def test_configuration_window_updates_max_messages_live(tmp_path):
    window = make_window(tmp_path)
    window.role_var.set("demo")
    window.enable_overlay_var.set(True)

    window.start_app()
    assert window.active_overlay_app is not None

    window.max_messages_var.set(4)
    window._on_style_changed()

    overlay = window.active_overlay_app.overlay_window
    assert window.active_overlay_app.max_messages == 4
    assert overlay.max_messages == 4
    if hasattr(overlay, "_impl"):
        assert overlay._impl.renderer.max_messages == 4


def test_configuration_window_updates_message_order_live(tmp_path):
    window = make_window(tmp_path)
    window.role_var.set("demo")
    window.enable_overlay_var.set(True)

    window.start_app()
    assert window.active_overlay_app is not None

    window.message_order_var.set("No topo")
    window._on_style_changed()

    overlay = window.active_overlay_app.overlay_window
    assert window.active_overlay_app.message_order == "down_top"
    if hasattr(overlay, "_impl"):
        assert overlay._impl.renderer.message_order == "down_top"


def test_configuration_window_closes_overlay_when_config_window_closes(tmp_path):
    window = make_window(tmp_path)
    window.role_var.set("demo")
    window.enable_overlay_var.set(True)

    window.start_app()
    assert window.active_overlay_app is not None

    window.close_window()
    assert window.active_overlay_app is None
