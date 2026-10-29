# Profile README workflow:
#   make preview          build, then open a GitHub-accurate preview
#   make ship m="msg"     pull, build, commit and push (goes live)

PY := $(shell command -v uv >/dev/null 2>&1 && echo "uv run --quiet --with-requirements requirements.txt python" || echo python3)

.PHONY: build preview ship

build:
	$(PY) scripts/build.py

preview: build
	$(PY) scripts/preview.py --open

ship:
	git pull --rebase --autostash
	$(PY) scripts/build.py
	git add -A
	git diff --cached --quiet || git commit -m "$(or $(m),Update profile)"
	git push
