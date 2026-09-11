"""Run the Lambda handler on localhost, translating HTTP into Function URL events.

set -a; . ./.env; set +a; .venv/bin/python dev_server.py 8791
"""

from __future__ import annotations

import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from blog_api.handler import lambda_handler


class Handler(BaseHTTPRequestHandler):
    def _serve(self) -> None:
        length = int(self.headers.get("content-length") or 0)
        body = self.rfile.read(length).decode("utf-8") if length else None
        event = {
            "version": "2.0",
            "rawPath": self.path.split("?", 1)[0],
            "requestContext": {"http": {"method": self.command, "path": self.path}},
            "headers": {k.lower(): v for k, v in self.headers.items()},
            "body": body,
            "isBase64Encoded": False,
        }
        result = lambda_handler(event, None)
        payload = result.get("body", "").encode("utf-8")
        self.send_response(result["statusCode"])
        for key, value in result.get("headers", {}).items():
            self.send_header(key, value)
        self.send_header("content-length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    do_GET = do_POST = do_OPTIONS = do_DELETE = _serve

    def log_message(self, fmt, *args):
        sys.stderr.write(f"{self.command} {fmt % args}\n")


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8791
    print(f"blog api on http://localhost:{port}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
