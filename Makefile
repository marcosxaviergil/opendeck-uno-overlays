# UNO Overlays for OpenDeck — development tasks. The plugin itself needs only Python 3.10+.
PYTHON ?= python3
PLUGIN := plugin/dev.br.consciencia.opendeck.uno-overlays.sdPlugin
PY_SOURCES := $(PLUGIN)/main.py $(PLUGIN)/uno scripts tests

.PHONY: check tools lint test test-pi build manual clean

# Fast checks first: missing tools and lint fail in seconds, before the long tests and the manual.
check: tools lint test test-pi manual

# Everything the checks, the build and the manual need, here and in the CI image (node:22-bookworm-slim
# plus the apt-get list of .forgejo/workflows/build.yaml). Lists what is missing instead of failing later.
tools:
	@missing=""; \
	for c in $(PYTHON) node git sh fc-list; do command -v $$c >/dev/null 2>&1 || missing="$$missing $$c"; done; \
	$(PYTHON) -c 'import pyflakes' 2>/dev/null || missing="$$missing pyflakes(python3-pyflakes)"; \
	$(PYTHON) -c 'import weasyprint' 2>/dev/null || missing="$$missing weasyprint"; \
	command -v fc-list >/dev/null 2>&1 && { fc-list ':lang=ja' family | grep -q . || missing="$$missing fonts-noto-cjk"; }; \
	if [ -n "$$missing" ]; then echo "Faltam comandos/pacotes:$$missing"; exit 1; fi; echo "tools: OK"

lint:
	$(PYTHON) -m pyflakes $(PY_SOURCES)
	@if command -v ruff >/dev/null 2>&1; then ruff check . && ruff format --check .; \
	else echo "lint: ruff not installed, style rules in pyproject.toml NOT checked"; fi
	@for f in $(PLUGIN)/pi/js/*.js; do node --check "$$f" || exit 1; done
	sh -n $(PLUGIN)/launch.sh
	$(PYTHON) -B scripts/build_i18n.py --check

test:
	$(PYTHON) -B -m unittest discover -s tests -v

test-pi:
	node --test tests/pi/inspector.test.cjs

build:
	$(PYTHON) -B scripts/build.py

manual:
	$(PYTHON) -B scripts/build_manual.py

clean:
	rm -rf dist
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
