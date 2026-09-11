"""Lambda Function URL entrypoint: a tiny router, no web framework.

Routes:
  GET  /health          -> post count
  GET  /posts           -> index
  GET  /posts/{slug}    -> one post with markdown body
  POST /chat            -> {"message": str, "history": [{"role","content"}]}
"""

from __future__ import annotations

import base64
import json
import logging

from blog_api import config
from blog_api.agent import ChatAgent, ChatError, ChatResult, ProviderError
from blog_api.content import ContentRepository

logger = logging.getLogger(__name__)

JSON = {"content-type": "application/json"}


class App:
    def __init__(self, repo: ContentRepository, agent, allowed_origin: str = "*") -> None:
        self.repo = repo
        self.agent = agent
        self.allowed_origin = allowed_origin

    # -- routing ---------------------------------------------------------------
    def handle(self, event: dict) -> dict:
        method = event.get("requestContext", {}).get("http", {}).get("method", "GET").upper()
        path = (event.get("rawPath") or "/").rstrip("/") or "/"
        try:
            return self._route(method, path, event)
        except ChatError as e:
            return self._json(400, {"error": str(e)})
        except ProviderError as e:
            # Public text only; the provider's message is already in the logs.
            return self._response(
                503,
                json.dumps({"error": str(e)}, ensure_ascii=False),
                {**JSON, "retry-after": "3600"},
            )
        except Exception:
            logger.exception("unhandled error on %s %s", method, path)
            return self._json(500, {"error": "internal error"})

    def _route(self, method: str, path: str, event: dict) -> dict:
        if method == "OPTIONS":
            return self._response(204, "", {})
        if path == "/health":
            return self._only(method, "GET") or self._json(
                200, {"ok": True, "posts": len(self.repo.list_posts())}
            )
        if path == "/posts":
            return self._only(method, "GET") or self._json(200, {"posts": self.repo.list_posts()})
        if path.startswith("/posts/"):
            slug = path[len("/posts/") :]
            if "/" in slug:
                return self._json(404, {"error": "not found"})
            if denied := self._only(method, "GET"):
                return denied
            post = self.repo.get_post(slug)
            return self._json(200, post) if post else self._json(404, {"error": "not found"})
        if path == "/chat":
            return self._only(method, "POST") or self._chat(event)
        return self._json(404, {"error": "not found"})

    def _only(self, method: str, allowed: str) -> dict | None:
        if method != allowed:
            return self._json(405, {"error": "method not allowed"})
        return None

    def _chat(self, event: dict) -> dict:
        body = _read_body(event)
        try:
            payload = json.loads(body) if body else {}
        except json.JSONDecodeError:
            return self._json(400, {"error": "body must be JSON"})
        if not isinstance(payload, dict) or not isinstance(payload.get("message"), str):
            return self._json(400, {"error": "'message' (string) is required"})
        history = payload.get("history") or []
        if not isinstance(history, list):
            return self._json(400, {"error": "'history' must be a list"})
        result: ChatResult = self.agent.ask(payload["message"], history=history)
        return self._json(
            200, {"answer": result.answer, "sources": result.sources, "usage": result.usage}
        )

    # -- responses ---------------------------------------------------------------
    def _json(self, status: int, payload) -> dict:
        return self._response(status, json.dumps(payload, ensure_ascii=False), JSON)

    def _response(self, status: int, body: str, headers: dict) -> dict:
        return {
            "statusCode": status,
            "headers": {
                **headers,
                "access-control-allow-origin": self.allowed_origin,
                "access-control-allow-methods": "GET, POST, OPTIONS",
                "access-control-allow-headers": "content-type",
                "access-control-max-age": "86400",
            },
            "body": body,
        }


def _read_body(event: dict) -> str:
    body = event.get("body") or ""
    if event.get("isBase64Encoded"):
        body = base64.b64decode(body).decode("utf-8")
    return body


_app: App | None = None


def build_app() -> App:
    from openai import OpenAI

    repo = ContentRepository(config.content_dir())
    client = OpenAI(
        api_key=config.deepseek_api_key(),
        base_url=config.DEEPSEEK_BASE_URL,
        timeout=45.0,
        max_retries=1,
    )
    agent = ChatAgent(repo, client=client, model=config.chat_model())
    return App(repo, agent, allowed_origin=config.allowed_origin())


def lambda_handler(event: dict, context) -> dict:
    global _app
    if _app is None:
        _app = build_app()
    return _app.handle(event)
