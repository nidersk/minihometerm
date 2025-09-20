import json
import threading
import time

import pytest

from minihometerm.hass_client import HAWebSocketClient


class DummyWS:
    """Fake WebSocketApp replacement for tests."""

    def __init__(self, url, on_open, on_message, on_error, on_close):
        self.url = url
        self.on_open = on_open
        self.on_message = on_message
        self.on_error = on_error
        self.on_close = on_close
        self.sent = []
        self.closed = False

    def send(self, msg):
        print("DummyWS.send called with:", msg)
        self.sent.append(json.loads(msg))

    def close(self):
        self.closed = True

    def run_forever(self, ping_interval=None):
        # simulate HA auth handshake
        self.on_message(self, json.dumps({"type": "auth_required"}))
        self.on_open(self)
        self.on_message(self, json.dumps({"type": "auth_ok"}))
        # simulate subscription result
        self.on_message(self, json.dumps({"id": 1, "type": "result", "success": True}))

        # block until closed
        while not self.closed:
            time.sleep(0.01)


@pytest.fixture
def client(monkeypatch):
    dummy_ws = None

    def fake_wsapp(url, on_open, on_message, on_error, on_close):
        nonlocal dummy_ws
        dummy_ws = DummyWS(url, on_open, on_message, on_error, on_close)
        return dummy_ws

    monkeypatch.setattr("minihometerm.hass_client.websocket.WebSocketApp", fake_wsapp)

    updates = []
    c = HAWebSocketClient(
        url="ws://fake",
        token="token123",
        entities={"light.kitchen"},
        on_entity_update=lambda eid, new, old: updates.append((eid, new, old)),
    )
    return c, lambda: dummy_ws, updates


def test_auth_and_subscription(client):
    c, ws_getter, _ = client
    c.start()
    time.sleep(0.1)  # let thread run
    ws = ws_getter()

    # first send() is auth, second is subscribe_events
    assert ws.sent[0]["type"] == "auth"
    assert ws.sent[0]["access_token"] == "token123"
    assert ws.sent[1]["type"] == "subscribe_events"
    assert ws.sent[1]["event_type"] == "state_changed"

    c.stop()


def test_entity_update_callback(client):
    c, ws_getter, updates = client
    c.start()
    time.sleep(0.1)
    ws = ws_getter()

    # send a state_changed event for subscribed entity
    event = {
        "id": 2,
        "type": "event",
        "event": {
            "event_type": "state_changed",
            "data": {
                "entity_id": "light.kitchen",
                "new_state": {"state": "on"},
                "old_state": {"state": "off"},
            },
        },
    }
    ws.on_message(ws, json.dumps(event))
    time.sleep(0.05)

    assert updates == [("light.kitchen", {"state": "on"}, {"state": "off"})]

    c.stop()


def test_entity_update_ignored(client):
    c, ws_getter, updates = client
    c.start()
    time.sleep(0.1)
    ws = ws_getter()

    # send a state_changed for an entity not in the filter
    event = {
        "id": 3,
        "type": "event",
        "event": {
            "event_type": "state_changed",
            "data": {
                "entity_id": "switch.other",
                "new_state": {"state": "on"},
                "old_state": {"state": "off"},
            },
        },
    }
    ws.on_message(ws, json.dumps(event))
    time.sleep(0.05)

    assert updates == []  # ignored

    c.stop()


def test_service_call_success(client):
    c, ws_getter, _ = client
    c.start()
    time.sleep(0.1)
    ws = ws_getter()

    def respond():
        time.sleep(0.05)
        # The last sent message is the call_service request
        sent = ws.sent[-1]
        mid = sent["id"]
        ws.on_message(
            ws,
            json.dumps({"id": mid, "type": "result", "success": True, "result": {"ok": 1}}),
        )

    threading.Thread(target=respond, daemon=True).start()

    res = c.call_service("light", "toggle", target={"entity_id": "light.kitchen"}, timeout=1.0)
    assert res == {"ok": 1}

    c.stop()


def test_service_call_timeout(client):
    c, _, _ = client
    c.start()
    time.sleep(0.1)

    with pytest.raises(TimeoutError):
        c.call_service("light", "toggle", target={"entity_id": "light.kitchen"}, timeout=0.2)

    c.stop()


def test_service_call_failure(client):
    """Simulate HA responding with success=False."""
    c, ws_getter, _ = client
    c.start()
    time.sleep(0.05)
    ws = ws_getter()

    def respond():
        time.sleep(0.05)
        mid = ws.sent[-1]["id"]
        ws.on_message(
            ws,
            json.dumps(
                {
                    "id": mid,
                    "type": "result",
                    "success": False,
                    "error": {"code": "bad_request", "message": "oops"},
                }
            ),
        )

    threading.Thread(target=respond, daemon=True).start()

    with pytest.raises(RuntimeError):
        c.call_service("light", "toggle", target={"entity_id": "light.kitchen"}, timeout=1.0)

    c.stop()


def test_set_entities_changes_filter(client):
    """Verify set_entities updates what events are delivered."""
    c, ws_getter, updates = client
    c.start()
    time.sleep(0.05)
    ws = ws_getter()

    # Initially only kitchen is subscribed
    event = {
        "id": 10,
        "type": "event",
        "event": {
            "event_type": "state_changed",
            "data": {
                "entity_id": "switch.other",
                "new_state": {"state": "on"},
                "old_state": {"state": "off"},
            },
        },
    }
    ws.on_message(ws, json.dumps(event))
    time.sleep(0.05)
    assert updates == []

    # Update filter to include switch.other
    c.set_entities(["switch.other"])
    ws.on_message(ws, json.dumps(event))
    time.sleep(0.05)
    assert updates[-1][0] == "switch.other"

    c.stop()


def test_ignored_message_types(client):
    """Ensure non-event messages are handled without crashing."""
    c, ws_getter, _ = client
    c.start()
    time.sleep(0.05)
    ws = ws_getter()

    # send pong
    ws.on_message(ws, json.dumps({"type": "pong"}))
    # send result with no pending id
    ws.on_message(ws, json.dumps({"id": 999, "type": "result", "success": True}))
    # send nonsense
    ws.on_message(ws, json.dumps({"type": "weird"}))

    # nothing to assert, just not raising
    c.stop()


def test_on_disconnect_called(monkeypatch):
    """Force an exception in _connect to trigger on_disconnect."""
    called = {}

    def fake_wsapp(*a, **k):
        raise RuntimeError("boom")

    monkeypatch.setattr("minihometerm.hass_client.websocket.WebSocketApp", fake_wsapp)

    def on_disc(e):
        called["err"] = str(e)

    c = HAWebSocketClient("ws://fake", "tok", on_disconnect=on_disc)
    t = threading.Thread(target=lambda: c.start(), daemon=True)
    t.start()
    time.sleep(0.2)
    c.stop()
    assert "boom" in called["err"]


def test_stop_closes_ws(client):
    """Ensure stop sets closed flag on dummy ws."""
    c, ws_getter, _ = client
    c.start()
    time.sleep(0.05)
    ws = ws_getter()
    assert not ws.closed
    c.stop()
    assert ws.closed


def test_on_connect_called(client):
    called = {}

    def _on_connect():
        called["ok"] = True

    c, ws_getter, _ = client
    c.on_connect = _on_connect
    c.start()
    time.sleep(0.1)
    assert "ok" in called
    c.stop()


def test_reconnect_after_failure(monkeypatch):
    """Simulate first connection fails, second works."""
    attempts = {"count": 0}
    last_ws = {}

    class FailingWS:
        def __init__(self, *a, **k):
            attempts["count"] += 1
            if attempts["count"] == 1:
                # first attempt fails
                raise RuntimeError("boom")
            last_ws["ws"] = self
            self.sent = []
            self.closed = False
            self.on_open = k["on_open"]
            self.on_message = k["on_message"]

        def send(self, msg):
            self.sent.append(json.loads(msg))

        def close(self):
            self.closed = True

        def run_forever(self, **kw):
            self.on_message(self, json.dumps({"type": "auth_required"}))
            self.on_open(self)
            self.on_message(self, json.dumps({"type": "auth_ok"}))

            while not self.closed:
                time.sleep(0.01)

    monkeypatch.setattr("minihometerm.hass_client.websocket.WebSocketApp", FailingWS)

    c = HAWebSocketClient("ws://fake", "tok")
    t = threading.Thread(target=c.start, daemon=True)
    t.start()
    time.sleep(2.0)
    c.stop()
    t.join()
    assert attempts["count"] >= 2
    assert last_ws["ws"].sent[0]["type"] == "auth"


def test_pending_future_rejected_on_disconnect(client):
    """If disconnect happens before result arrives, pending call fails fast."""
    c, ws_getter, _ = client
    c.start()
    time.sleep(0.05)

    def call_in_thread():
        with pytest.raises(ConnectionError):
            c.call_service("light", "toggle", timeout=1.0)

    th = threading.Thread(target=call_in_thread)
    th.start()

    time.sleep(0.1)
    ws = ws_getter()
    ws.close()  # trigger disconnect -> run_forever returns -> cleanup rejects pending
    th.join()
    c.stop()


def test_send_error(monkeypatch):
    """Force .send to raise exception and check it doesn't crash."""

    class BrokenWS:
        def __init__(self, *a, **k):
            self.on_open = k["on_open"]
            self.on_message = k["on_message"]

        def send(self, msg):
            raise RuntimeError("send fail")

        def run_forever(self, **kw):
            self.on_message(self, json.dumps({"type": "auth_required"}))
            self.on_open(self)
            self.on_message(self, json.dumps({"type": "auth_ok"}))
            time.sleep(0.05)

        def close(self):
            pass

    monkeypatch.setattr("minihometerm.hass_client.websocket.WebSocketApp", BrokenWS)
    c = HAWebSocketClient("ws://fake", "tok")
    # Just start and stop quickly — on_open will trigger send and fail
    c.start()
    time.sleep(0.1)
    c.stop()


def test_auth_required_message(client):
    c, ws_getter, _ = client
    c.start()
    time.sleep(0.05)
    ws = ws_getter()
    # Just send auth_required to hit that branch
    ws.on_message(ws, json.dumps({"type": "auth_required"}))
    c.stop()


def test_auth_ok_triggers_on_connect(client):
    called = {}
    c, ws_getter, _ = client
    c.on_connect = lambda: called.setdefault("ok", True)
    c.start()
    time.sleep(0.05)
    ws = ws_getter()
    ws.on_message(ws, json.dumps({"type": "auth_ok"}))
    time.sleep(0.05)
    # client should have sent a subscribe message
    assert any(m["type"] == "subscribe_events" for m in ws.sent)
    assert "ok" in called
    c.stop()


def test_event_ignored_when_not_in_entities(client):
    c, ws_getter, updates = client
    c.set_entities(["light.only"])
    c.start()
    time.sleep(0.05)
    ws = ws_getter()
    event = {
        "type": "event",
        "event": {
            "event_type": "state_changed",
            "data": {
                "entity_id": "switch.other",
                "new_state": {"state": "on"},
                "old_state": {"state": "off"},
            },
        },
    }
    ws.on_message(ws, json.dumps(event))
    time.sleep(0.05)
    assert updates == []
    c.stop()


def test_result_sets_pending(client):
    c, ws_getter, _ = client
    c.start()
    time.sleep(0.05)
    ws = ws_getter()

    # start service call in thread
    def do_call():
        res = c.call_service("light", "toggle", timeout=1.0)
        assert res == {"ok": 1}

    th = threading.Thread(target=do_call)
    th.start()
    time.sleep(0.1)
    # pick the last sent call_service id
    mid = ws.sent[-1]["id"]
    ws.on_message(
        ws, json.dumps({"id": mid, "type": "result", "success": True, "result": {"ok": 1}})
    )
    th.join()
    c.stop()


def test_send_failure(monkeypatch):
    class BrokenWS:
        def __init__(self, *a, **k):
            self.on_open = k["on_open"]
            self.on_message = k["on_message"]

        def send(self, msg):
            raise RuntimeError("boom")

        def run_forever(self, **kw):
            self.on_message(self, json.dumps({"type": "auth_ok"}))
            time.sleep(0.05)

        def close(self):
            pass

    monkeypatch.setattr("minihometerm.hass_client.websocket.WebSocketApp", BrokenWS)
    c = HAWebSocketClient("ws://fake", "tok")
    c.start()
    time.sleep(0.1)
    c.stop()


def test_reconnect_triggers_on_disconnect(monkeypatch):
    called = {}

    def fake_wsapp(*a, **k):
        raise RuntimeError("fail")

    monkeypatch.setattr("minihometerm.hass_client.websocket.WebSocketApp", fake_wsapp)
    c = HAWebSocketClient(
        "ws://fake", "tok", on_disconnect=lambda e: called.setdefault("err", str(e))
    )
    t = threading.Thread(target=c.start)
    t.start()
    time.sleep(1.2)  # enough for backoff=1s retry attempt
    c.stop()
    t.join()
    assert "err" in called
