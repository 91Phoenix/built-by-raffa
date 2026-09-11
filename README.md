# Bradicode

Personal blog (static HTML, deployed on Cloudflare Workers) plus a small
backend that serves the posts as an API and answers questions about them.

- `index.html`, `posts/`, `style.css`, `js/`: the site. `chat.html` is the
  ask-the-blog page; set the API URL in `js/config.js`.
- `backend/`: Python Lambda. Posts API and a DeepSeek tool-calling chat over
  the posts. Test-driven; see `backend/README.md`.
- `infra/`: Terraform for the Lambda and its public Function URL on AWS.
- `.github/workflows/backend.yml`: lint, test, package, validate, deploy.
