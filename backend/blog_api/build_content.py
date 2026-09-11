"""Build the agent's corpus from the static site.

Reads `posts/index.html` for the card metadata (date, title, excerpt, tags)
and each `posts/<slug>.html` for the body, then writes `index.json` plus one
markdown file per post. The output is bundled into the Lambda zip, so the
API needs no database: the repo is the source of truth.

Usage: python -m blog_api.build_content <site_dir> <out_dir> --site-url URL
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from html.parser import HTMLParser
from pathlib import Path

from blog_api.html_to_text import post_from_html


@dataclass
class Card:
    slug: str
    date: str
    title: str
    excerpt: str
    tags: list[str]


class _CardParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.cards: list[Card] = []
        self._card: Card | None = None
        self._field: str | None = None
        self._buf: list[str] = []
        self._depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = dict(attrs)
        classes = (a.get("class") or "").split()
        if tag == "a" and "post-card" in classes:
            href = a.get("href") or ""
            slug = re.sub(r"\.html$", "", href.rsplit("/", 1)[-1])
            self._card = Card(slug=slug, date="", title="", excerpt="", tags=[])
            return
        if self._card is None:
            return
        for cls, name in (
            ("post-date", "date"),
            ("post-title", "title"),
            ("post-excerpt", "excerpt"),
            ("post-tag", "tag"),
        ):
            if cls in classes:
                self._field = name
                self._buf = []
                self._depth = 0
                return
        if self._field is not None:
            self._depth += 1

    def handle_endtag(self, tag: str) -> None:
        if self._card is None:
            return
        if tag == "a":
            self.cards.append(self._card)
            self._card = None
            return
        if self._field is None:
            return
        if self._depth:
            self._depth -= 1
            return
        text = re.sub(r"\s+", " ", "".join(self._buf)).strip()
        if self._field == "tag":
            self._card.tags.append(text)
        else:
            setattr(self._card, self._field, text)
        self._field = None

    def handle_data(self, data: str) -> None:
        if self._card is not None and self._field is not None:
            self._buf.append(data)


def read_cards(index_html: Path) -> list[Card]:
    parser = _CardParser()
    parser.feed(index_html.read_text(encoding="utf-8"))
    parser.close()
    return parser.cards


def build_content(site_dir: Path, out_dir: Path, site_url: str) -> dict:
    site_url = site_url.rstrip("/")
    posts_dir = site_dir / "posts"
    cards = read_cards(posts_dir / "index.html")
    (out_dir / "posts").mkdir(parents=True, exist_ok=True)

    entries = []
    for card in cards:
        source = posts_dir / f"{card.slug}.html"
        if not source.exists():
            raise FileNotFoundError(f"card '{card.slug}' in posts/index.html has no {source}")
        doc = post_from_html(source.read_text(encoding="utf-8"))
        title = doc.title or card.title
        markdown = f"# {title}\n\n{doc.body}\n"
        (out_dir / "posts" / f"{card.slug}.md").write_text(markdown, encoding="utf-8")
        entry = asdict(card)
        entry.update(
            title=title,
            read_time=doc.read_time,
            url=f"{site_url}/posts/{card.slug}.html",
        )
        entries.append(entry)

    index = {"site_url": site_url, "posts": entries}
    (out_dir / "index.json").write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n")
    return index


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("site_dir", type=Path)
    ap.add_argument("out_dir", type=Path)
    ap.add_argument("--site-url", required=True)
    args = ap.parse_args(argv)
    index = build_content(args.site_dir, args.out_dir, args.site_url)
    print(f"wrote {len(index['posts'])} posts to {args.out_dir}")


if __name__ == "__main__":
    main()
