import json
from types import SimpleNamespace

import pytest

from blog_api import handler as handler_module
from blog_api.agent import ChatError, ChatResult
from blog_api.build_content import build_content
from blog_api.content import ContentRepository


class FakeAgent:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.calls = []

    def ask(self, message, history=None):
        self.calls.append((message, history))
        if self.error:
            raise self.error
        return self.result


@pytest.fixture
def app(site_dir, tmp_path):
    out = tmp_path / "content"
    build_content(site_dir, out, site_url="https://bradicode.com")
    repo = ContentRepository(out)
    agent = FakeAgent(
        result=ChatResult(
            answer="He did.",
            sources=[{"slug": "s", "title": "T", "url": "https://bradicode.com/posts/s.html"}],
            usage={"prompt_tokens": 1, "completion_tokens": 1},
        )
    )
    return handler_module.App(repo, agent, allowed_origin="https://bradicode.com"), agent


def event(method, path, body=None, origin="https://bradicode.com"):
    headers = {"content-type": "application/json"}
    if origin:
        headers["origin"] = origin
    return {
        "version": "2.0",
        "rawPath": path,
        "requestContext": {"http": {"method": method, "path": path}},
        "headers": headers,
        "body": json.dumps(body) if body is not None else None,
        "isBase64Encoded": False,
    }


def test_get_posts_lists_index(app):
    a, _ = app
    res = a.handle(event("GET", "/posts"))
    assert res["statusCode"] == 200
    assert res["headers"]["content-type"] == "application/json"
    body = json.loads(res["body"])
    assert [p["slug"] for p in body["posts"]] == ["crawling-with-scrapy", "second-post"]


def test_get_single_post_and_404(app):
    a, _ = app
    ok = a.handle(event("GET", "/posts/crawling-with-scrapy"))
    assert ok["statusCode"] == 200
    assert json.loads(ok["body"])["body"].startswith("# The Bugs")
    missing = a.handle(event("GET", "/posts/nope"))
    assert missing["statusCode"] == 404
    assert json.loads(missing["body"]) == {"error": "not found"}


def test_post_chat_calls_agent_with_history(app):
    a, agent = app
    res = a.handle(
        event(
            "POST", "/chat", {"message": "Scrapy?", "history": [{"role": "user", "content": "hi"}]}
        )
    )
    assert res["statusCode"] == 200
    body = json.loads(res["body"])
    assert body["answer"] == "He did."
    assert body["sources"][0]["slug"] == "s"
    assert agent.calls == [("Scrapy?", [{"role": "user", "content": "hi"}])]


def test_post_chat_invalid_json_and_missing_message_are_400(app):
    a, _ = app
    bad = event("POST", "/chat")
    bad["body"] = "{not json"
    assert a.handle(bad)["statusCode"] == 400
    assert a.handle(event("POST", "/chat", {"history": []}))["statusCode"] == 400
    assert a.handle(event("POST", "/chat", {"message": 3}))["statusCode"] == 400


def test_chat_error_maps_to_400_and_unexpected_to_500(site_dir, tmp_path):
    out = tmp_path / "content"
    build_content(site_dir, out, site_url="https://x")
    repo = ContentRepository(out)
    a = handler_module.App(repo, FakeAgent(error=ChatError("too long")), allowed_origin="*")
    res = a.handle(event("POST", "/chat", {"message": "x"}))
    assert res["statusCode"] == 400
    assert json.loads(res["body"]) == {"error": "too long"}

    a = handler_module.App(repo, FakeAgent(error=RuntimeError("boom")), allowed_origin="*")
    res = a.handle(event("POST", "/chat", {"message": "x"}))
    assert res["statusCode"] == 500
    assert "boom" not in res["body"]


def test_cors_headers_and_preflight(app):
    a, _ = app
    res = a.handle(event("OPTIONS", "/chat"))
    assert res["statusCode"] == 204
    assert res["headers"]["access-control-allow-origin"] == "https://bradicode.com"
    assert "POST" in res["headers"]["access-control-allow-methods"]
    got = a.handle(event("GET", "/posts"))
    assert got["headers"]["access-control-allow-origin"] == "https://bradicode.com"


def test_unknown_route_and_method(app):
    a, _ = app
    assert a.handle(event("GET", "/nope"))["statusCode"] == 404
    assert a.handle(event("DELETE", "/posts"))["statusCode"] == 405


def test_health(app):
    a, _ = app
    res = a.handle(event("GET", "/health"))
    assert res["statusCode"] == 200
    assert json.loads(res["body"])["posts"] == 2


def test_base64_body_is_decoded(app):
    import base64

    a, agent = app
    ev = event("POST", "/chat")
    ev["body"] = base64.b64encode(json.dumps({"message": "b64"}).encode()).decode()
    ev["isBase64Encoded"] = True
    assert a.handle(ev)["statusCode"] == 200
    assert agent.calls[0][0] == "b64"


def test_lambda_handler_entrypoint_builds_app_lazily(monkeypatch, site_dir, tmp_path):
    out = tmp_path / "content"
    build_content(site_dir, out, site_url="https://x")
    monkeypatch.setenv("CONTENT_DIR", str(out))
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test")
    monkeypatch.setattr(handler_module, "_app", None)
    res = handler_module.lambda_handler(event("GET", "/health"), SimpleNamespace())
    assert res["statusCode"] == 200


def test_provider_error_maps_to_503_with_public_message_only(site_dir, tmp_path):
    from blog_api.agent import ProviderError

    out = tmp_path / "content"
    build_content(site_dir, out, site_url="https://x")
    repo = ContentRepository(out)
    err = ProviderError("The chat is out of credit for now.", status=402, detail="sk-secret leak")
    a = handler_module.App(repo, FakeAgent(error=err), allowed_origin="*")
    res = a.handle(event("POST", "/chat", {"message": "x"}))
    assert res["statusCode"] == 503
    assert json.loads(res["body"]) == {"error": "The chat is out of credit for now."}
    assert "sk-secret" not in res["body"]
    assert res["headers"]["retry-after"] == "3600"
