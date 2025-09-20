import os

import pytest
from doubles import DummyWS
from kivy.logger import Logger as logger

from minihometerm.hass_client import HAWebSocketClient


@pytest.fixture(autouse=True, scope="session")
def headless_kivy():
    # Ensure tests don't try to open a real window.
    os.environ.setdefault("KIVY_WINDOW", "mock")
    os.environ.setdefault("KIVY_GL_BACKEND", "mock")
    os.environ.setdefault("KIVY_NO_ARGS", "1")
    yield


@pytest.fixture
def mock_cfg(monkeypatch, tmp_path):
    from minihometerm import config

    monkeypatch.setattr(config, "USER_CONFIG_PATH", tmp_path / "doesnotexist.ini")
    monkeypatch.setattr(config, "GLOBAL_CONFIG_PATH", tmp_path / "alsodoesnotexist.ini")

    cfg = config.load_config()

    return cfg


@pytest.fixture
def client(monkeypatch):
    # Patch the symbol as used by the module under test (critical!)
    monkeypatch.setattr(
        "minihometerm.hass_client.websocket.WebSocketApp",
        DummyWS,
        raising=True,
    )

    updates = []

    # Optionally wrap on_entity_update to capture events
    def on_update(eid, new_state, old_state):
        updates.append((eid, new_state, old_state))

    c = HAWebSocketClient(
        url="ws://localhost:8123/api/websocket",
        token="token123",
        entities=["input_boolean.test_toggle_1"],
        on_entity_update=on_update,
    )

    # We don’t know the DummyWS instance until _connect constructs it,
    # so we expose a getter that finds it after start().
    def ws_getter():
        return c._ws  # the DummyWS instance after start()

    def stop(self):
        self._running = False
        if self._ws:
            try:
                self._ws.close()
            except Exception as e:
                logger.warning("HAWebSocket: Error while closing WebSocket: %s", e)
        if self._thread:
            self._thread.join(timeout=5)
            # (Optional) set to None to avoid accidental reuse
            self._thread = None
            self._ws = None

    # Yield (so teardown always runs)
    try:
        yield c, ws_getter, updates
    finally:
        c.stop()  # ensure thread stops even if test fails
