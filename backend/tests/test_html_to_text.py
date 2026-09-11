from blog_api.html_to_text import post_from_html
from tests.conftest import POST_HTML


def test_extracts_title_date_and_read_time():
    post = post_from_html(POST_HTML)
    assert post.title == "The Bugs I Couldn't See: Rewriting a Scraper"
    assert post.date == "April 2026"
    assert post.read_time == "16 min read"


def test_body_is_markdown_like_with_headings_and_inline_code():
    post = post_from_html(POST_HTML)
    assert "## Part 1 — The Two Scripts" in post.body
    assert "### Why not httpx?" in post.body
    assert "`requests.Session()`" in post.body
    assert (
        "My first scraper worked. That was the problem — it filled the DB with `848` recipes."
        in post.body
    )


def test_body_skips_chrome_svg_but_keeps_figcaption():
    post = post_from_html(POST_HTML)
    assert "All posts" not in post.body
    assert "ignored svg text" not in post.body
    assert "Layers you write yourself." in post.body


def test_lists_code_blocks_and_tables():
    post = post_from_html(POST_HTML)
    assert "- Async HTTP\n- Same selector library" in post.body
    assert "```\nscrapy crawl recipes\n```" in post.body
    assert "| Field | Before |" in post.body
    assert "| name | lost strong |" in post.body


def test_body_has_no_runs_of_blank_lines():
    post = post_from_html(POST_HTML)
    assert "\n\n\n" not in post.body
    assert not post.body.startswith("\n")
