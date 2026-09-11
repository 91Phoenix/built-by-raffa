"""Turn a post's HTML into a markdown-like document the chat agent can read.

The blog posts are hand-written HTML. The agent works better on plain text
with the structure kept (headings, lists, code, tables), so this walks the
`<article>` and emits markdown. Stdlib only: the Lambda package stays small.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from html.parser import HTMLParser

SKIPPED_TAGS = {"svg", "script", "style", "nav", "footer"}
BLOCK_TAGS = {"p", "h1", "h2", "h3", "h4", "li", "pre", "blockquote", "figcaption", "tr", "hr"}
HEADING_PREFIX = {"h1": "# ", "h2": "## ", "h3": "### ", "h4": "#### "}


@dataclass
class PostDocument:
    title: str
    date: str
    read_time: str
    body: str


@dataclass
class _Block:
    tag: str
    text: list[str] = field(default_factory=list)
    cells: list[str] = field(default_factory=list)
    header_row: bool = False


class _ArticleParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.date = ""
        self.read_time = ""
        self.lines: list[str] = []
        self._skip_depth = 0
        self._in_article = False
        self._block: _Block | None = None
        self._in_pre = False
        self._in_cell = False
        self._meta_spans: list[str] = []
        self._in_meta = False
        self._meta_div_depth = 0
        self._div_depth = 0
        self._current_span: list[str] | None = None
        self._table_rows = 0

    # -- tag handling -----------------------------------------------------
    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        if tag in SKIPPED_TAGS or self._skip_depth:
            self._skip_depth += 1
            return
        if tag == "article":
            self._in_article = True
            return
        if not self._in_article:
            return
        classes = (attrs_dict.get("class") or "").split()
        if tag == "div":
            self._div_depth += 1
            if "post-meta" in classes:
                self._in_meta = True
                self._meta_div_depth = self._div_depth
            return
        if self._in_meta and tag == "span":
            self._current_span = []
            return
        if tag == "table":
            self._table_rows = 0
            return
        if tag in ("th", "td"):
            self._in_cell = True
            if self._block is not None and tag == "th":
                self._block.header_row = True
            return
        if tag == "br":
            if self._block is not None:
                self._block.text.append("\n")
            return
        if tag == "code" and not self._in_pre:
            if self._block is not None:
                self._block.text.append("`")
            return
        if tag == "pre":
            self._in_pre = True
        if tag in BLOCK_TAGS:
            self._flush_block()
            self._block = _Block(tag)
            if tag == "hr":
                self.lines.append("---")
                self._block = None

    def handle_endtag(self, tag: str) -> None:
        if self._skip_depth:
            self._skip_depth -= 1
            return
        if tag == "article":
            self._flush_block()
            self._in_article = False
            return
        if not self._in_article:
            return
        if tag == "div":
            if self._in_meta and self._div_depth == self._meta_div_depth:
                self._in_meta = False
                spans = [s for s in self._meta_spans if s and s != "·"]
                if spans:
                    self.date = spans[0]
                if len(spans) > 1:
                    self.read_time = spans[1]
            self._div_depth -= 1
            return
        if tag == "span" and self._current_span is not None:
            self._meta_spans.append("".join(self._current_span).strip())
            self._current_span = None
            return
        if tag in ("th", "td"):
            self._in_cell = False
            if self._block is not None:
                self._block.cells.append(_collapse("".join(self._block.text)))
                self._block.text = []
            return
        if tag == "code" and not self._in_pre:
            if self._block is not None:
                self._block.text.append("`")
            return
        if tag == "pre":
            self._in_pre = False
        if tag in BLOCK_TAGS:
            self._flush_block()

    def handle_data(self, data: str) -> None:
        if self._skip_depth or not self._in_article:
            return
        if self._current_span is not None:
            self._current_span.append(data)
            return
        if self._block is not None:
            self._block.text.append(data)

    # -- emitting -----------------------------------------------------------
    def _flush_block(self) -> None:
        block = self._block
        self._block = None
        if block is None:
            return
        if block.tag == "tr":
            if not block.cells:
                return
            self.lines.append("| " + " | ".join(block.cells) + " |")
            if block.header_row:
                self.lines.append("|" + "---|" * len(block.cells))
            return
        if block.tag == "pre":
            code = "".join(block.text).strip("\n")
            self.lines.append("```\n" + code + "\n```")
            return
        text = _collapse("".join(block.text))
        if not text:
            return
        if block.tag == "h1":
            if not self.title:
                self.title = text
            return
        if block.tag in HEADING_PREFIX:
            self.lines.append(HEADING_PREFIX[block.tag] + text)
        elif block.tag == "li":
            self.lines.append("- " + text)
        elif block.tag == "blockquote":
            self.lines.append("> " + text)
        else:
            self.lines.append(text)


def _collapse(text: str) -> str:
    return re.sub(r"[ \t\r\n]+", " ", text).strip()


def _join_lines(lines: list[str]) -> str:
    """Blank line between blocks, except consecutive list items and table rows."""
    out: list[str] = []
    prev = ""
    for line in lines:
        if out:
            same_run = (line.startswith("- ") and prev.startswith("- ")) or (
                line.startswith("|") and prev.startswith("|")
            )
            out.append("" if not same_run else None)  # type: ignore[arg-type]
        out.append(line)
        prev = line
    return "\n".join(line for line in out if line is not None)


def post_from_html(html: str) -> PostDocument:
    parser = _ArticleParser()
    parser.feed(html)
    parser.close()
    return PostDocument(
        title=parser.title,
        date=parser.date,
        read_time=parser.read_time,
        body=_join_lines(parser.lines),
    )
