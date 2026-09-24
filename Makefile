.PHONY: help setup watch dev render build docker-build docker-watch clean

VENV := .venv
ifeq ($(OS),Windows_NT)
  PY := $(VENV)/Scripts/python.exe
else
  PY := $(VENV)/bin/python
endif
IMAGE := archforge

help:
	@echo "ArchForge - architecture diagrams as code"
	@echo ""
	@echo "  Local (needs Python 3.10+ and Graphviz):"
	@echo "    make setup         Create .venv and install dependencies"
	@echo "    make watch         Live-render diagrams on save"
	@echo "    make dev           Live-render + site preview at http://127.0.0.1:8000"
	@echo "    make render        Render all diagrams once"
	@echo "    make build         Build the static site into public/"
	@echo ""
	@echo "  Docker (needs only Docker):"
	@echo "    make docker-watch  Live-render + site preview at http://localhost:8000"
	@echo ""
	@echo "    make clean         Remove generated PNGs, public/ and caches"

$(PY):
	python3 -m venv $(VENV) || python -m venv $(VENV)
	$(PY) -m pip install --upgrade pip -q

setup: $(PY)
	$(PY) -m pip install -r requirements.txt -q
	@command -v dot >/dev/null 2>&1 || echo "\n⚠  Graphviz 'dot' not found. Install it (brew install graphviz / apt install graphviz / winget install graphviz) or use 'make docker-watch'."
	@echo "✔ Setup complete. Run 'make dev'."

watch: $(PY)
	$(PY) watch.py

dev: $(PY)
	$(PY) watch.py --serve

render: $(PY)
	$(PY) watch.py --once

build: $(PY)
	$(PY) build.py

docker-build:
	docker build -t $(IMAGE) .

docker-watch: docker-build
	docker run --rm -it -p 8000:8000 -v "$(CURDIR):/data" $(IMAGE)

clean:
	rm -f docs/assets/*.png
	rm -rf public __pycache__ architecture/__pycache__
