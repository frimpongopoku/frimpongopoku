"""Build the profile README and its SVG images from profile.yml.

    python scripts/build.py            # fetch live stats, write README.md + assets/
    python scripts/build.py --offline  # reuse the last stats in assets/stats.json

Fonts are subset per SVG and embedded as base64, because GitHub serves README
images in a sandbox that can't load external fonts.
"""
import base64
import io
import json
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from xml.sax.saxutils import escape

import yaml
from fontTools import subset
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
CARDS = ASSETS / "cards"

# palette (matches the mockup)
BG, PANEL, PANEL_PRO, BORDER = "#0d1117", "#11161d", "#0f1712", "#30363d"
FG, SOFT, MUTED = "#e6edf3", "#c2cbd4", "#8b949e"
TERM, TERM_SIDE, TERM_LINE, TERM_TEXT, TERM_DIM = "#0b0f0c", "#111712", "#1f2a20", "#9aa79c", "#5c6a5e"
GOLD, CLAY, LEAF, BLUE = "#f2b632", "#d4603a", "#3fa66b", "#6aa9ff"

STATUS = {"live": ("available", LEAF), "wip": ("in progress", GOLD), "work": ("day job", MUTED)}
AGENT_COLOR = {"me": GOLD, "run": LEAF, "done": BLUE, "wait": CLAY}
LANES = {
    "studio": ("Biibisoft studio", "Products I own and build independently."),
    "pro": ("Professional · MassEnergize", "Work done as part of my role."),
}


# ---------- fonts ----------

class Font:
    def __init__(self, family, file):
        self.family, self.path = family, ROOT / "fonts" / file
        self.tt = TTFont(self.path)
        self.cmap = self.tt.getBestCmap()
        self.hmtx = self.tt["hmtx"]
        self.upm = self.tt["head"].unitsPerEm

    def width(self, text, size):
        adv = 0
        for ch in text:
            glyph = self.cmap.get(ord(ch)) or ".notdef"
            adv += self.hmtx[glyph][0]
        return adv * size / self.upm

    def embed(self, chars):
        opts = subset.Options()
        opts.flavor = "woff2"
        opts.layout_features = ["*"]
        font = TTFont(self.path)
        sub = subset.Subsetter(opts)
        sub.populate(text="".join(sorted(chars)) + " ")
        sub.subset(font)
        buf = io.BytesIO()
        font.flavor = "woff2"
        font.save(buf)
        data = base64.b64encode(buf.getvalue()).decode()
        return f"@font-face{{font-family:'{self.family}';src:url(data:font/woff2;base64,{data}) format('woff2')}}"


MONO = Font("M4", "mono-400.ttf")
MONO_B = Font("M6", "mono-600.ttf")
DISPLAY = Font("D8", "display-800.ttf")
DISPLAY_M = Font("D5", "display-500.ttf")


class Svg:
    """Collects SVG elements and the characters each font draws, then embeds just those glyphs."""

    def __init__(self, w, h, title):
        self.w, self.h, self.title = w, h, title
        self.parts, self.defs, self.used = [], [], {}

    def add(self, s):
        self.parts.append(s)

    def text(self, x, y, s, font, size, fill, anchor="start", extra=""):
        self.used.setdefault(font, set()).update(s)
        a = f' text-anchor="{anchor}"' if anchor != "start" else ""
        return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{font.family}" font-size="{size}" '
                f'fill="{fill}"{a}{extra}>{escape(s)}</text>')

    def render(self):
        faces = "".join(f.embed(chars) for f, chars in self.used.items())
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
                f'viewBox="0 0 {self.w} {self.h}" role="img"><title>{escape(self.title)}</title>'
                f'<style>{faces}text{{white-space:pre}}</style><defs>{"".join(self.defs)}</defs>'
                + "".join(self.parts) + "</svg>")


def wrap(text, font, size, max_w):
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if font.width(trial, size) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def fit(text, font, size, max_w):
    if font.width(text, size) <= max_w:
        return text
    while text and font.width(text + "…", size) > max_w:
        text = text[:-1]
    return text.rstrip() + "…"


def steps(w, n):
    return ";".join(f"{w * i / n:.1f}" for i in range(n + 1))


# ---------- hero ----------

def hero(cfg):
    h = cfg["hero"]
    W, TOP, SIDE = 900, 36, 210
    x0, max_w = SIDE + 30, W - SIDE - 30 - 28
    svg = Svg(W, 0, f"{h['name']}: {h['thesis']}")
    body = []

    # main pane, laid out top to bottom so the height follows the content
    y = TOP + 36
    clip_id = 0

    def prompt(y, cmd, begin, reveal=None):
        nonlocal clip_id
        out = []
        out.append(svg.text(x0, y, "frimpong", MONO, 13, LEAF))
        px = x0 + MONO.width("frimpong ", 13)
        out.append(svg.text(px, y, "~/accra $", MONO, 13, GOLD))
        cx = px + MONO.width("~/accra $ ", 13)
        if cmd:
            clip_id += 1
            cw = MONO.width(cmd, 13)
            svg.defs.append(
                f'<clipPath id="c{clip_id}"><rect x="{cx:.1f}" y="{y - 14:.1f}" width="0" height="20">'
                f'<animate attributeName="width" values="{steps(cw, len(cmd))}" calcMode="discrete" '
                f'begin="{begin}s" dur="{len(cmd) * 0.09:.2f}s" fill="freeze"/></rect></clipPath>')
            out.append(f'<g clip-path="url(#c{clip_id})">{svg.text(cx, y, cmd, MONO, 13, FG)}</g>')
        else:
            out.append(f'<rect x="{cx:.1f}" y="{y - 12:.1f}" width="8" height="16" fill="{GOLD}">'
                       f'<animate attributeName="opacity" values="1;0" dur="1s" calcMode="discrete" repeatCount="indefinite"/></rect>')
        return group(out, reveal)

    def group(items, reveal):
        if reveal is None:
            return "".join(items)
        return (f'<g opacity="0"><set attributeName="opacity" to="1" begin="{reveal}s" fill="freeze"/>'
                + "".join(items) + "</g>")

    body.append(prompt(y, "whoami", 0.3))

    size = 44
    while DISPLAY.width(h["name"], size) > max_w:
        size -= 1
    y += 22 + size * 0.85
    name_y = y
    y += 36
    thesis_y = y
    body.append(group([svg.text(x0, name_y, h["name"], DISPLAY, size, FG, extra=' letter-spacing="-0.5"'),
                       svg.text(x0, thesis_y, h["thesis"], DISPLAY_M, 22, GOLD)], 1.1))

    y += 40
    body.append(prompt(y, "cat how.txt", 1.7, reveal=1.6))
    y += 26
    lines = wrap(h["intro"], MONO, 13, max_w)
    body.append(group([svg.text(x0, y + i * 21, ln, MONO, 13, TERM_TEXT) for i, ln in enumerate(lines)], 2.9))
    y += len(lines) * 21 + 14
    body.append(prompt(y, None, 0, reveal=3.3))

    # sidebar
    agents = h["agents"]
    side_h = TOP + 40 + len(agents) * 28 + 16
    H = int(max(y + 30, side_h))
    svg.h = H
    side = [f'<rect x="0" y="{TOP}" width="{SIDE}" height="{H - TOP}" fill="{TERM_SIDE}"/>',
            f'<line x1="{SIDE}" y1="{TOP}" x2="{SIDE}" y2="{H}" stroke="{TERM_LINE}"/>']
    running = sum(a["state"] == "run" for a in agents)
    side.append(svg.text(18, TOP + 24, "AGENTS", MONO, 10, TERM_DIM, extra=' letter-spacing="1.2"'))
    side.append(svg.text(SIDE - 14, TOP + 24, f"{running} running", MONO_B, 10, LEAF, anchor="end"))
    for i, a in enumerate(agents):
        ry = TOP + 38 + i * 28
        if a["state"] == "me":
            side.append(f'<rect x="8" y="{ry}" width="{SIDE - 16}" height="24" rx="5" fill="#1c241d"/>')
        dot = f'<circle cx="22" cy="{ry + 12}" r="3.5" fill="{AGENT_COLOR[a["state"]]}">'
        if a["state"] == "run":
            dot += f'<animate attributeName="opacity" values="1;0.25;1" dur="1.4s" begin="{i * 0.3:.1f}s" repeatCount="indefinite"/>'
        side.append(dot + "</circle>")
        tag_w = MONO.width(a["tag"], 10)
        label = fit(a["label"], MONO, 12, SIDE - 16 - 34 - tag_w - 10)
        side.append(svg.text(34, ry + 16, label, MONO, 12, FG if a["state"] == "me" else TERM_TEXT))
        side.append(svg.text(SIDE - 16, ry + 16, a["tag"], MONO, 10, TERM_DIM, anchor="end"))

    svg.defs.append(f'<clipPath id="win"><rect width="{W}" height="{H}" rx="12"/></clipPath>')
    chrome = [f'<rect width="{W}" height="{H}" fill="{TERM}"/>',
              f'<line x1="0" y1="{TOP}" x2="{W}" y2="{TOP}" stroke="{TERM_LINE}"/>']
    for i, c in enumerate(["#ff5f57", "#febc2e", "#28c840"]):
        chrome.append(f'<circle cx="{18 + i * 18}" cy="18" r="5.5" fill="{c}"/>')
    chrome.append(svg.text(80, 22, "termite — ~/accra", MONO, 11, "#6c7a6e"))

    svg.add(f'<g clip-path="url(#win)">{"".join(chrome + side + body)}</g>')
    svg.add(f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="12" fill="none" stroke="{TERM_LINE}"/>')
    return svg.render()


# ---------- project cards ----------

def card(p):
    W, H, PAD = 436, 164, 20
    pro = p["lane"] == "pro"
    svg = Svg(W, H, f"{p['name']}: {p['blurb']}")
    svg.add(f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="10" fill="{PANEL_PRO if pro else PANEL}" stroke="{BORDER}"/>')

    label, color = STATUS[p["status"]]
    pw = MONO.width(label, 10.5) + 16
    svg.add(f'<rect x="{W - PAD - pw:.1f}" y="24" width="{pw:.1f}" height="20" rx="10" fill="none" stroke="{color}"/>')
    svg.add(svg.text(W - PAD - pw / 2, 38, label, MONO, 10.5, color, anchor="middle"))

    size = 21
    avail = W - PAD * 2 - pw - 12
    while DISPLAY.width(p["name"], size) > avail and size > 15:
        size -= 1
    svg.add(svg.text(PAD, 42, fit(p["name"], DISPLAY, size, avail), DISPLAY, size, FG, extra=' letter-spacing="-0.2"'))

    y = 72
    if p.get("shipped_in"):
        svg.add(svg.text(PAD, 64, f"shipped in {p['shipped_in']}", MONO_B, 11, GOLD))
        y = 88
    max_lines = 3 if y == 72 else 2
    lines = wrap(p["blurb"], DISPLAY_M, 14.5, W - PAD * 2)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = fit(lines[-1] + " …", DISPLAY_M, 14.5, W - PAD * 2 - 10)
    for i, ln in enumerate(lines):
        svg.add(svg.text(PAD, y + i * 21, ln, DISPLAY_M, 14.5, SOFT))

    x = PAD
    for tag in p.get("tags", []):
        name, col = tag[0], ("#" + tag[1]) if len(tag) > 1 else MUTED
        svg.add(f'<circle cx="{x + 4.5}" cy="{H - 24}" r="4.5" fill="{col}"/>')
        svg.add(svg.text(x + 14, H - 20, name, MONO, 11.5, MUTED))
        x += 14 + MONO.width(name, 11.5) + 16
    return svg.render()


# ---------- stats + footer ----------

def fetch_stats(user, offline):
    cache = ASSETS / "stats.json"
    old = json.loads(cache.read_text()) if cache.exists() else {}
    if offline:
        return old or {"repos": 0, "languages": 0}
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        try:
            token = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, check=True).stdout.strip()
        except Exception:
            token = None

    def get(url):
        req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "profile-build"})
        if token:
            req.add_header("Authorization", f"Bearer {token}")
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.load(r)

    try:
        langs, page = set(), 1
        while True:
            batch = get(f"https://api.github.com/users/{user}/repos?type=owner&per_page=100&page={page}")
            langs.update(r["language"] for r in batch if r["language"] and not r["fork"])
            if len(batch) < 100:
                break
            page += 1
        stats = {"repos": get(f"https://api.github.com/users/{user}")["public_repos"], "languages": len(langs)}
        cache.write_text(json.dumps(stats, indent=2) + "\n")
        return stats
    except Exception as e:
        print(f"warning: couldn't fetch stats ({e}); using cached values", file=sys.stderr)
        return old or {"repos": 0, "languages": 0}


def stats_svg(m, stats):
    cells = [(str(m["platforms"]), "platforms", m["platforms_note"]),
             (str(stats["languages"]), "languages", "across public repos"),
             (str(stats["repos"]), "public repos", "and counting"),
             ("2017", "shipping since", "on GitHub")]
    W, H = 900, 104
    svg = Svg(W, H, ", ".join(f"{v} {l}" for v, l, _ in cells))
    svg.add(f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="10" fill="{PANEL}" stroke="{BORDER}"/>')
    cw = W / len(cells)
    for i, (v, l, sub) in enumerate(cells):
        x = i * cw
        if i:
            svg.add(f'<line x1="{x:.1f}" y1="0" x2="{x:.1f}" y2="{H}" stroke="{BORDER}"/>')
        svg.add(svg.text(x + 20, 44, v, DISPLAY, 30, FG))
        svg.add(svg.text(x + 20, 68, fit(l, MONO_B, 11.5, cw - 36), MONO_B, 11.5, SOFT))
        svg.add(svg.text(x + 20, 86, fit(sub, MONO, 11, cw - 36), MONO, 11, MUTED))
    return svg.render()


def kente_svg():
    W, H = 900, 10
    bands = [(GOLD, 22), (BG, 3), (CLAY, 12), (BG, 3), (LEAF, 12), (BG, 3), ("#1a1a1a", 7), (BG, 3)]
    rects, x = [], 0
    while x < W:
        for col, bw in bands:
            rects.append(f'<rect x="{x}" width="{bw}" height="{H}" fill="{col}"/>')
            x += bw
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
            f'<defs><clipPath id="k"><rect width="{W}" height="{H}" rx="3"/></clipPath></defs>'
            f'<g clip-path="url(#k)">{"".join(rects)}</g></svg>')


# ---------- markdown ----------

def badge(b):
    enc = lambda s: urllib.parse.quote(s.replace("-", "--").replace("_", "__"))
    img = (f'<img src="https://img.shields.io/badge/{enc(b["label"])}-{enc(b["value"])}-{b["color"]}'
           f'?style=flat-square&labelColor=2b2f2b" alt="{escape(b["label"])}: {escape(b["value"])}">')
    return f'<a href="{b["url"]}">{img}</a>' if b.get("url") else img


def multiplier_md(m):
    own = "<br>\n".join(escape(x) for x in m["own"])
    fast = "<br>\n".join(escape(x) for x in m["speeds_up"])
    loop = " → ".join(f"<code>{escape(s)}</code>" for s in m["loop"])
    return (f'{m["lede"]}\n\n<table>\n<tr><th align="left" width="50%">What I own</th>'
            f'<th align="left" width="50%">What AI speeds up</th></tr>\n'
            f'<tr><td valign="top">\n{own}\n</td><td valign="top">\n{fast}\n</td></tr>\n</table>\n\n'
            f'**How a project runs:** {loop}<br>\n**Toolkit:** {" · ".join(m["toolkit"])}')


def work_md(projects):
    out = []
    for lane, (title, sub) in LANES.items():
        picked = [p for p in projects if p["lane"] == lane and p.get("featured")]
        if not picked:
            continue
        imgs = []
        for p in picked:
            img = f'<img src="assets/cards/{p["id"]}.svg" width="49%" alt="{escape(p["name"])}: {escape(p["blurb"])}">'
            imgs.append(f'<a href="{p["url"]}">{img}</a>' if p.get("url") else img)
        out.append(f"### {title}\n<sub>{sub}</sub>\n\n<p>\n" + "\n".join(imgs) + "\n</p>")
    return "\n\n".join(out)


def stack_md(stack):
    rows = "\n".join(f'| **{s["layer"]}** | {" · ".join(s["items"])} |' for s in stack)
    return "| Layer | Tools |\n| :-- | :-- |\n" + rows


def vault_md(projects):
    picked = [p for p in projects if p["lane"] == "vault" and p.get("featured")]
    if not picked:
        return ""
    def title(p):
        return f"[{p['name']}]({p['url']})" if p.get("url") else p["name"]
    items = "\n".join(f'- **{title(p)}**: {p["blurb"]} `{p["stack"]}`' for p in picked)
    return f"<details open>\n<summary><b>From the vault</b>: older things I'm still proud of</summary>\n\n{items}\n\n</details>"


def main():
    offline = "--offline" in sys.argv
    cfg = yaml.safe_load((ROOT / "profile.yml").read_text())
    ids = [p["id"] for p in cfg["projects"]]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        sys.exit(f"duplicate project ids in profile.yml: {', '.join(sorted(dupes))}")

    CARDS.mkdir(parents=True, exist_ok=True)
    for old in CARDS.glob("*.svg"):
        old.unlink()

    (ASSETS / "hero.svg").write_text(hero(cfg))
    for p in cfg["projects"]:
        if p.get("featured") and p["lane"] != "vault":
            (CARDS / f"{p['id']}.svg").write_text(card(p))
    stats = fetch_stats(cfg["user"], offline)
    (ASSETS / "stats.svg").write_text(stats_svg(cfg["multiplier"], stats))
    (ASSETS / "kente.svg").write_text(kente_svg())

    h = cfg["hero"]
    values = {
        "hero_alt": escape(f'{h["name"]}. {h["thesis"]} {h["intro"]}'),
        "badges": "\n".join(badge(b) for b in cfg["badges"]),
        "multiplier": multiplier_md(cfg["multiplier"]),
        "stats_alt": escape(f'{cfg["multiplier"]["platforms"]} platforms, {stats["languages"]} languages, {stats["repos"]} public repos, shipping since 2017'),
        "work": work_md(cfg["projects"]),
        "stack": stack_md(cfg["stack"]),
        "vault": vault_md(cfg["projects"]),
        "footer": escape(cfg["footer"]),
    }
    tpl = (ROOT / "README.template.md").read_text()
    missing = set(re.findall(r"{{(\w+)}}", tpl)) - values.keys()
    if missing:
        sys.exit(f"README.template.md uses unknown placeholders: {', '.join(sorted(missing))}")
    readme = re.sub(r"{{(\w+)}}", lambda m: values[m.group(1)], tpl)
    (ROOT / "README.md").write_text(readme)
    n = sum(1 for p in cfg["projects"] if p.get("featured") and p["lane"] != "vault")
    print(f"built README.md, hero, {n} cards, stats ({stats['repos']} repos, {stats['languages']} languages)")


if __name__ == "__main__":
    main()
