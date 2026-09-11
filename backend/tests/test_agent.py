import json
from types import SimpleNamespace

import pytest

from blog_api.agent import MAX_TOOL_ROUNDS, ChatAgent, ChatError
from blog_api.build_content import build_content
from blog_api.content import ContentRepository


@pytest.fixture
def repo(site_dir, tmp_path):
    out = tmp_path / "content"
    build_content(site_dir, out, site_url="https://bradicode.dev")
    return ContentRepository(out)


def _tool_call(call_id, name, args):
    return SimpleNamespace(
        id=call_id,
        type="function",
        function=SimpleNamespace(name=name, arguments=json.dumps(args)),
    )


def _message(content=None, tool_calls=None):
    return SimpleNamespace(content=content, tool_calls=tool_calls)


def _response(message, prompt=10, completion=5):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=message)],
        usage=SimpleNamespace(prompt_tokens=prompt, completion_tokens=completion),
    )


class FakeCompletions:
    """Scripted stand-in for `client.chat.completions`."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.responses.pop(0)


def _agent(repo, responses):
    completions = FakeCompletions(responses)
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    return ChatAgent(repo, client=client, model="test-model"), completions


def test_answers_directly_without_tools(repo):
    agent, completions = _agent(repo, [_response(_message("Hi, ask me about the posts."))])
    result = agent.ask("hello")
    assert result.answer == "Hi, ask me about the posts."
    assert result.sources == []
    assert result.usage == {"prompt_tokens": 10, "completion_tokens": 5}
    sent = completions.calls[0]
    assert sent["model"] == "test-model"
    assert sent["messages"][0]["role"] == "system"
    assert sent["messages"][-1] == {"role": "user", "content": "hello"}
    assert {t["function"]["name"] for t in sent["tools"]} == {
        "list_posts",
        "search_posts",
        "read_post",
    }


def test_runs_tools_and_reports_read_posts_as_sources(repo):
    agent, completions = _agent(
        repo,
        [
            _response(_message(tool_calls=[_tool_call("c1", "search_posts", {"query": "scrapy"})])),
            _response(
                _message(
                    tool_calls=[_tool_call("c2", "read_post", {"slug": "crawling-with-scrapy"})]
                )
            ),
            _response(_message("Yes: he rewrote a scraper in Scrapy."), prompt=100, completion=20),
        ],
    )
    result = agent.ask("Has Raffaele used Scrapy?")
    assert result.answer == "Yes: he rewrote a scraper in Scrapy."
    assert result.sources == [
        {
            "slug": "crawling-with-scrapy",
            "title": "The Bugs I Couldn't See: Rewriting a Scraper",
            "url": "https://bradicode.dev/posts/crawling-with-scrapy.html",
        }
    ]
    # usage accumulates across rounds
    assert result.usage == {"prompt_tokens": 120, "completion_tokens": 30}
    # tool results were fed back with the matching call ids
    third_call_messages = completions.calls[2]["messages"]
    tool_msgs = [m for m in third_call_messages if m["role"] == "tool"]
    assert [m["tool_call_id"] for m in tool_msgs] == ["c1", "c2"]
    assert "## Part 1" in tool_msgs[1]["content"]


def test_unknown_tool_and_bad_slug_return_error_text_not_exceptions(repo):
    agent, completions = _agent(
        repo,
        [
            _response(
                _message(
                    tool_calls=[
                        _tool_call("c1", "read_post", {"slug": "missing"}),
                        _tool_call("c2", "explode", {}),
                    ]
                )
            ),
            _response(_message("Not covered.")),
        ],
    )
    result = agent.ask("anything")
    tool_msgs = [m for m in completions.calls[1]["messages"] if m["role"] == "tool"]
    assert "no post" in tool_msgs[0]["content"].lower()
    assert "unknown tool" in tool_msgs[1]["content"].lower()
    assert result.sources == []


def test_history_is_included_but_capped(repo):
    agent, completions = _agent(repo, [_response(_message("ok"))])
    history = [
        {"role": "user" if i % 2 == 0 else "assistant", "content": f"m{i}"} for i in range(30)
    ]
    agent.ask("latest", history=history)
    msgs = completions.calls[0]["messages"]
    non_system = [m for m in msgs if m["role"] != "system"]
    assert non_system[-1]["content"] == "latest"
    assert len(non_system) <= agent.max_history + 1
    assert non_system[0]["content"] == "m20"


def test_gives_up_after_max_tool_rounds(repo):
    looping = [
        _response(_message(tool_calls=[_tool_call(f"c{i}", "list_posts", {})]))
        for i in range(MAX_TOOL_ROUNDS + 1)
    ]
    agent, _ = _agent(repo, looping)
    with pytest.raises(ChatError):
        agent.ask("loop forever")


def test_rejects_empty_or_too_long_messages(repo):
    agent, _ = _agent(repo, [])
    with pytest.raises(ChatError):
        agent.ask("   ")
    with pytest.raises(ChatError):
        agent.ask("x" * (agent.max_message_chars + 1))


def _api_status_error(status, message):
    import httpx
    import openai

    request = httpx.Request("POST", "https://api.deepseek.com/chat/completions")
    response = httpx.Response(status, request=request, json={"error": {"message": message}})
    return openai.APIStatusError(message, response=response, body={"error": {"message": message}})


class RaisingCompletions:
    def __init__(self, error):
        self.error = error

    def create(self, **kwargs):
        raise self.error


def _raising_agent(repo, error):
    client = SimpleNamespace(chat=SimpleNamespace(completions=RaisingCompletions(error)))
    return ChatAgent(repo, client=client, model="test-model")


@pytest.mark.parametrize(
    "status,message,expected",
    [
        (402, "Insufficient Balance", "out of credit"),
        (429, "Rate limit reached", "busy"),
        (401, "Authentication Fails", "misconfigured"),
        (503, "Server overloaded", "unavailable"),
    ],
)
def test_provider_status_errors_become_provider_error(repo, status, message, expected):
    from blog_api.agent import ProviderError

    agent = _raising_agent(repo, _api_status_error(status, message))
    with pytest.raises(ProviderError) as info:
        agent.ask("anything")
    assert info.value.status == status
    assert expected in str(info.value).lower()
    assert message in info.value.detail


def test_provider_connection_error_becomes_provider_error(repo):
    import httpx
    import openai

    from blog_api.agent import ProviderError

    request = httpx.Request("POST", "https://api.deepseek.com/chat/completions")
    agent = _raising_agent(repo, openai.APIConnectionError(request=request))
    with pytest.raises(ProviderError) as info:
        agent.ask("anything")
    assert info.value.status is None
    assert "unreachable" in str(info.value).lower()
