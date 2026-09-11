"""Tool-calling chat over the posts, in the style of an LLM wiki.

The model gets three tools (list, search, read) and decides what to open,
so each answer costs a handful of tool rounds instead of the whole corpus in
context. Posts it actually read are returned as sources, so the UI can link
them and the reader can check the claim.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

import openai

from blog_api.content import ContentRepository

logger = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 6

SYSTEM_PROMPT = """\
You are the assistant of Bradicode, Raffaele Rotella's engineering blog.
Visitors ask whether Raffaele has experience with some technology, problem or
practice. Answer only from the blog posts, using the tools:

- list_posts: every post with title, date, tags and excerpt. Cheap; call it first.
- search_posts: keyword search over post bodies; returns snippets.
- read_post: the full markdown of one post. Read a post before citing details from it.

Rules:
- Ground every claim in a post you read. Mention the post title when you draw on it.
- If the posts do not cover the question, say so plainly and suggest the closest post, if any.
- Be concise: a short paragraph, or a few bullets for several items. No preamble.
- Never invent projects, employers, dates or numbers.
- Answer in the language of the question.
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_posts",
            "description": "List every blog post: slug, title, date, tags and excerpt.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_posts",
            "description": "Keyword search over post titles, tags and bodies; ranked snippets.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "Search terms."}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_post",
            "description": "Return the full markdown of one post, by slug.",
            "parameters": {
                "type": "object",
                "properties": {"slug": {"type": "string"}},
                "required": ["slug"],
            },
        },
    },
]


class ChatError(Exception):
    """A request the caller can fix: bad input, or a run that did not converge."""


class ProviderError(Exception):
    """DeepSeek did not serve the request. `str()` is safe to show a visitor;
    `detail` is the provider's text and goes to the logs only."""

    def __init__(self, public_message: str, status: int | None, detail: str = "") -> None:
        super().__init__(public_message)
        self.status = status
        self.detail = detail


# DeepSeek answers 402 "Insufficient Balance" when the prepaid credit is gone;
# the page says so instead of a generic error, and CloudWatch gets the detail.
PROVIDER_MESSAGES = {
    401: "The chat is misconfigured on the server side.",
    402: "The chat is out of credit for now. The posts are still here to read.",
    429: "The chat is busy right now; try again in a minute.",
}


def _provider_error(error: Exception) -> ProviderError:
    if isinstance(error, openai.APIStatusError):
        status = error.status_code
        detail = str(getattr(error, "message", None) or error)
        public = PROVIDER_MESSAGES.get(
            status, "The chat provider is unavailable right now; try again later."
        )
        return ProviderError(public, status=status, detail=detail)
    return ProviderError(
        "The chat provider is unreachable right now; try again later.",
        status=None,
        detail=str(error),
    )


@dataclass
class ChatResult:
    answer: str
    sources: list[dict] = field(default_factory=list)
    usage: dict = field(default_factory=lambda: {"prompt_tokens": 0, "completion_tokens": 0})


class ChatAgent:
    def __init__(
        self,
        repo: ContentRepository,
        client,
        model: str,
        max_history: int = 10,
        max_message_chars: int = 1000,
        max_output_tokens: int = 800,
    ) -> None:
        self.repo = repo
        self.client = client
        self.model = model
        self.max_history = max_history
        self.max_message_chars = max_message_chars
        self.max_output_tokens = max_output_tokens

    def ask(self, message: str, history: list[dict] | None = None) -> ChatResult:
        message = (message or "").strip()
        if not message:
            raise ChatError("message is empty")
        if len(message) > self.max_message_chars:
            raise ChatError(f"message longer than {self.max_message_chars} characters")

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages += _clean_history(history or [], self.max_history)
        messages.append({"role": "user", "content": message})

        usage = {"prompt_tokens": 0, "completion_tokens": 0}
        read_slugs: list[str] = []

        for _ in range(MAX_TOOL_ROUNDS + 1):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=TOOLS,
                    max_tokens=self.max_output_tokens,
                    temperature=0.2,
                )
            except (openai.APIStatusError, openai.APIConnectionError) as error:
                provider_error = _provider_error(error)
                logger.error(
                    "deepseek request failed: status=%s detail=%s",
                    provider_error.status,
                    provider_error.detail,
                )
                raise provider_error from error
            if getattr(response, "usage", None):
                usage["prompt_tokens"] += response.usage.prompt_tokens or 0
                usage["completion_tokens"] += response.usage.completion_tokens or 0

            reply = response.choices[0].message
            tool_calls = getattr(reply, "tool_calls", None) or []
            if not tool_calls:
                return ChatResult(
                    answer=(reply.content or "").strip(),
                    sources=self._sources(read_slugs),
                    usage=usage,
                )

            messages.append(
                {
                    "role": "assistant",
                    "content": reply.content,
                    "tool_calls": [
                        {
                            "id": call.id,
                            "type": "function",
                            "function": {
                                "name": call.function.name,
                                "arguments": call.function.arguments,
                            },
                        }
                        for call in tool_calls
                    ],
                }
            )
            for call in tool_calls:
                result = self._run_tool(call.function.name, call.function.arguments, read_slugs)
                messages.append({"role": "tool", "tool_call_id": call.id, "content": result})

        raise ChatError("the assistant could not finish answering; try a narrower question")

    def _run_tool(self, name: str, raw_args: str, read_slugs: list[str]) -> str:
        try:
            args = json.loads(raw_args) if raw_args else {}
        except json.JSONDecodeError:
            return "Error: tool arguments were not valid JSON."
        if name == "list_posts":
            return json.dumps(self.repo.list_posts(), ensure_ascii=False)
        if name == "search_posts":
            return json.dumps(self.repo.search(str(args.get("query", ""))), ensure_ascii=False)
        if name == "read_post":
            slug = str(args.get("slug", ""))
            post = self.repo.get_post(slug)
            if post is None:
                return f"Error: no post with slug '{slug}'. Use list_posts to see the slugs."
            if slug not in read_slugs:
                read_slugs.append(slug)
            return post["body"]
        return f"Error: unknown tool '{name}'."

    def _sources(self, slugs: list[str]) -> list[dict]:
        out = []
        for slug in slugs:
            post = self.repo.get_post(slug)
            if post:
                out.append({"slug": slug, "title": post["title"], "url": post["url"]})
        return out


def _clean_history(history: list[dict], max_items: int) -> list[dict]:
    cleaned = []
    for item in history:
        role = item.get("role") if isinstance(item, dict) else None
        content = item.get("content") if isinstance(item, dict) else None
        if role in ("user", "assistant") and isinstance(content, str) and content.strip():
            cleaned.append({"role": role, "content": content[:4000]})
    return cleaned[-max_items:]
