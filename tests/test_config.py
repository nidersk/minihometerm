import pytest

from minihometerm import config


@pytest.fixture
def clean_env(monkeypatch):
    """Ensure no env vars interfere with tests."""
    monkeypatch.delenv("MINIHOMETERM_WS_URL", raising=False)
    monkeypatch.delenv("MINIHOMETERM_TOKEN", raising=False)


def test_config_defaults(monkeypatch, tmp_path, caplog):

    monkeypatch.setattr(config, "USER_CONFIG_PATH", tmp_path / "doesnotexist.ini")
    monkeypatch.setattr(config, "GLOBAL_CONFIG_PATH", tmp_path / "alsodoesnotexist.ini")

    with caplog.at_level("INFO"):
        cfg = config.load_config()

    assert not any("User config found" in m for m in caplog.messages)
    assert not any("Global config found" in m for m in caplog.messages)

    assert cfg.get("connection", "ws_url") == "ws://homeassistant.local:8123/api/websocket"
    assert cfg.get("connection", "token") == "<YOUR_LONG_LIVED_TOKEN>"


def test_malformed_configs(clean_env, caplog, tmp_path, monkeypatch):
    """If config.ini is broken, defaults should still apply."""
    cfg_path = tmp_path / "config.ini"
    cfg_path.write_text("MALFORMED FILE WITHOUT SECTIONS\n")

    monkeypatch.setattr(config, "GLOBAL_CONFIG_PATH", cfg_path)
    monkeypatch.setattr(config, "USER_CONFIG_PATH", cfg_path)

    with caplog.at_level("WARNING"):
        cfg = config.load_config()

    assert any("Ignoring malformed global config" in message for message in caplog.messages)
    assert any("Ignoring malformed user config" in message for message in caplog.messages)

    # Even though file is broken/missing sections, defaults are restored
    assert cfg.get("connection", "ws_url") == "ws://homeassistant.local:8123/api/websocket"
    assert cfg.get("connection", "token") == "<YOUR_LONG_LIVED_TOKEN>"


def test_override_with_file(clean_env, tmp_path, monkeypatch):
    cfg_path = tmp_path / "config.ini"
    cfg_path.write_text(
        "[connection]\n"
        "ws_url = ws://192.168.1.100:8123/api/websocket\n"
        "token = filetoken\n"
        "entities = light.kitchen,light.living_room\n"
        "\n[ui]\n"
        "theme = dark\n"
        "fullscreen = 1\n"
    )

    monkeypatch.setattr(config, "USER_CONFIG_PATH", cfg_path)

    cfg = config.load_config()
    assert cfg.get("connection", "ws_url") == "ws://192.168.1.100:8123/api/websocket"
    assert cfg.get("connection", "token") == "filetoken"
    assert cfg.get("connection", "entities") == "light.kitchen,light.living_room"
    assert cfg.get("ui", "theme") == "dark"
    assert cfg.get("ui", "fullscreen") == "1"


def test_override_with_env(clean_env, monkeypatch):
    monkeypatch.setenv("MINIHOMETERM_WS_URL", "ws://env-override:8123/api/websocket")
    monkeypatch.setenv("MINIHOMETERM_TOKEN", "envtoken")

    cfg = config.load_config()
    assert cfg.get("connection", "ws_url") == "ws://env-override:8123/api/websocket"
    assert cfg.get("connection", "token") == "envtoken"


def test_file_then_env_priority(clean_env, tmp_path, monkeypatch):
    cfg_path = tmp_path / "config.ini"
    cfg_path.write_text(
        "[connection]\n" "ws_url = ws://file-only:8123/api/websocket\n" "token = filetoken\n"
    )
    monkeypatch.setattr(config, "USER_CONFIG_PATH", cfg_path)

    # env overrides file
    monkeypatch.setenv("MINIHOMETERM_WS_URL", "ws://env-override:8123/api/websocket")
    monkeypatch.setenv("MINIHOMETERM_TOKEN", "envtoken")

    cfg = config.load_config()
    assert cfg.get("connection", "ws_url") == "ws://env-override:8123/api/websocket"
    assert cfg.get("connection", "token") == "envtoken"


def test_missing_sections_fallback(clean_env, caplog, tmp_path, monkeypatch):
    """If config.ini is missing sections or broken, defaults should still apply."""
    cfg_path = tmp_path / "config.ini"
    cfg_path.write_text(
        "[connection]\n"
        "ws_url = ws://192.168.1.100:8123/api/websocket\n"
        "token = \n"
        "entities = light.kitchen,light.living_room\n"
        "\n[ui]\n"
        "fullscreen = 1\n"
    )

    monkeypatch.setattr(config, "GLOBAL_CONFIG_PATH", tmp_path / "also_nonexistent.ini")
    monkeypatch.setattr(config, "USER_CONFIG_PATH", cfg_path)

    with caplog.at_level("WARNING"):
        cfg = config.load_config()

    assert not any("Ignoring malformed" in message for message in caplog.messages)

    # Even though file is broken/missing sections, defaults are restored
    assert cfg.get("connection", "ws_url") == "ws://192.168.1.100:8123/api/websocket"
    assert cfg.get("connection", "token") == ""
    assert "light.kitchen,light.living_room" in cfg.get("connection", "entities")

    # Also UI section is still available
    assert cfg.get("ui", "theme") == "dark"
    assert cfg.get("ui", "fullscreen") == "1"
