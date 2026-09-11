"""Hits the real DeepSeek API. Skipped unless DEEPSEEK_API_KEY is set.

Run: make live  (loads backend/.env)
"""

import os
from pathlib import Path

import pytest

from blog_api.agent import ChatAgent
from blog_api.config import DEEPSEEK_BASE_URL, chat_model
from blog_api.content import ContentRepository

pytestmark = pytest.mark.live

CONTENT = Path(__file__).resolve().parents[1] / "blog_api" / "content"


@pytest.fixture
def agent():
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        pytest.skip("DEEPSEEK_API_KEY not set")
    if not (CONTENT / "index.json").exists():
        pytest.skip("run `make content` first")
    from openai import OpenAI

    client = OpenAI(api_key=key, base_url=DEEPSEEK_BASE_URL, timeout=60.0)
    return ChatAgent(ContentRepository(CONTENT), client=client, model=chat_model())


def test_finds_scrapy_experience_and_cites_the_post(agent):
    result = agent.ask("Has Raffaele ever used Scrapy?")
    print("\nANSWER:", result.answer, "\nSOURCES:", result.sources, "\nUSAGE:", result.usage)
    assert "scrapy" in result.answer.lower()
    assert any(s["slug"] == "crawling-with-scrapy" for s in result.sources)


def test_admits_when_posts_do_not_cover_a_topic(agent):
    result = agent.ask("Has Raffaele written about COBOL mainframes?")
    print("\nANSWER:", result.answer, "\nSOURCES:", result.sources, "\nUSAGE:", result.usage)
    assert "cobol" in result.answer.lower()
    assert result.answer.lower().count("cobol") >= 1
