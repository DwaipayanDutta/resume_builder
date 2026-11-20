"""Generate Resume Studio brand assets (SVG) + a preview sheet.

usage: python -I make_brand.py <font_dir> <repo_root> <preview_dir>
"""
import sys
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

font_dir, repo, preview_dir = (Path(a) for a in sys.argv[1:4])

NAVY = "#0B1020"
NAVY_TEXT = "#0F172A"
VIOLET_LIGHT = "#A78BFA"
VIOLET_DARK = "#6D28D9"
TEAL = "#2DD4BF"
FOLD = "#DDD6FE"


def sparkle(cx, cy, a, w):
    """Four-point star centred on (cx, cy): arm length a, waist w."""
    return (f"M{cx},{cy - a} Q{cx + w},{cy - w} {cx + a},{cy} Q{cx + w},{cy + w} {cx},{cy + a} "
            f"Q{cx - w},{cy + w} {cx - a},{cy} Q{cx - w},{cy - w} {cx},{cy - a} Z")


# ---- icon geometry on a 64 x 64 grid --------------------------------------
DOC = "M14 4H36L48 16V54A6 6 0 0 1 42 60H14A6 6 0 0 1 8 54V10A6 6 0 0 1 14 4Z"
FOLD_PATH = "M36 4V12A4 4 0 0 0 40 16H48Z"
# R monogram whose leg continues into a verification check
R_CHECK = "M17 46V22H25A6 6 0 0 1 25 34H17M25 34L30 41L41 27"
SPARK = sparkle(50, 45, 9.5, 1.9)


def icon_group(p: str) -> tuple[str, str]:
    """(defs, body) for the icon, ids prefixed with p so several can share a page."""
    defs = f"""
    <linearGradient id="{p}g" x1="8" y1="4" x2="48" y2="60" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="{VIOLET_LIGHT}"/>
      <stop offset="1" stop-color="{VIOLET_DARK}"/>
    </linearGradient>
    <mask id="{p}m" maskUnits="userSpaceOnUse" x="0" y="0" width="64" height="64">
      <rect width="64" height="64" fill="#fff"/>
      <path d="{SPARK}" fill="#000" stroke="#000" stroke-width="3.6" stroke-linejoin="round"/>
    </mask>"""
    body = f"""
    <g mask="url(#{p}m)">
      <path d="{DOC}" fill="url(#{p}g)"/>
      <path d="{FOLD_PATH}" fill="{FOLD}" fill-opacity="0.9"/>
      <path d="{R_CHECK}" fill="none" stroke="#fff" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>
    </g>
    <path d="{SPARK}" fill="{TEAL}"/>"""
    return defs, body


def icon_svg(size=64, title=True) -> str:
    defs, body = icon_group("rs")
    t = '<title>Resume Studio</title>' if title else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="{size}" height="{size}" '
            f'role="img" aria-label="Resume Studio">{t}<defs>{defs}</defs>{body}\n</svg>\n')


# ---- wordmark: outlined Poppins SemiBold ------------------------------------
font = TTFont(font_dir / "Poppins-SemiBold.ttf")
glyphs = font.getGlyphSet()
cmap = font.getBestCmap()
hmtx = font["hmtx"]
upem = font["head"].unitsPerEm
cap = font["OS/2"].sCapHeight


def wordmark(text: str, cap_px: float, x0: float, baseline: float, tracking_em=0.06):
    s = cap_px / cap
    x = x0
    out = []
    for ch in text:
        gname = cmap[ord(ch)]
        adv = hmtx[gname][0]
        if ch != " ":
            pen = SVGPathPen(glyphs)
            glyphs[gname].draw(TransformPen(pen, (s, 0, 0, -s, x, baseline)))
            out.append(pen.getCommands())
        x += adv * s + tracking_em * upem * s
    width = x - x0 - tracking_em * upem * s
    return " ".join(out), width


def lockup_svg(text_color: str) -> str:
    defs, body = icon_group("rs")
    cap_px = 22
    path, w = wordmark("RESUME STUDIO", cap_px, 80, 32 + cap_px / 2)
    total_w = round(80 + w + 2)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {total_w} 64" width="{total_w}" height="64" '
            f'role="img" aria-label="Resume Studio"><title>Resume Studio</title><defs>{defs}</defs>{body}\n'
            f'  <path fill="{text_color}" d="{path}"/>\n</svg>\n')


def app_icon_svg() -> str:
    defs, body = icon_group("rs")
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" width="1024" height="1024" role="img" aria-label="Resume Studio">
  <title>Resume Studio</title>
  <defs>{defs}
    <radialGradient id="glow" cx="512" cy="470" r="520" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#4C1D95" stop-opacity="0.55"/>
      <stop offset="1" stop-color="{NAVY}" stop-opacity="0"/>
    </radialGradient>
  </defs>
  <rect width="1024" height="1024" fill="{NAVY}"/>
  <rect width="1024" height="1024" fill="url(#glow)"/>
  <g transform="translate(512 512) scale(10.2) translate(-33.5 -32)">{body}
  </g>
</svg>
"""


brand = repo / "assets" / "brand"
public = repo / "web" / "public"
(public / "brand").mkdir(parents=True, exist_ok=True)
brand.mkdir(parents=True, exist_ok=True)

files = {
    "resume-studio-icon.svg": icon_svg(),
    "resume-studio-logo-on-dark.svg": lockup_svg("#FFFFFF"),
    "resume-studio-logo-on-light.svg": lockup_svg(NAVY_TEXT),
    "resume-studio-app-icon.svg": app_icon_svg(),
}
for name, svg in files.items():
    (brand / name).write_text(svg, encoding="utf-8")
for name in ("resume-studio-icon.svg", "resume-studio-logo-on-dark.svg", "resume-studio-logo-on-light.svg"):
    (public / "brand" / name).write_text(files[name], encoding="utf-8")
(public / "favicon.svg").write_text(files["resume-studio-icon.svg"], encoding="utf-8")

# ---- preview sheet ----------------------------------------------------------
preview_dir.mkdir(parents=True, exist_ok=True)
icon = icon_svg()
sizes = "".join(f'<div class="cell"><img src="{brand.as_uri()}/resume-studio-icon.svg" width="{s}" height="{s}"><span>{s}px</span></div>'
                for s in (256, 64, 32, 16))
(preview_dir / "preview.html").write_text(f"""<!doctype html><meta charset=utf-8>
<style>body{{margin:0;font:12px sans-serif}} .row{{display:flex;gap:40px;align-items:end;padding:30px}}
.dark{{background:{NAVY};color:#94a3b8}} .light{{background:#fff;color:#64748b}}
.cell{{display:flex;flex-direction:column;align-items:center;gap:8px}} img.pix{{image-rendering:pixelated}}</style>
<div class="row dark">{sizes}</div>
<div class="row light">{sizes}</div>
<div class="row dark"><img src="{brand.as_uri()}/resume-studio-logo-on-dark.svg" height="64"></div>
<div class="row light"><img src="{brand.as_uri()}/resume-studio-logo-on-light.svg" height="64"></div>
<div class="row light"><img class="pix" src="{brand.as_uri()}/resume-studio-icon.svg" width="32" height="32" style="width:128px;height:128px">
<span>32px rendered, magnified 4x</span><img src="{brand.as_uri()}/resume-studio-app-icon.svg" width="300"></div>
""", encoding="utf-8")
(preview_dir / "app-icon.html").write_text(
    f'<!doctype html><style>html,body{{margin:0;background:{NAVY}}}</style>'
    f'<img src="{brand.as_uri()}/resume-studio-app-icon.svg" width="1024" height="1024" style="display:block">',
    encoding="utf-8")
print("ok", [p.name for p in brand.iterdir()])
