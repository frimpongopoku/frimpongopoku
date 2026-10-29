"""One-time: cut static font instances from the Google Fonts variable files.

Run only if you want different weights:  python scripts/make_fonts.py
"""
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "fonts" / "src"
OUT = ROOT / "fonts"

INSTANCES = {
    "mono-400.ttf": ("JetBrainsMono.ttf", {"wght": 400}),
    "mono-600.ttf": ("JetBrainsMono.ttf", {"wght": 600}),
    "display-800.ttf": ("Bricolage.ttf", {"wght": 800, "opsz": 48, "wdth": 100}),
    "display-500.ttf": ("Bricolage.ttf", {"wght": 500, "opsz": 24, "wdth": 100}),
}

for out, (src, axes) in INSTANCES.items():
    font = instantiateVariableFont(TTFont(SRC / src), axes)
    font.save(OUT / out)
    print("wrote", out)
