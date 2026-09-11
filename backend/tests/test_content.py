import pytest

from blog_api.build_content import build_content
from blog_api.content import ContentRepository


@pytest.fixture
def repo(site_dir, tmp_path):
    out = tmp_path / "content"
    build_content(site_dir, out, site_url="https://bradicode.dev")
    return ContentRepository(out)


def test_list_posts_returns_index_entries_without_bodies(repo):
    posts = repo.list_posts()
    assert [p["slug"] for p in posts] == ["crawling-with-scrapy", "second-post"]
    assert "body" not in posts[0]
    assert posts[0]["url"].endswith("/posts/crawling-with-scrapy.html")


def test_get_post_returns_metadata_and_markdown_body(repo):
    post = repo.get_post("crawling-with-scrapy")
    assert post["title"] == "The Bugs I Couldn't See: Rewriting a Scraper"
    assert post["body"].startswith("# The Bugs I Couldn't See")
    assert "## Part 1" in post["body"]


def test_get_post_unknown_slug_is_none_and_rejects_path_tricks(repo):
    assert repo.get_post("nope") is None
    assert repo.get_post("../index") is None


def test_search_ranks_by_term_hits_and_returns_snippets(repo):
    hits = repo.search("kubernetes kafka")
    assert hits[0]["slug"] == "second-post"
    assert "Kafka" in hits[0]["snippet"]
    assert all(h["score"] > 0 for h in hits)


def test_search_matches_title_and_tags_too(repo):
    hits = repo.search("scrapy")
    assert hits[0]["slug"] == "crawling-with-scrapy"


def test_search_no_hits_is_empty(repo):
    assert repo.search("zebra quantum") == []
