import json

from blog_api.build_content import build_content, read_cards


def test_read_cards_collects_slug_date_title_excerpt_tags(site_dir):
    cards = read_cards(site_dir / "posts" / "index.html")
    assert [c.slug for c in cards] == ["crawling-with-scrapy", "second-post"]
    first = cards[0]
    assert first.date == "April 2026"
    assert first.title == "The Bugs I Couldn't See: Rewriting a Scraper"
    assert first.excerpt == "A scraper that quietly returns almost the right data — and the audit."
    assert first.tags == ["python", "scrapy"]


def test_build_content_writes_index_and_one_markdown_per_post(site_dir, tmp_path):
    out = tmp_path / "content"
    build_content(site_dir, out, site_url="https://bradicode.com")

    index = json.loads((out / "index.json").read_text())
    assert [p["slug"] for p in index["posts"]] == ["crawling-with-scrapy", "second-post"]
    first = index["posts"][0]
    assert first["url"] == "https://bradicode.com/posts/crawling-with-scrapy.html"
    assert first["tags"] == ["python", "scrapy"]
    assert first["read_time"] == "16 min read"

    md = (out / "posts" / "crawling-with-scrapy.md").read_text()
    assert md.startswith("# The Bugs I Couldn't See: Rewriting a Scraper\n")
    assert "## Part 1 — The Two Scripts" in md


def test_build_content_fails_when_a_card_has_no_post_file(site_dir, tmp_path):
    (site_dir / "posts" / "second-post.html").unlink()
    try:
        build_content(site_dir, tmp_path / "content", site_url="https://x")
    except FileNotFoundError as e:
        assert "second-post" in str(e)
    else:
        raise AssertionError("expected FileNotFoundError")
