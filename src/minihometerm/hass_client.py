import json
import random
import threading
import time
from typing import Any, Callable, Dict, Iterable, Optional, Set

import websocket
from kivy.logger import Logger as logger


class HAWebSocketClient:
    def __init__(
        self,
        url: str,
        token: str,
        entities: Optional[Iterable[str]] = None,
        on_entity_update: Optional[
            Callable[[str, Dict[str, Any], Optional[Dict[str, Any]]], None]
        ] = None,
        on_connect: Optional[Callable[[], None]] = None,
        on_disconnect: Optional[Callable[[Exception | None], None]] = None,
    ):
        self.url = url
        self.token = token
        self.entities: Set[str] = set(entities or [])
        self.on_entity_update = on_entity_update
        self.on_connect = on_connect
        self.on_disconnect = on_disconnect

        self._ws: Optional[websocket.WebSocketApp] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._id = 1
        self._id_lock = threading.Lock()
        self._pending: Dict[int, Dict[str, Any]] = {}
        self._pending_cond = threading.Condition()

        self._backoff = 1.0
        self._max_backoff = 60.0

    # ---------- Public API ----------

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_forever, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._ws:
            try:
                self._ws.close()
            except Exception as e:
                logger.warning("HAWebSocket: Error while closing WebSocket: %s", e)
        if self._thread:
            self._thread.join(timeout=5)

    def set_entities(self, entities: Iterable[str]):
        self.entities = set(entities)

    def call_service(
        self,
        domain: str,
        service: str,
        service_data: Optional[Dict[str, Any]] = None,
        target: Optional[Dict[str, Any]] = None,
        timeout: float = 2.0,
    ) -> Dict[str, Any]:
        msg = {
            "type": "call_service",
            "domain": domain,
            "service": service,
        }
        if service_data:
            msg["service_data"] = service_data
        if target:
            msg["target"] = target

        mid = self._next_id()
        msg["id"] = mid

        with self._pending_cond:
            self._pending[mid] = None
            self._send(msg)
            ok = self._pending_cond.wait_for(
                lambda: self._pending[mid] is not None, timeout=timeout
            )
            resp = self._pending.pop(mid, None)
        if not ok or not resp:
            raise TimeoutError("Service call timed out")
        if resp.get("error") == "disconnected":
            raise ConnectionError("WebSocket disconnected during service call")
        if not resp.get("success", False):
            raise RuntimeError(f"Service call failed: {resp.get('error')}")
        return resp.get("result", {})

    # ---------- Internals ----------

    def _run_forever(self):
        while self._running:
            try:
                self._connect()
            except Exception as e:
                if self.on_disconnect:
                    self.on_disconnect(e)
                delay = min(self._backoff, self._max_backoff)
                jitter = random.uniform(0, delay * 0.2)  # nosec
                wait = delay + jitter
                logger.warning("HAWebSocket: Disconnected: %s, retrying in %.1fs", e, wait)
                time.sleep(wait)
                self._backoff = min(self._backoff * 2, self._max_backoff)

    def _connect(self):
        def on_open(ws):
            logger.info("HAWebSocket: Connected, authenticating…")
            ws.send(json.dumps({"type": "auth", "access_token": self.token}))

        def on_message(ws, message):
            self._handle_message(json.loads(message))

        def on_error(ws, error):
            logger.error("HAWebSocket: WebSocket error: %s", error)

        def on_close(ws, code, msg):
            logger.info("HAWebSocket: WebSocket closed: %s %s", code, msg)

        self._ws = websocket.WebSocketApp(
            self.url,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
        )

        # Blocking loop (returns on disconnect)
        self._ws.run_forever(ping_interval=20)

        # 🚨 After run_forever exits, reject all pending calls
        with self._pending_cond:
            for mid in list(self._pending):
                # Mark them with a special marker so caller sees disconnect
                self._pending[mid] = {"success": False, "error": "disconnected"}
            self._pending_cond.notify_all()

    def _handle_message(self, msg: Dict[str, Any]):
        mtype = msg.get("type")
        if mtype == "auth_required":
            return  # will auth in on_open
        if mtype == "auth_ok":
            self._backoff = 1.0
            logger.info("HAWebSocket: Auth OK")

            mid = self._next_id()
            self._send({"id": mid, "type": "subscribe_events", "event_type": "state_changed"})

            if self.on_connect:
                self.on_connect()
            return
        if mtype == "event":
            event = msg.get("event", {})
            if event.get("event_type") == "state_changed":
                data = event.get("data", {})
                eid = data.get("entity_id")
                if self.entities and eid not in self.entities:
                    return
                if self.on_entity_update:
                    self.on_entity_update(eid, data.get("new_state"), data.get("old_state"))
            return
        if mtype == "result":
            mid = msg.get("id")
            if mid:
                with self._pending_cond:
                    self._pending[mid] = msg
                    self._pending_cond.notify_all()

    def _send(self, payload: Dict[str, Any]):
        try:
            if self._ws:
                self._ws.send(json.dumps(payload))
        except Exception as e:
            logger.error("HAWebSocket: Send failed: %s", e)

    def _next_id(self) -> int:
        with self._id_lock:
            mid = self._id
            self._id += 1
            return mid
