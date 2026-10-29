"""Render README.md the way GitHub does, using local images, into preview.html.

    python scripts/preview.py          # writes preview.html
    python scripts/preview.py --open   # and opens it in the browser

Uses GitHub's own markdown API through the `gh` CLI, so tables, <details> and
image sizing match the real profile page.
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

html = subprocess.run(
    ["gh", "api", "markdown", "-f", "mode=gfm", "-f", "context=frimpongopoku/frimpongopoku",
     "-F", f"text=@{ROOT / 'README.md'}"],
    capture_output=True, text=True, check=True).stdout

# GitHub rewrites relative image paths to the pushed copies; point them back at local files.
html = re.sub(r'https://github\.com/frimpongopoku/frimpongopoku/(?:raw|blob)/[^/]+/(assets/[^"?]+)(?:\?raw=true)?', r"\1", html)
html = re.sub(r'https://raw\.githubusercontent\.com/frimpongopoku/frimpongopoku/[^/]+/(assets/[^"?]+)', r"\1", html)
html = re.sub(r'<a [^>]*href="(assets/[^"]+)"[^>]*>(<img [^>]*>)</a>', r"\2", html)

theme = "dark" if "--light" not in sys.argv else "light"
page = f"""<!doctype html><html><head><meta charset="utf-8"><title>Profile preview</title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/github-markdown-css/5.5.1/github-markdown-{theme}.min.css">
<style>body{{background:{'#0d1117' if theme == 'dark' else '#fff'};margin:0}}
.wrap{{max-width:830px;margin:32px auto;padding:24px;border:1px solid {'#30363d' if theme == 'dark' else '#d0d7de'};border-radius:6px}}</style>
</head><body><div class="wrap markdown-body">{html}</div></body></html>"""
(ROOT / "preview.html").write_text(page)
print("wrote preview.html")
if "--open" in sys.argv:
    subprocess.run(["open", str(ROOT / "preview.html")])
