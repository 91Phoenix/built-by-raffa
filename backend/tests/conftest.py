import textwrap
from pathlib import Path

import pytest

POST_HTML = textwrap.dedent(
    """\
    <!DOCTYPE html>
    <html lang="en" data-theme="light">
    <head>
      <meta charset="UTF-8">
      <title>The Bugs I Couldn't See: Rewriting a Scraper &mdash; Bradicode</title>
      <link rel="stylesheet" href="../style.css">
    </head>
    <body>
      <nav id="nav-slot"></nav>
      <main>
        <a href="index.html" class="back-link">&larr; All posts</a>
        <article>
          <div class="post-header">
            <h1>The Bugs I Couldn't See: Rewriting a Scraper</h1>
            <div class="post-meta">
              <span>April 2026</span>
              <span class="dot">&middot;</span>
              <span>16 min read</span>
            </div>
          </div>
          <p>My first scraper <em>worked</em>. That was the problem &mdash; it filled the DB with <code>848</code> recipes.</p>
          <hr>
          <h2>Part 1 &mdash; The Two Scripts</h2>
          <p>Each used <code>requests.Session()</code>.</p>
          <figure>
            <div class="diagram-scroll">
              <svg viewBox="0 0 10 10" role="img" aria-label="Layers diagram"><text x="1" y="1">ignored svg text</text></svg>
            </div>
            <figcaption>Layers you write yourself.</figcaption>
          </figure>
          <h3>Why not httpx?</h3>
          <ul>
            <li>Async HTTP</li>
            <li>Same selector library</li>
          </ul>
          <pre><code>scrapy crawl recipes
</code></pre>
          <table>
            <tr><th>Field</th><th>Before</th></tr>
            <tr><td>name</td><td>lost strong</td></tr>
          </table>
        </article>
      </main>
      <footer id="footer-slot"></footer>
      <script src="../js/site.js"></script>
    </body>
    </html>
    """
)

INDEX_HTML = textwrap.dedent(
    """\
    <!DOCTYPE html>
    <html lang="en">
    <body>
      <main>
        <div class="section-label">2026</div>
        <a href="crawling-with-scrapy.html" class="post-card">
          <div class="post-date">April 2026</div>
          <div class="post-title">The Bugs I Couldn't See: Rewriting a Scraper</div>
          <div class="post-excerpt">A scraper that <em>quietly</em> returns almost the right data &mdash; and the audit.</div>
          <span class="post-tag">python</span>
          <span class="post-tag">scrapy</span>
        </a>
        <a href="second-post.html" class="post-card">
          <div class="post-date">September 2026</div>
          <div class="post-title">Second Post</div>
          <div class="post-excerpt">About agents.</div>
          <span class="post-tag">ai agents</span>
        </a>
      </main>
    </body>
    </html>
    """
)

SECOND_POST_HTML = textwrap.dedent(
    """\
    <html><body><main><article>
      <div class="post-header"><h1>Second Post</h1>
        <div class="post-meta"><span>September 2026</span><span class="dot">&middot;</span><span>3 min read</span></div>
      </div>
      <p>Agents summarize Kubernetes builds with Kafka spans.</p>
    </article></main></body></html>
    """
)


@pytest.fixture
def site_dir(tmp_path: Path) -> Path:
    posts = tmp_path / "posts"
    posts.mkdir()
    (posts / "index.html").write_text(INDEX_HTML)
    (posts / "crawling-with-scrapy.html").write_text(POST_HTML)
    (posts / "second-post.html").write_text(SECOND_POST_HTML)
    return tmp_path
