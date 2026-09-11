PY := .venv/bin/python
SITE_URL ?= https://bradicode.com
BUILD := build
ZIP := $(BUILD)/blog_api.zip

.PHONY: venv content test lint live package clean

venv:
	uv venv --python 3.12 .venv
	uv pip install --python $(PY) -e ".[dev]"

content:
	$(PY) -m blog_api.build_content .. blog_api/content --site-url $(SITE_URL)

test:
	$(PY) -m pytest -q -m "not live"

lint:
	$(PY) -m ruff check .
	$(PY) -m ruff format --check .

# Real DeepSeek calls. Reads backend/.env (never committed).
live: content
	set -a; . ./.env; set +a; $(PY) -m pytest -q -m live -s

# Lambda zip: arm64 manylinux wheels + our package + the built corpus.
package: content
	rm -rf $(BUILD)/package && mkdir -p $(BUILD)/package
	uv pip install --quiet --python $(PY) --target $(BUILD)/package \
		--python-platform aarch64-manylinux2014 --python-version 3.12 \
		--only-binary :all: "openai>=1.60,<3.0"
	cp -R blog_api $(BUILD)/package/blog_api
	find $(BUILD)/package -name "__pycache__" -type d -prune -exec rm -rf {} +
	rm -f $(ZIP)
	cd $(BUILD)/package && zip -qr ../blog_api.zip . -x "*.dist-info/RECORD"
	@ls -lh $(ZIP)

clean:
	rm -rf $(BUILD) blog_api/content .pytest_cache .ruff_cache
