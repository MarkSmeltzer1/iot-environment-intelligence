"""
Local MQTT monitor web page.

Subscribes to the raw MQTT topic and serves a small browser page that shows
incoming payloads as they arrive. This is useful for demos because MQTT port
1883 is not an HTTP page.
"""
import json
import os
import threading
from collections import deque
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Deque, Dict, List
from urllib.parse import urlparse

import paho.mqtt.client as mqtt

from src.utils.config_loader import load_config
from src.utils.logger import setup_logger


logger = setup_logger("mqtt_monitor")
MESSAGES: Deque[Dict[str, Any]] = deque(maxlen=100)
MESSAGES_LOCK = threading.Lock()


def _utc_now() -> str:
    """Return current UTC time for display."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _format_payload(payload: str) -> str:
    """Pretty-print JSON payloads, leaving malformed payloads readable."""
    try:
        return json.dumps(json.loads(payload), indent=2, sort_keys=True)
    except json.JSONDecodeError:
        return payload


def add_message(topic: str, payload: str) -> Dict[str, Any]:
    """Store one received MQTT message for the web page."""
    record = {
        "received_at": _utc_now(),
        "topic": topic,
        "payload": payload,
        "pretty_payload": _format_payload(payload),
    }

    with MESSAGES_LOCK:
        MESSAGES.appendleft(record)
        count = len(MESSAGES)

    logger.info("Monitor captured MQTT message on %s", topic)
    record["buffered_count"] = count
    return record


def get_messages() -> List[Dict[str, Any]]:
    """Return buffered messages newest-first."""
    with MESSAGES_LOCK:
        return list(MESSAGES)


def build_mqtt_client(config: Dict[str, Any]) -> mqtt.Client:
    """Create and configure the MQTT subscriber client."""
    mqtt_config = config["mqtt"]
    topic = os.getenv("MQTT_TOPIC_RAW", mqtt_config["topic_raw"])

    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id="environment_web_monitor",
    )

    def on_connect(client, userdata, flags, reason_code, properties=None):
        if str(reason_code) in ("0", "Success"):
            logger.info("Monitor connected to MQTT broker and subscribed to %s", topic)
            client.subscribe(topic)
        else:
            logger.error("Monitor failed to connect to MQTT broker: %s", reason_code)

    def on_message(client, userdata, msg):
        add_message(msg.topic, msg.payload.decode("utf-8", errors="replace"))

    client.on_connect = on_connect
    client.on_message = on_message
    return client


class MonitorRequestHandler(BaseHTTPRequestHandler):
    """HTTP handler for the monitor page and JSON API."""

    def do_GET(self):
        parsed_path = urlparse(self.path)

        if parsed_path.path == "/":
            self._send_html()
        elif parsed_path.path == "/api/messages":
            self._send_json({"messages": get_messages()})
        elif parsed_path.path == "/api/status":
            self._send_json({"status": "running", "message_count": len(get_messages())})
        else:
            self.send_error(404, "Not found")

    def log_message(self, format, *args):
        logger.info("HTTP %s", format % args)

    def _send_json(self, data: Dict[str, Any]):
        encoded = json.dumps(data).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _send_html(self):
        encoded = MONITOR_HTML.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


MONITOR_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>MQTT Live Monitor</title>
  <style>
    :root {
      color-scheme: dark;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #101418;
      color: #e9eef2;
    }
    body {
      margin: 0;
      padding: 24px;
      background: #101418;
    }
    header {
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      gap: 16px;
      margin-bottom: 18px;
    }
    h1 {
      font-size: 28px;
      margin: 0;
      font-weight: 700;
    }
    .status {
      color: #9fb0bd;
      font-size: 14px;
    }
    .grid {
      display: grid;
      gap: 12px;
    }
    .message {
      border: 1px solid #2b3944;
      border-radius: 8px;
      background: #151c22;
      overflow: hidden;
    }
    .meta {
      display: grid;
      grid-template-columns: minmax(180px, 240px) 1fr;
      gap: 12px;
      padding: 12px 14px;
      background: #1b252d;
      border-bottom: 1px solid #2b3944;
      font-size: 14px;
    }
    .label {
      color: #91a6b5;
    }
    pre {
      margin: 0;
      padding: 14px;
      white-space: pre-wrap;
      word-break: break-word;
      font-size: 14px;
      line-height: 1.45;
      color: #d8f3dc;
    }
    .empty {
      border: 1px dashed #3a4b57;
      border-radius: 8px;
      color: #9fb0bd;
      padding: 20px;
    }
  </style>
</head>
<body>
  <header>
    <h1>MQTT Live Monitor</h1>
    <div class="status" id="status">Waiting for messages...</div>
  </header>
  <main class="grid" id="messages">
    <div class="empty">No MQTT messages received yet.</div>
  </main>
  <script>
    async function loadMessages() {
      const response = await fetch('/api/messages', { cache: 'no-store' });
      const data = await response.json();
      const messages = data.messages || [];
      const container = document.getElementById('messages');
      const status = document.getElementById('status');
      status.textContent = `${messages.length} buffered message(s), refreshed ${new Date().toLocaleTimeString()}`;

      if (messages.length === 0) {
        container.innerHTML = '<div class="empty">No MQTT messages received yet.</div>';
        return;
      }

      container.innerHTML = messages.map((message, index) => `
        <section class="message">
          <div class="meta">
            <div><span class="label">#</span> ${messages.length - index}</div>
            <div><span class="label">Received</span> ${message.received_at}</div>
            <div><span class="label">Topic</span> ${message.topic}</div>
            <div><span class="label">Payload</span> raw MQTT JSON</div>
          </div>
          <pre>${escapeHtml(message.pretty_payload)}</pre>
        </section>
      `).join('');
    }

    function escapeHtml(value) {
      return String(value)
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#039;');
    }

    loadMessages();
    setInterval(loadMessages, 1000);
  </script>
</body>
</html>
"""


def main() -> int:
    """Run the MQTT monitor web server."""
    config = load_config()
    mqtt_config = config["mqtt"]
    broker = os.getenv("MQTT_BROKER", mqtt_config["broker"])
    port = int(os.getenv("MQTT_PORT", mqtt_config["port"]))
    keepalive = mqtt_config["keepalive"]

    client = build_mqtt_client(config)
    client.connect(broker, port, keepalive)
    client.loop_start()

    host = os.getenv("MONITOR_HOST", "0.0.0.0")
    monitor_port = int(os.getenv("MONITOR_PORT", "8600"))
    server = ThreadingHTTPServer((host, monitor_port), MonitorRequestHandler)
    logger.info("MQTT monitor available at http://localhost:%s", monitor_port)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Stopping MQTT monitor")
    finally:
        server.server_close()
        client.loop_stop()
        client.disconnect()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
