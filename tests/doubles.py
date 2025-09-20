# tests/doubles.py
import json
import threading


class DummyWS:
    """
    Minimal WebSocketApp-compatible double with deterministic lifecycle.
    """

    def __init__(self, url, on_open=None, on_message=None, on_error=None, on_close=None):
        self.url = url
        self.on_open = on_open
        self.on_message = on_message
        self.on_error = on_error
        self.on_close = on_close

        self._closed = threading.Event()
        self._started = threading.Event()
        self.sent = []  # list of parsed JSON payloads
        self.raw_sent = []  # raw JSON strings (optional)
        self._lock = threading.Lock()

    @property
    def closed(self) -> bool:
        """Return True if the websocket has been closed."""
        return self._closed.is_set()

    # WebSocketApp API compatibility
    def run_forever(self, *_, **__):
        # Signal that run_forever has started; helpful for tests to wait on readiness
        self._started.set()

        # Simulate server lifecycle: call on_open once
        if self.on_open:
            try:
                self.on_open(self)
            except Exception as e:
                if self.on_error:
                    self.on_error(self, e)

        # Block until closed; no busy loop, no sleep race
        self._closed.wait()

        # Simulate a clean close
        if self.on_close:
            self.on_close(self, 1000, "dummy close")

    def close(self):
        # Unblock run_forever and let it return
        self._closed.set()

    def send(self, data):
        # Capture outgoing messages from client
        with self._lock:
            self.raw_sent.append(data)
            try:
                self.sent.append(json.loads(data))
            except Exception:
                # Keep raw if not JSON
                pass

    def server_send(self, payload: dict):
        if self.on_message:
            self.on_message(self, json.dumps(payload))
