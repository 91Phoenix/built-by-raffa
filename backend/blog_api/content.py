"""Read-only access to the built corpus: the post index, bodies and a search.

Search is plain term scoring. The corpus is a dozen posts, so a keyword
index beats embeddings here: no vector store, no embedding calls, and the
agent can always read the full post when a hit looks promising.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

_WORD = re.compile(r"[a-z0-9][a-z0-9+#./-]*")
_STOPWORDS = {
    "a",
    "an",
    "the",
    "and",
    "or",
    "of",
    "to",
    "in",
    "on",
    "for",
    "with",
    "is",
    "are",
    "was",
    "were",
    "be",
    "it",
    "that",
    "this",
    "as",
    "at",
    "by",
    "from",
    "he",
    "his",
    "has",
    "have",
    "had",
    "did",
    "does",
    "do",
    "about",
    "any",
    "what",
    "which",
    "who",
    "how",
    "you",
    "your",
    "i",
    "my",
    "me",
    "raffaele",
    "raffa",
    "ever",
    "used",
    "use",
    "using",
    "experience",
}


def _tokens(text: str) -> list[str]:
    return [t.strip("./-") for t in _WORD.findall(text.lower()) if t.strip("./-")]


class ContentRepository:
    def __init__(self, content_dir: Path | str) -> None:
        self.content_dir = Path(content_dir)
        index = json.loads((self.content_dir / "index.json").read_text(encoding="utf-8"))
        self.site_url: str = index["site_url"]
        self._posts: list[dict] = index["posts"]
        self._by_slug = {p["slug"]: p for p in self._posts}
        self._bodies: dict[str, str] = {}

    def list_posts(self) -> list[dict]:
        return [dict(p) for p in self._posts]

    def _body(self, slug: str) -> str:
        if slug not in self._bodies:
            path = self.content_dir / "posts" / f"{slug}.md"
            self._bodies[slug] = path.read_text(encoding="utf-8")
        return self._bodies[slug]

    def get_post(self, slug: str) -> dict | None:
        meta = self._by_slug.get(slug)
        if meta is None:
            return None
        return {**meta, "body": self._body(slug)}

    def search(self, query: str, limit: int = 5) -> list[dict]:
        terms = [t for t in _tokens(query) if t not in _STOPWORDS]
        if not terms:
            return []
        hits = []
        for meta in self._posts:
            body = self._body(meta["slug"])
            title_tokens = _tokens(meta["title"])
            tag_tokens = _tokens(" ".join(meta["tags"]))
            body_tokens = _tokens(body)
            score = 0.0
            for term in terms:
                score += 5.0 * title_tokens.count(term)
                score += 5.0 * tag_tokens.count(term)
                score += min(body_tokens.count(term), 10)
            if score > 0:
                hits.append(
                    {
                        "slug": meta["slug"],
                        "title": meta["title"],
                        "url": meta["url"],
                        "score": score,
                        "snippet": _snippet(body, terms),
                    }
                )
        hits.sort(key=lambda h: h["score"], reverse=True)
        return hits[:limit]


def _snippet(body: str, terms: list[str], width: int = 240) -> str:
    lower = body.lower()
    positions = [lower.find(t) for t in terms]
    positions = [p for p in positions if p >= 0]
    if not positions:
        return body[:width].strip()
    start = max(0, min(positions) - width // 3)
    chunk = body[start : start + width].replace("\n", " ").strip()
    return ("…" if start else "") + chunk + ("…" if start + width < len(body) else "")
