"""Minimal webhook sink: appends every POST (headers + raw body) to a JSON-lines file."""
import json
import os
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

LOG_PATH = os.environ.get("LOG_PATH", "/data/webhooks.jsonl")
READ_TOKEN = os.environ["READ_TOKEN"]  # guards GET /events
PORT = int(os.environ.get("PORT", "8080"))
_lock = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length") or 0))
        record = {
            "received_at": datetime.now(timezone.utc).isoformat(),
            "path": self.path,
            "headers": dict(self.headers),
            "body": body.decode("utf-8", errors="replace"),
        }
        with _lock, open(LOG_PATH, "a") as f:
            f.write(json.dumps(record) + "\n")
        self._send(200, b'{"ok":true}', "application/json")

    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/healthz":
            return self._send(200, b"ok", "text/plain")
        if url.path == "/events" and parse_qs(url.query).get("token") == [READ_TOKEN]:
            try:
                with open(LOG_PATH, "rb") as f:
                    data = f.read()
            except FileNotFoundError:
                data = b""
            return self._send(200, data, "application/x-ndjson")
        self._send(404, b"not found", "text/plain")

    def _send(self, status, body, ctype):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
