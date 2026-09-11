# Blog API

One Python Lambda serving the posts and a chat over them.

| Route | What |
|---|---|
| `GET /health` | post count |
| `GET /posts` | index: slug, title, date, tags, excerpt, url |
| `GET /posts/{slug}` | the post as markdown, plus its metadata |
| `POST /chat` | `{"message": "...", "history": [{"role","content"}]}` returns `{answer, sources, usage}` |

## How the chat works

No database and no embeddings. `make content` turns `posts/*.html` into
`blog_api/content/index.json` plus one markdown file per post, and that
folder ships inside the Lambda zip. The chat is a tool-calling loop
(`blog_api/agent.py`) over DeepSeek with three tools: `list_posts`,
`search_posts` (keyword scoring), `read_post`. Posts the model actually read
come back as `sources`, so the page can link them.

Guards: 1000-character messages, 10 turns of history, 800 output tokens,
at most 6 tool rounds, and the account-wide Lambda concurrency quota (10 on a new account; set `reserved_concurrency` in Terraform once the quota is raised).

When DeepSeek refuses (402 credit gone, 429 rate limit, 401 bad key, 5xx),
`/chat` answers 503 with a plain-language message the page shows as-is,
and the provider's own text goes to CloudWatch. Top up at
https://platform.deepseek.com and the chat resumes; nothing to redeploy.

## Develop

```sh
make venv        # uv venv + deps
make content     # build the corpus from ../posts
make test        # unit tests (no network)
make lint
cp .env.example .env && $EDITOR .env
make live        # two real DeepSeek calls
set -a; . ./.env; set +a; .venv/bin/python dev_server.py 8791
```

Then point `js/config.js` at `http://localhost:8791` and open the site with
any static server (`python3 -m http.server 8000` from the repo root).

## Ship

`make package` builds `build/blog_api.zip` (arm64 wheels). Terraform in
`../infra` uploads it.
