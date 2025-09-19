import pytest

from minihometerm import config


@pytest.fixture
def clean_env(monkeypatch):
    """Ensure no env vars interfere with tests."""
    monkeypatch.delenv("MINIHOMETERM_WS_URL", raising=False)
    monkeypatch.delenv("MINIHOMETERM_TOKEN", raising=False)


def test_config_defaults(monkeypatch, tmp_path, caplog):
    """If global/user config.ini is missing, defaults should still apply."""
    monkeypatch.setattr(config, "USER_CONFIG_PATH", tmp_path / "doesnotexist.ini")
    monkeypatch.setattr(config, "GLOBAL_CONFIG_PATH", tmp_path / "alsodoesnotexist.ini")

    with caplog.at_level("INFO"):
        cfg = config.load_config()

    assert not any("Global config found" in m for m in caplog.messages)
    assert not any("User config found" in m for m in caplog.messages)

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

    assert cfg.get("connection", "ws_url") == "ws://homeassistant.local:8123/api/websocket"
    assert cfg.get("connection", "token") == "<YOUR_LONG_LIVED_TOKEN>"


def test_global_config(clean_env, caplog, tmp_path, monkeypatch):
    """If global config.ini is available, load values from it."""
    cfg_path = tmp_path / "config.ini"
    cfg_path.write_text(
        "[connection]\n" "ws_url = ws://global:8123/api/websocket\n" "token = global_token\n"
    )

    monkeypatch.setattr(config, "GLOBAL_CONFIG_PATH", cfg_path)
    monkeypatch.setattr(config, "USER_CONFIG_PATH", tmp_path / "doesnotexist.ini")

    with caplog.at_level("INFO"):
        cfg = config.load_config()

    assert any("Global config found" in m for m in caplog.messages)
    assert not any("User config found" in m for m in caplog.messages)

    assert cfg.get("connection", "ws_url") == "ws://global:8123/api/websocket"
    assert cfg.get("connection", "token") == "global_token"


def test_user_config(clean_env, caplog, tmp_path, monkeypatch):
    """If user config.ini is available, load values from it."""
    cfg_path = tmp_path / "config.ini"
    cfg_path.write_text(
        "[connection]\n" "ws_url = ws://global:8123/api/websocket\n" "token = global_token\n"
    )

    monkeypatch.setattr(config, "GLOBAL_CONFIG_PATH", tmp_path / "doesnotexist.ini")
    monkeypatch.setattr(config, "USER_CONFIG_PATH", cfg_path)

    with caplog.at_level("INFO"):
        cfg = config.load_config()

    assert not any("Global config found" in m for m in caplog.messages)
    assert any("User config found" in m for m in caplog.messages)

    assert cfg.get("connection", "ws_url") == "ws://global:8123/api/websocket"
    assert cfg.get("connection", "token") == "global_token"


def test_override_global_with_user_config(clean_env, caplog, tmp_path, monkeypatch):
    """If global and user config.ini is available, load values from user config."""
    cfg_path_global = tmp_path / "config_global.ini"
    cfg_path_global.write_text(
        "[connection]\n" "ws_url = ws://global:8123/api/websocket\n" "token = global_token\n"
    )

    cfg_path_user = tmp_path / "config_user.ini"
    cfg_path_user.write_text(
        "[connection]\n" "ws_url = ws://user:8123/api/websocket\n" "token = user_token\n"
    )

    monkeypatch.setattr(config, "GLOBAL_CONFIG_PATH", cfg_path_global)
    monkeypatch.setattr(config, "USER_CONFIG_PATH", cfg_path_user)

    with caplog.at_level("INFO"):
        cfg = config.load_config()

    assert any("Global config found" in m for m in caplog.messages)
    assert any("User config found" in m for m in caplog.messages)

    assert cfg.get("connection", "ws_url") == "ws://user:8123/api/websocket"
    assert cfg.get("connection", "token") == "user_token"


def test_override_with_env_variables(clean_env, caplog, tmp_path, monkeypatch):
    """If global and user config.ini is available, load values from user config."""
    cfg_path_global = tmp_path / "config_global.ini"
    cfg_path_global.write_text(
        "[connection]\n" "ws_url = ws://global:8123/api/websocket\n" "token = global_token\n"
    )

    cfg_path_user = tmp_path / "config_user.ini"
    cfg_path_user.write_text(
        "[connection]\n" "ws_url = ws://user:8123/api/websocket\n" "token = user_token\n"
    )

    monkeypatch.setattr(config, "GLOBAL_CONFIG_PATH", cfg_path_global)
    monkeypatch.setattr(config, "USER_CONFIG_PATH", cfg_path_user)

    monkeypatch.setenv("MINIHOMETERM_WS_URL", "ws://env:8123/api/websocket")
    monkeypatch.setenv("MINIHOMETERM_TOKEN", "env_token")

    with caplog.at_level("INFO"):
        cfg = config.load_config()

    assert any("Global config found" in m for m in caplog.messages)
    assert any("User config found" in m for m in caplog.messages)

    assert cfg.get("connection", "ws_url") == "ws://env:8123/api/websocket"
    assert cfg.get("connection", "token") == "env_token"
