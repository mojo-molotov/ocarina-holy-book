#!/usr/bin/env python3
"""
Ocarina PDF Generator
=====================

Generates one compressed A4 PDF per locale from a VitePress docs/ folder.

Usage:
    1. Set DOCS_DIR and FONTS_DIR below to match your environment.
    2. pip install reportlab pillow pyyaml pygments pikepdf numpy \\
                  arabic-reshaper python-bidi fonttools cairosvg
    3. python3 script.py

Inputs:  docs/ folder with .md files + images, Noto font files
Outputs: ocarina-en.pdf, ocarina-fr.pdf in OUTPUT_DIR

See prompt.md for the full specification and known pitfalls.

Character rendering philosophy:
    - Text characters (covered by NotoSans/NotoMath/NotoSymbols2) are always
      rendered as vector glyphs via drawString or <font> tags. Never as PNGs.
    - Color emoji (NotoColorEmoji) are rasterized to PNG via fontTools SVG
      table extraction + cairosvg. Pillow cannot render this font.
    - Outline PNG rasterization is a last resort for supplementary-plane
      symbols (cp >= U+10000) where ReportLab has a glyph-index encoding bug.
"""

import os
import re
import html
import subprocess
import tempfile
from functools import lru_cache
from pathlib import Path

import yaml
from PIL import Image as PILImage

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Flowable,
    Paragraph, Spacer, PageBreak, NextPageTemplate,
    HRFlowable, KeepTogether,
)
from reportlab.lib.styles import ParagraphStyle

try:
    from pygments import lex
    from pygments.lexers import get_lexer_by_name, TextLexer
    from pygments.token import Token
    PYGMENTS_OK = True
except ImportError:
    PYGMENTS_OK = False

import arabic_reshaper
from bidi.algorithm import get_display as bidi_display

# ╔════════════════════════════════════════════════════════════════════════════╗
# ║  CONFIG — adapt these to your environment, then run `python3 script.py`    ║
# ╚════════════════════════════════════════════════════════════════════════════╝
# Paths
DOCS_DIR    = Path("/home/claude/docs")
FONTS_DIR   = Path("/home/claude/fonts")
OUTPUT_DIR  = Path("/mnt/user-data/outputs")
PUBLIC_DIR  = DOCS_DIR / "public"   # images referenced by /assets/... in markdown

# Page layout (A4)
PAGE_W, PAGE_H = A4
MARGIN_L = 20 * mm
MARGIN_R = 20 * mm
MARGIN_T = 20 * mm
MARGIN_B = 25 * mm
CONTENT_W = PAGE_W - MARGIN_L - MARGIN_R
CONTENT_H = PAGE_H - MARGIN_T - MARGIN_B

# Code blocks
_CODE_WRAP_COL = 75   # max line width inside code blocks (used by black + comment wrap)

OUTPUT_DIR.mkdir(exist_ok=True)
# ════════════════════════════════════════════════════════════════════════════════

# ── Font registration ─────────────────────────────────────────────────────────
def register_fonts():
    fd = FONTS_DIR
    pdfmetrics.registerFont(TTFont("NotoSans",         str(fd / "NotoSans-Regular.ttf")))
    pdfmetrics.registerFont(TTFont("NotoSans-Bold",    str(fd / "NotoSans-Bold.ttf")))
    pdfmetrics.registerFont(TTFont("NotoSans-Italic",  str(fd / "NotoSans-Italic.ttf")))
    pdfmetrics.registerFont(TTFont("NotoSans-BoldItalic", str(fd / "NotoSans-BoldItalic.ttf")))
    pdfmetrics.registerFont(TTFont("NotoMono",         str(fd / "NotoSansMono-Regular.ttf")))
    pdfmetrics.registerFont(TTFont("NotoArabic",       str(fd / "NotoNaskhArabic-Regular.ttf")))
    pdfmetrics.registerFont(TTFont("NotoSymbols2",     str(fd / "NotoSansSymbols2-Regular.ttf")))
    pdfmetrics.registerFont(TTFont("NotoMath",         str(fd / "NotoSansMath-Regular.ttf")))
    pdfmetrics.registerFontFamily(
        "NotoSans",
        normal="NotoSans",
        bold="NotoSans-Bold",
        italic="NotoSans-Italic",
        boldItalic="NotoSans-BoldItalic",
    )

register_fonts()

# ── Font coverage lookup ──────────────────────────────────────────────────────
# Load cmaps via fontTools (also used below for the emoji font), avoiding
# 3 redundant ReportLab TTFont parses just to get character coverage.
def _load_cmap(path: Path) -> set[int]:
    from fontTools.ttLib import TTFont as _FT
    return set(_FT(str(path)).getBestCmap().keys())

_sym2_cmap = _load_cmap(FONTS_DIR / "NotoSansSymbols2-Regular.ttf")
_math_cmap = _load_cmap(FONTS_DIR / "NotoSansMath-Regular.ttf")
_ns_cmap   = _load_cmap(FONTS_DIR / "NotoSans-Regular.ttf")

@lru_cache(maxsize=None)
def fallback_font_for(cp: int) -> str | None:
    """Return the fallback font name for a codepoint, or None if NotoSans covers it.

    NotoSans covers Basic Latin + Latin-1 (U+0000–U+00FF), Latin Extended-A/B,
    Greek, Cyrillic, and a large chunk of General Punctuation / Letterlike
    Symbols (em-dash, en-dash, ellipsis, fractions, etc.) up to U+25CC.
    We check the actual NotoSans cmap so no symbol it can render is ever
    incorrectly routed to a fallback font.
    """
    if cp in _ns_cmap:
        return None
    if cp in _sym2_cmap:
        return "NotoSymbols2"
    if cp in _math_cmap:
        return "NotoMath"
    return None

# ── Emoji rasterization (NotoColorEmoji SVG → cairosvg → PNG) ─────────────────
# NotoColorEmoji uses COLR/CPAL + SVG tables; Pillow cannot render these.
# We use fontTools to extract the per-glyph SVG and cairosvg to rasterize it.
# Glob to support all NotoColorEmoji variants:
#   NotoColorEmoji.ttf            (apt)
#   NotoColorEmoji-Regular.ttf    (upstream)
#   NotoColorEmoji-flat.ttf       (alternate)
_EMOJI_FONT_PATH = next(
    (str(p) for p in sorted(FONTS_DIR.glob("NotoColorEmoji*.ttf"))),
    None,
)
# Cache survives across builds (persistent in ~/.cache, not /tmp).
_EMOJI_CACHE_DIR = Path.home() / ".cache" / "ocarina-pdf" / "emoji"
_EMOJI_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# fontTools data loaded once at startup (font object + cmap + name→id map)
_EMOJI_FT        = None
_EMOJI_CMAP: dict[int, str] = {}
_EMOJI_NAME_TO_ID: dict[str, int] = {}

def _init_emoji_svg():
    global _EMOJI_FT, _EMOJI_CMAP, _EMOJI_NAME_TO_ID
    if not _EMOJI_FONT_PATH:
        return
    try:
        from fontTools.ttLib import TTFont as _FT
        _EMOJI_FT = _FT(_EMOJI_FONT_PATH)
        _EMOJI_CMAP.update(_EMOJI_FT.getBestCmap())
        for idx, name in enumerate(_EMOJI_FT.getGlyphOrder()):
            _EMOJI_NAME_TO_ID[name] = idx
    except Exception as e:
        print(f"  [emoji] fontTools init failed: {e}")

_init_emoji_svg()

def _is_emoji_cp(cp: int) -> bool:
    """Return True for codepoints outside NotoSans that live in emoji/symbol ranges."""
    if cp in _ns_cmap:
        return False   # NotoSans renders it natively — never rasterize
    return (
        0x2000 <= cp <= 0x27BF   # misc symbols, dingbats, arrows, etc.
        or 0x2900 <= cp <= 0x2BFF
        or 0x1F000 <= cp <= 0x1FAFF  # main emoji block
    )


def _is_emoji_cp_raw(cp: int) -> bool:
    """Range-only emoji check, ignoring _ns_cmap.

    Used by the VS16-promotion path: when a codepoint IS in _ns_cmap but is
    followed by U+FE0F, we still want to check whether the codepoint falls in
    an emoji range so we can try color-emoji rendering.
    """
    return (
        0x2000 <= cp <= 0x27BF
        or 0x2900 <= cp <= 0x2BFF
        or 0x1F000 <= cp <= 0x1FAFF
    )

# Sentinel: cache keys (hex codepoint strings) known to produce no usable glyph
_emoji_miss_cache: set[str] = set()


def render_emoji_png(seq: str) -> str | None:
    """
    Rasterize an emoji sequence to a PNG via NotoColorEmoji's SVG table + cairosvg.

    NotoColorEmoji ships as a COLR v1 / SVG font; Pillow's embedded_color=True
    only handles CBDT/CBLC bitmap fonts and produces empty images for this font.
    Instead we:
      1. Look up the glyph ID for the requested codepoint (with VS16 support).
      2. Find the SVG document that covers that glyph ID.
      3. Extract <g id="glyphN">…</g> via regex (avoids parsing the 14 MB SVG
         with ElementTree, which would be very slow and can OOM).
      4. Prepend the shared <defs> block (needed for xlink gradients).
      5. Wrap everything in a standalone SVG with `viewBox="0 -920 1280 1140"`
         (NotoColorEmoji SVG coords are already Y-down — no flip needed).
      6. Render to PNG with cairosvg and cache the result.
    """
    if not _EMOJI_FT:
        return None

    # Cache key uses all codepoints in the sequence to distinguish e.g. ⬆ vs ⬆️
    cache_key = "_".join(f"{ord(c):05X}" for c in seq)
    if cache_key in _emoji_miss_cache:
        return None
    cache_path = _EMOJI_CACHE_DIR / f"emoji_{cache_key}.png"
    if cache_path.exists():
        return str(cache_path)

    try:
        import re as _re
        import cairosvg as _cairosvg

        base_cp = ord(seq[0])
        vs_cp   = ord(seq[1]) if len(seq) > 1 else None

        # Variation-selector lookup (e.g. U+2708 U+FE0F → coloured airplane)
        gname = None
        if vs_cp is not None and hasattr(_EMOJI_FT, 'get'):
            cmap14_tbl = None
            for t in _EMOJI_FT['cmap'].tables:
                if hasattr(t, 'uvsDict'):
                    cmap14_tbl = t; break
            if cmap14_tbl and vs_cp in cmap14_tbl.uvsDict:
                for base, gn in (cmap14_tbl.uvsDict[vs_cp] or []):
                    if base == base_cp and gn:
                        gname = gn; break

        if not gname:
            gname = _EMOJI_CMAP.get(base_cp)
        if not gname:
            _emoji_miss_cache.add(cache_key); return None

        gid = _EMOJI_NAME_TO_ID.get(gname)
        if gid is None:
            _emoji_miss_cache.add(cache_key); return None

        svg_table = _EMOJI_FT.get('SVG ')
        if not svg_table:
            _emoji_miss_cache.add(cache_key); return None

        # Locate the SVG document for this glyph ID
        doc_data: str | None = None
        for doc in svg_table.docList:
            if doc.startGlyphID <= gid <= doc.endGlyphID:
                doc_data = doc.data if isinstance(doc.data, str) else doc.data.decode('utf-8')
                break
        if not doc_data:
            _emoji_miss_cache.add(cache_key); return None

        # Extract <g id="glyphN">…</g> via balanced-tag scan (regex avoids
        # fully parsing the large shared document)
        tag = f'<g id="glyph{gid}">'
        idx = doc_data.find(tag)
        if idx == -1:
            _emoji_miss_cache.add(cache_key); return None
        depth, pos = 0, idx
        while pos < len(doc_data):
            og = doc_data.find('<g', pos)
            cg = doc_data.find('</g>', pos)
            if cg == -1: break
            if og != -1 and og < cg:
                depth += 1; pos = og + 2
            else:
                depth -= 1; pos = cg + 4
                if depth == 0: break
        glyph_g = doc_data[idx:pos]

        # Extract shared <defs> (contains gradient definitions for xlink refs)
        m = _re.search(r'<defs>.*?</defs>', doc_data, _re.DOTALL)
        defs = m.group(0) if m else ''

        # Build a standalone SVG.
        # NotoColorEmoji SVG glyphs use screen-convention coordinates:
        #   Y negative = above baseline, Y positive = below baseline.
        # Glyph Y coords typically span from ~-920 to ~+220 (1140 units).
        # Glyph X coords span from ~0 to ~1280.
        # No Y-axis flip is needed — the coordinates are already Y-down.
        svg_str = (
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'viewBox="0 -920 1280 1140" '
            f'width="512" height="512">'
            f'{defs}'
            f'{glyph_g}'
            f'</svg>'
        )
        png_bytes = _cairosvg.svg2png(bytestring=svg_str.encode(),
                                       output_width=512, output_height=512)
        if not png_bytes or len(png_bytes) < 100:
            _emoji_miss_cache.add(cache_key); return None

        cache_path.write_bytes(png_bytes)
        return str(cache_path)

    except Exception as e:
        print(f"  [warn] render_emoji_png({seq!r}): {e}")
        _emoji_miss_cache.add(cache_key)
        return None

# Map from ReportLab font name → TTF path, for outline rasterization.
_OUTLINE_FONT_PATHS: dict[str, str] = {
    "NotoSymbols2": str(FONTS_DIR / "NotoSansSymbols2-Regular.ttf"),
    "NotoMath":     str(FONTS_DIR / "NotoSansMath-Regular.ttf"),
}
_outline_miss_cache: set[str] = set()

def render_outline_png(ch: str, font_name: str) -> str | None:
    """
    Rasterize a single outline-font symbol to a black PNG via Pillow.

    Used because ReportLab encodes high-codepoint characters as internal glyph
    indices (not Unicode values) when passed through <font> tags or
    canvas.drawString, producing wrong glyphs.  Rasterizing via Pillow and
    embedding as an image bypasses that limitation entirely.

    Renders in black (0,0,0) at a generous size so anti-aliasing is smooth,
    then lets ReportLab scale the image to fit inline (width=11 height=11).
    """
    font_path = _OUTLINE_FONT_PATHS.get(font_name)
    if not font_path:
        return None
    cache_key = f"outline_{font_name}_{ord(ch):05X}"
    if cache_key in _outline_miss_cache:
        return None
    cache_path = _EMOJI_CACHE_DIR / f"{cache_key}.png"
    if cache_path.exists():
        return str(cache_path)
    try:
        from PIL import ImageFont, ImageDraw, Image as _PILImage
        import numpy as np
        size = 80   # render large for clean anti-aliasing, ReportLab scales down
        font = ImageFont.truetype(font_path, size)
        img = _PILImage.new('RGBA', (size + 20, size + 20), (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)
        draw.text((5, 5), ch, font=font, fill=(0, 0, 0, 255))
        bbox = img.getbbox()
        if not bbox:
            _outline_miss_cache.add(cache_key)
            return None
        cropped = img.crop(bbox)
        alpha_arr = np.frombuffer(cropped.split()[-1].tobytes(), dtype=np.uint8)
        if not np.any(alpha_arr > 10):
            _outline_miss_cache.add(cache_key)
            return None
        cropped.save(str(cache_path), 'PNG')
        return str(cache_path)
    except Exception:
        _outline_miss_cache.add(cache_key)
        return None


# ── Styles ────────────────────────────────────────────────────────────────────
def make_styles() -> dict:
    s: dict = {}

    def ns(**kw):
        base = dict(fontName="NotoSans", fontSize=10, leading=14, spaceAfter=6)
        base.update(kw)
        return base

    s["Normal"] = ParagraphStyle("Normal", **ns())

    # All headings and chapter label share leftIndent=0 (no indent)
    s["H1"] = ParagraphStyle("H1", fontName="NotoSans-Bold", fontSize=20, leading=26,
                               spaceAfter=10, spaceBefore=14, leftIndent=0)
    s["H2"] = ParagraphStyle("H2", fontName="NotoSans-Bold", fontSize=16, leading=21,
                               spaceAfter=8,  spaceBefore=12, leftIndent=0)
    s["H3"] = ParagraphStyle("H3", fontName="NotoSans-Bold", fontSize=13, leading=18,
                               spaceAfter=6,  spaceBefore=10, leftIndent=0)
    s["H4"] = ParagraphStyle("H4", fontName="NotoSans-Bold", fontSize=11, leading=15,
                               spaceAfter=5,  spaceBefore=8,  leftIndent=0)
    s["H5"] = ParagraphStyle("H5", fontName="NotoSans-Bold", fontSize=10, leading=14,
                               spaceAfter=4,  spaceBefore=6,  leftIndent=0)
    s["H6"] = ParagraphStyle("H6", fontName="NotoSans-Italic", fontSize=10, leading=14,
                               spaceAfter=4,  spaceBefore=6,  leftIndent=0)

    # Chapter header: "Chapter N" label above H1 title
    s["ChapterLabel"] = ParagraphStyle(
        "ChapterLabel", fontName="NotoSans-Bold", fontSize=11, leading=15,
        spaceAfter=2, spaceBefore=10,
        textColor=colors.HexColor("#888888"), leftIndent=0,
    )
    # Chapter subtitle = description, flush-left with same leftIndent=0
    s["ChapterSubtitle"] = ParagraphStyle(
        "ChapterSubtitle", fontName="NotoSans-Italic", fontSize=11, leading=15,
        spaceAfter=14, spaceBefore=2, leftIndent=0,
        textColor=colors.HexColor("#555555"),
    )

    # Bullet: slight indent for the bullet symbol
    s["Bullet"] = ParagraphStyle("Bullet", **ns(leftIndent=14, firstLineIndent=0))

    # Blockquote: left bar + italic, generous bottom margin
    s["Blockquote"] = ParagraphStyle(
        "Blockquote", fontName="NotoSans-Italic", fontSize=10, leading=14,
        leftIndent=16, spaceAfter=14, spaceBefore=4,
        textColor=colors.HexColor("#555555"),
    )

    # Caption for centered image captions
    s["Caption"] = ParagraphStyle(
        "Caption", fontName="NotoSans-Italic", fontSize=8, leading=12,
        alignment=1, spaceAfter=10, spaceBefore=6,
    )

    # Right-aligned quote author (― Laozi, etc.)
    s["QuoteAuthor"] = ParagraphStyle(
        "QuoteAuthor", fontName="NotoSans-Italic", fontSize=9, leading=13,
        alignment=2, spaceAfter=8, spaceBefore=0,
    )

    s["Footnote"] = ParagraphStyle("Footnote", **ns(fontSize=8, leading=11, spaceAfter=2))

    s["CoverTitle"] = ParagraphStyle(
        "CoverTitle", fontName="NotoSans-Bold", fontSize=32, leading=40,
        alignment=1, textColor=colors.white,
    )
    s["CoverAuthor"] = ParagraphStyle(
        "CoverAuthor", fontName="NotoSans-Italic", fontSize=16, leading=22,
        alignment=1, textColor=colors.white,
    )
    s["ToCTitle"] = ParagraphStyle(
        "ToCTitle", fontName="NotoSans-Bold", fontSize=18, leading=24,
        spaceAfter=14, leftIndent=0,
    )
    return s

STYLES = make_styles()

# ── Helpers: XML escaping & Arabic detection ──────────────────────────────────
VARIATION_SEL = '\uFE0F'

def escape_xml(s: str) -> str:
    """Decode HTML entities, normalize NBSP, then XML-escape.

    Called from multiple sites: some (inline_to_rl) have already unescaped
    their input, others (HTML block parsing, chapter titles) have not.
    html.unescape is idempotent on text without entities, so calling it
    twice is harmless — keep the unescape here so the function is safe
    everywhere.
    """
    s = html.unescape(s)
    s = s.replace('\xa0', ' ')
    s = (s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
         .replace('"', '&quot;').replace("'", '&#39;'))
    return s

def is_arabic_cp(cp: int) -> bool:
    return (0x0600 <= cp <= 0x06FF or 0x0750 <= cp <= 0x077F or
            0xFB50 <= cp <= 0xFDFF or 0xFE70 <= cp <= 0xFEFF)

# ── Inline markdown → ReportLab XML ──────────────────────────────────────────
def inline_to_rl(text: str, footnotes: list | None = None) -> str:
    """
    Convert markdown inline syntax to a ReportLab XML string.
    html.unescape() is applied to the whole input first so &nbsp; etc. are resolved
    before character-by-character processing.
    """
    if footnotes is None:
        footnotes = []
    text = html.unescape(text)   # ← decode entities on the full string first
    result: list[str] = []
    i = 0
    n = len(text)

    while i < n:
        ch = text[i]

        # ── Hard-break sentinel (from join_paragraph_lines) ───────────────────
        # Allows bold/italic markers to span across a hard-break boundary: the
        # whole paragraph text (including \x00BR\x00 sentinels) is processed in
        # a single inline_to_rl call, so ** opening and closing markers are
        # always visible to each other regardless of line breaks.
        if text[i:i+4] == '\x00BR\x00':
            result.append('<br/>')
            i += 4; continue

        # ── Code span ─────────────────────────────────────────────────────────
        if ch == '`':
            j = text.find('`', i + 1)
            if j == -1:
                result.append(escape_xml(ch)); i += 1; continue
            inner = escape_xml(text[i+1:j])
            result.append(f'<font name="NotoMono" color="#d73a49">{inner}</font>')
            i = j + 1; continue

        # ── Bold-italic *** ───────────────────────────────────────────────────
        if text[i:i+3] == '***':
            j = text.find('***', i + 3)
            if j != -1:
                result.append(f'<b><i>{inline_to_rl(text[i+3:j], footnotes)}</i></b>')
                i = j + 3; continue

        # ── Bold ** ──────────────────────────────────────────────────────────
        if text[i:i+2] == '**':
            j = text.find('**', i + 2)
            if j != -1:
                result.append(f'<b>{inline_to_rl(text[i+2:j], footnotes)}</b>')
                i = j + 2; continue

        # ── Italic _ (snake_case-safe) ────────────────────────────────────────
        if ch == '_' and not (i > 0 and text[i-1].isalnum()):
            j = i + 1
            while j < n:
                if text[j] == '_' and not (j + 1 < n and text[j+1].isalnum()):
                    break
                j += 1
            if j < n and text[j] == '_':
                result.append(f'<i>{inline_to_rl(text[i+1:j], footnotes)}</i>')
                i = j + 1; continue

        # ── Italic * ─────────────────────────────────────────────────────────
        if ch == '*' and text[i:i+2] != '**':
            j = text.find('*', i + 1)
            if j != -1:
                result.append(f'<i>{inline_to_rl(text[i+1:j], footnotes)}</i>')
                i = j + 1; continue

        # ── Autolink <https://...> or <http://...> ────────────────────────────
        if ch == '<':
            m = re.match(r'<(https?://[^>]+)>', text[i:])
            if m:
                url = m.group(1)
                footnotes.append(url)
                ref_n = len(footnotes)
                short = url[:60] + '…' if len(url) > 60 else url
                result.append(
                    f'<a href="{escape_xml(url)}" color="#0366d6">{escape_xml(short)}</a>'
                    f'<super><font size="7">[{ref_n}]</font></super>'
                )
                i += m.end(); continue

        # ── Link [text](url) ─────────────────────────────────────────────────
        if ch == '[':
            m = re.match(r'\[([^\]]*)\]\((<[^>]*>|[^)]*(?:\([^)]*\)[^)]*)*)\)', text[i:])
            if m:
                link_text = inline_to_rl(m.group(1), footnotes)
                url = m.group(2)
                # Strip angle brackets from <url> form
                if url.startswith('<') and url.endswith('>'):
                    url = url[1:-1]
                footnotes.append(url)
                ref_n = len(footnotes)
                result.append(
                    f'<a href="{escape_xml(url)}" color="#0366d6">{link_text}</a>'
                    f'<super><font size="7">[{ref_n}]</font></super>'
                )
                i += m.end(); continue

        # ── Variation selector — strip silently ──────────────────────────────
        if ch == VARIATION_SEL:
            i += 1; continue

        # ── Arabic run ────────────────────────────────────────────────────────
        cp = ord(ch)
        if is_arabic_cp(cp):
            j = i
            while j < n and (is_arabic_cp(ord(text[j])) or text[j] == ' '):
                j += 1
            run = text[i:j]
            # Reshape: maps logical Unicode codepoints to their correct
            # contextual presentation forms and reverses for visual LTR display.
            run = bidi_display(arabic_reshaper.reshape(run))
            result.append(f'<font name="NotoArabic"> {escape_xml(run)} </font>')
            i = j; continue

        # ── VS16 emoji promotion ──────────────────────────────────────────────
        # Some codepoints live in _ns_cmap (e.g. ℹ U+2139) but when followed
        # by U+FE0F they request color-emoji rendering (ℹ️).  Check this BEFORE
        # the general symbol/emoji handler so these are not rendered as plain
        # NotoSans text glyphs.
        has_vs_next = (i + 1 < n and text[i + 1] == VARIATION_SEL)
        if has_vs_next and cp in _ns_cmap and _is_emoji_cp_raw(cp):
            seq = ch + VARIATION_SEL
            png = render_emoji_png(seq)
            if png:
                result.append(
                    f'<img src="{png}" width="13" height="13" valign="-2"/>'
                )
                i += 2   # skip base + VS16
                continue
            # render_emoji_png failed: fall through to plain-char rendering

        # ── Symbol / emoji: rasterize color emoji; fallback font for others ─────
        # Guard: if NotoSans covers this codepoint natively, skip the special
        # handler entirely and fall through to plain-char rendering below.
        # Without this guard, codepoints like → (U+2192) that are in the
        # _is_emoji_cp range (0x2000–0x27BF) but are also in _ns_cmap would
        # incorrectly go through render_emoji_png / render_outline_png, which
        # produces small B&W PNG artefacts instead of clean vector glyphs.
        fb = fallback_font_for(cp)
        if fb or (cp not in _ns_cmap and _is_emoji_cp(cp)):
            j = i
            run_chars: list[str] = []
            while j < n:
                c = text[j]
                c_cp = ord(c)
                # Keep U+FE0F in run_chars so the inner loop can detect
                # color-emoji sequences (e.g. ⚠️ = U+26A0 U+FE0F).
                # It will be consumed by the has_vs logic and never emitted.
                if c == VARIATION_SEL:
                    run_chars.append(c)
                    j += 1; continue
                if c_cp in _ns_cmap or not (fallback_font_for(c_cp) or _is_emoji_cp(c_cp)):
                    break
                run_chars.append(c)
                j += 1

            i2 = 0
            while i2 < len(run_chars):
                ec = run_chars[i2]
                ec_cp = ord(ec)
                # Include trailing VS16 in the sequence so render_emoji_png
                # gets the color-emoji variant (e.g. \u2b06\ufe0f = ⬆️)
                has_vs = (i2 + 1 < len(run_chars)
                          and run_chars[i2 + 1] == VARIATION_SEL)
                seq = ec + VARIATION_SEL if has_vs else ec
                if _is_emoji_cp(ec_cp):
                    png = render_emoji_png(seq)
                    if png:
                        result.append(
                            f'<img src="{png}" width="13" height="13" valign="-2"/>'
                        )
                        i2 += 2 if has_vs else 1
                        continue
                # Fallback font (NotoMath / NotoSymbols2).
                # For BMP codepoints (cp < U+10000), <font> tags work correctly
                # in ReportLab Paragraph XML — use them for crisp vector rendering.
                # For supplementary-plane codepoints, ReportLab has a glyph-index
                # encoding issue, so we fall back to render_outline_png there.
                efb = fallback_font_for(ec_cp)
                if efb:
                    if ec_cp < 0x10000:
                        result.append(
                            f'<font name="{efb}">{escape_xml(ec)}</font>'
                        )
                    else:
                        opng = render_outline_png(ec, efb)
                        if opng:
                            result.append(
                                f'<img src="{opng}" width="13" height="13" valign="-2"/>'
                            )
                        else:
                            result.append(
                                f'<font name="{efb}">{escape_xml(ec)}</font>'
                            )
                else:
                    result.append(escape_xml(ec))
                i2 += 1
            i = j; continue

        # ── Plain character ───────────────────────────────────────────────────
        result.append(escape_xml(ch))
        i += 1

    return ''.join(result)


def join_paragraph_lines(lines: list[str]) -> str:
    """CommonMark hard-break: 2+ trailing spaces → \\x00BR\\x00 sentinel.

    Returns a single string (not a list) so that inline_to_rl processes the
    whole paragraph in one pass.  This is required for bold/italic markers
    that span a hard-break boundary (e.g. ``**opening text.  \\nclosing.**``):
    splitting into segments first and calling inline_to_rl per-segment breaks
    such spans because the opening ``**`` and closing ``**`` end up in separate
    calls where neither can find its matching delimiter.
    """
    processed = []
    for line in lines:
        if line.endswith('  '):
            processed.append(line.rstrip() + '\x00BR\x00')
        else:
            processed.append(line)
    return ' '.join(processed)


# ── Pygments token→color (GitHub light theme) ─────────────────────────────────
_TOKEN_COLORS: dict = {
    Token.Keyword:                  '#d73a49',
    Token.Keyword.Declaration:      '#d73a49',
    Token.Keyword.Type:             '#d73a49',
    Token.Keyword.Namespace:        '#d73a49',
    Token.Name.Builtin:             '#005cc5',
    Token.Name.Function:            '#6f42c1',
    Token.Name.Function.Magic:      '#6f42c1',
    Token.Name.Class:               '#6f42c1',
    Token.Name.Decorator:           '#6f42c1',
    Token.Name.Exception:           '#6f42c1',
    Token.Literal.String:           '#032f62',
    Token.Literal.String.Doc:       '#6a737d',
    Token.Literal.String.Interpol:  '#032f62',
    Token.Literal.String.Affix:     '#032f62',
    Token.Literal.Number:           '#005cc5',
    Token.Comment:                  '#6a737d',
    Token.Operator:                 '#d73a49',
    Token.Operator.Word:            '#d73a49',
    Token.Punctuation:              '#24292e',
    Token.Name.Attribute:           '#005cc5',
    Token.Name.Tag:                 '#22863a',
}
_DEFAULT_COLOR = '#24292e'

def _token_color(ttype) -> str:
    while ttype:
        if ttype in _TOKEN_COLORS:
            return _TOKEN_COLORS[ttype]
        ttype = ttype.parent
    return _DEFAULT_COLOR


def _tokenize_to_line_spans(code: str, lang: str) -> list[list[tuple[str, str]]]:
    """
    Tokenize `code` with Pygments and return a list of lines.
    Each line is a list of (hex_color, text) tuples.
    """
    raw_lines = code.split('\n')
    if not PYGMENTS_OK:
        return [[(_DEFAULT_COLOR, line)] for line in raw_lines]

    try:
        lexer = get_lexer_by_name(lang, stripall=False)
    except Exception:
        lexer = TextLexer()

    colored: list[tuple[str, str]] = [(_token_color(t), v) for t, v in lex(code, lexer)]

    # Split into lines preserving token boundaries
    line_spans: list[list[tuple[str, str]]] = []
    current: list[tuple[str, str]] = []
    for color, text in colored:
        parts = text.split('\n')
        for idx, part in enumerate(parts):
            if part:
                current.append((color, part))
            if idx < len(parts) - 1:
                line_spans.append(current)
                current = []
    if current:
        line_spans.append(current)

    # Align with raw_lines
    while len(line_spans) < len(raw_lines):
        line_spans.append([])
    return line_spans[:len(raw_lines)]


# ── Code block pre-processing ─────────────────────────────────────────────────
# (_CODE_WRAP_COL is defined in the CONFIG section at the top of the file)

def _reformat_python_with_black(code: str) -> str:
    """
    Run `black --line-length 75` on a Python code snippet.
    Black produces idiomatic, backslash-free line breaks (function argument
    expansion, parenthesised expressions, etc.).
    Returns the reformatted code, or the original if black fails or is absent.
    """
    try:
        r = subprocess.run(
            ['python3', '-m', 'black', '--line-length', str(_CODE_WRAP_COL),
             '--quiet', '-'],
            input=code, capture_output=True, text=True, timeout=10,
        )
        if r.returncode == 0 and r.stdout:
            # black adds a trailing newline; strip it to match the original
            return r.stdout.rstrip('\n')
    except Exception:
        pass
    return code


def wrap_comment(line: str, indent_str: str = '') -> list[str]:
    """
    Wrap a single comment line so every emitted line is <= 75 chars.
    Break points (in priority order):
      1. Last '(' whose index is < avail AND the substring from that '(' to
         the matching ')' fits on a continuation line — this keeps parenthesised
         clauses (e.g. mypy error messages) together on a single line.
      2. First ';' whose index is < avail (strict, no over-75 tolerance)
      3. First ',' whose index is < avail
      4. Last space within avail chars
      5. No good break found — emit as-is to avoid infinite loop
    Continuation lines use ``indent_str + '# '`` as prefix.
    Brackets [] are NOT used as break characters.
    """
    m = re.match(r'^(\s*#\s*)(.*)', line)
    if not m:
        return [line]
    prefix = m.group(1)
    remaining = m.group(2)
    cont_prefix = indent_str + '# '
    result: list[str] = []
    current_prefix = prefix

    while True:
        avail = _CODE_WRAP_COL - len(current_prefix)
        if avail <= 0 or len(remaining) <= avail:
            result.append(current_prefix + remaining)
            break

        # Priority 1: break just before a '(' that opens a parenthesised
        # clause.  We always prefer this over comma/semicolon breaks so that
        # error messages like:
        #   # error: Expected type 'X' (matched generic type 'Y'), got 'Z'
        # wrap cleanly at the '(' regardless of whether the parenthesised
        # content itself fits on a single continuation line (if it doesn't,
        # the next iteration will wrap it further).
        bp = -1
        paren_idx = remaining.rfind('(', 0, avail)
        if paren_idx > 0:
            bp = paren_idx  # break *before* the '('

        # Priority 2: first ';' or ',' strictly within avail
        if bp == -1:
            for sep in (';', ','):
                idx = remaining.find(sep)
                if 0 < idx < avail:
                    bp = idx + 1  # break after the separator
                    break

        # Priority 3: last space strictly within avail
        if bp == -1:
            bp = remaining[:avail].rfind(' ')

        if bp <= 0:
            result.append(current_prefix + remaining)
            break

        result.append(current_prefix + remaining[:bp].rstrip())
        remaining = remaining[bp:].lstrip()
        current_prefix = cont_prefix

    return result


def _wrap_comment_only_lines(code: str) -> str:
    """
    Apply wrap_comment to any comment line still over 75 chars after black
    reformatting (black does not reflow comments).
    Also handles non-comment lines that exceed 75 chars due to a trailing
    inline comment (e.g. `some_expr  # <- [!]`): the comment is peeled off
    and placed on its own continuation line.
    """
    out: list[str] = []
    for line in code.split('\n'):
        if len(line) > _CODE_WRAP_COL:
            stripped = line.lstrip()
            indent = line[:len(line) - len(stripped)]
            if stripped.startswith('#'):
                # Pure comment line → word-wrap it
                out.extend(wrap_comment(line, indent))
                continue
            # Non-comment line with trailing inline comment?
            # Find a '#' that is not inside a string (simple heuristic: last
            # '#' preceded by whitespace and not inside quotes).
            ic = _find_inline_comment(stripped)
            if ic != -1:
                code_part = (indent + stripped[:ic]).rstrip()
                comment_part = stripped[ic:]          # includes the '#'
                # Only peel if the full line truly overflows. If even the
                # code part alone is too long we still peel (removes the
                # comment contribution), but we don't peel when the full
                # line already fits — that would move comments unnecessarily.
                if len(line) > _CODE_WRAP_COL:
                    out.append(code_part)
                    out.extend(wrap_comment(indent + comment_part, indent))
                    continue
        out.append(line)
    return '\n'.join(out)


def _find_inline_comment(s: str) -> int:
    """
    Return the index of a trailing inline ``#`` comment in a stripped source
    line, or -1 if none.  Uses a minimal quote-tracking state machine so we
    don't mistake a ``#`` inside a string literal for a comment marker.
    """
    in_single = False
    in_double = False
    i = 0
    while i < len(s):
        c = s[i]
        if c == '\\' and (in_single or in_double):
            i += 2; continue
        if c == "'" and not in_double:
            in_single = not in_single
        elif c == '"' and not in_single:
            in_double = not in_double
        elif c == '#' and not in_single and not in_double:
            return i
        i += 1
    return -1


def _split_long_string_literal(line: str) -> list[str]:
    """
    Split a line that is too long because it contains a long string literal.
    Uses implicit string concatenation (PEP 3120).
    Only handles the common case: a single long quoted string (f-string or
    regular) as the only or last argument on the line.
    Returns a list of lines, or [line] if no split could be found.
    """
    stripped = line.lstrip()
    indent = line[:len(line) - len(stripped)]
    # Find a quoted string that spans most of the line
    # Support: f"...", "...", f'...', '...'
    # Tail may be punctuation (,) or whitespace
    m = re.match(r'^(.*?)(f?["\'])(.+)(["\'])([,\s]*)$', stripped)
    if not m:
        return [line]
    prefix, q_open, content, q_close, tail = m.groups()
    if q_open[-1] != q_close:  # mismatched quote types
        return [line]
    quote = q_open[-1]
    fprefix = 'f' if q_open.startswith('f') else ''
    # Find a good split point in the content near the middle
    avail = _CODE_WRAP_COL - len(indent) - len(prefix) - len(q_open) - 1
    if avail < 10 or len(content) <= avail:
        return [line]
    # Try to split at a space within the string content
    bp = content.rfind(' ', 0, avail)
    if bp <= 0:
        bp = avail
    first_half  = content[:bp]
    second_half = content[bp:]
    cont_indent = indent + ' ' * 4
    line1 = f'{indent}{prefix}{fprefix}{quote}{first_half}{quote}'
    line2 = f'{cont_indent}{fprefix}{quote}{second_half}{quote}{tail}'
    return [line1, line2]


def preprocess_code_block(code: str, lang: str) -> str:
    """
    Full pre-processing pipeline for a code block:
      1. If lang is 'python': run black.
      2. Wrap any remaining comment lines that exceed 75 cols.
    """
    is_python = lang in ('python', 'py')
    if is_python and code.strip():
        code = _reformat_python_with_black(code)
    code = _wrap_comment_only_lines(code)
    return code


# ── CodeBlock Flowable ────────────────────────────────────────────────────────
class CodeBlock(Flowable):
    _PADDING    = 8
    _LINE_H     = 11.5
    _FONT       = 'NotoMono'
    _FONT_SIZE  = 8.0
    _BG         = colors.HexColor('#f6f8fa')
    _BORDER     = colors.HexColor('#e1e4e8')

    def __init__(self, code: str, lang: str = 'text'):
        super().__init__()
        self.spaceAfter = 14          # breathing room after the block
        self.lang = lang
        code = preprocess_code_block(code, lang)  # black + comment wrap
        self.code = code
        self._lines = code.split('\n')
        self._token_lines = _tokenize_to_line_spans(code, lang)
        self._avail_w: float = CONTENT_W
        self._h: float = 0.0

    def _compute_height(self) -> float:
        return len(self._lines) * self._LINE_H + 2 * self._PADDING

    def __repr__(self):
        first = (self._lines[0] if self._lines else '').strip()[:40]
        return f"CodeBlock({self.lang}, {len(self._lines)} lines, first={first!r})"

    def wrap(self, availWidth, availHeight):
        self._avail_w = availWidth
        self._h = self._compute_height()
        return (availWidth, self._h)

    def split(self, availWidth, availHeight):
        max_lines = max(0, int((availHeight - 2 * self._PADDING) / self._LINE_H))
        if max_lines == 0:
            return []
        if max_lines >= len(self._lines):
            self._avail_w = availWidth
            self._h = self._compute_height()
            return [self]

        def _clone(lines, token_lines):
            b = CodeBlock.__new__(CodeBlock)
            b.spaceAfter = self.spaceAfter
            b.lang = self.lang
            b.code = '\n'.join(lines)
            b._lines = lines
            b._token_lines = token_lines
            b._avail_w = availWidth
            b._h = len(lines) * self._LINE_H + 2 * self._PADDING
            return b

        return [
            _clone(self._lines[:max_lines],  self._token_lines[:max_lines]),
            _clone(self._lines[max_lines:],  self._token_lines[max_lines:]),
        ]

    def draw(self):
        c = self.canv
        w, h = self._avail_w, self._h
        c.saveState()

        # Background + border
        c.setFillColor(self._BG)
        c.roundRect(0, 0, w, h, 4, fill=1, stroke=0)
        c.setStrokeColor(self._BORDER)
        c.setLineWidth(0.5)
        c.roundRect(0, 0, w, h, 4, fill=0, stroke=1)

        # Text with per-token colors + per-character font fallback.
        # NotoMono is used for all ASCII/monospace text; characters covered
        # by NotoSansSymbols2 or NotoSansMath (arrows, warning signs, etc.)
        # are rendered with the appropriate fallback font at the same size so
        # they appear inline without substitution.
        y = h - self._PADDING - self._FONT_SIZE
        for spans in self._token_lines:
            x = self._PADDING
            for color, text in spans:
                c.setFillColor(colors.HexColor(color))
                # Group consecutive characters that share the same font
                seg_font  = None
                seg_chars = []

                def _flush_seg():
                    nonlocal x
                    if not seg_chars:
                        return
                    s = ''.join(seg_chars)
                    c.setFont(seg_font, self._FONT_SIZE)
                    c.drawString(x, y, s)
                    x += c.stringWidth(s, seg_font, self._FONT_SIZE)

                chars = list(text)
                ci = 0
                while ci < len(chars):
                    ch = chars[ci]
                    cp = ord(ch)
                    # U+FE0F after base = color emoji sequence
                    has_vs16 = (ci + 1 < len(chars)
                                and chars[ci + 1] == VARIATION_SEL)
                    if has_vs16 or _is_emoji_cp(cp):
                        seq = ch + VARIATION_SEL if has_vs16 else ch
                        png = render_emoji_png(seq)
                        if png:
                            _flush_seg()
                            seg_chars.clear(); seg_font = None
                            em = self._FONT_SIZE * 1.4
                            # Vertical alignment: drawString places text on the
                            # baseline at y; drawImage places the image's bottom
                            # at the given y. To center the image on the text's
                            # x-height, lower it by ~em/2 - x_height/2. For
                            # NotoMono at _FONT_SIZE=8 (em=11.2), this is ~3pt.
                            # If you change _FONT_SIZE, retune this offset.
                            img_y = y - 3
                            c.drawImage(png, x, img_y, em, em,
                                        mask="auto",
                                        preserveAspectRatio=True)
                            x += em
                            ci += 2 if has_vs16 else 1
                            continue
                        # render_emoji_png failed: for BMP codepoints with a
                        # fallback font, use drawString directly — ReportLab's
                        # glyph-index encoding bug only affects supplementary-
                        # plane characters (cp >= 0x10000).  For supplementary
                        # plane or when no fallback font exists, rasterize via
                        # Pillow as a last resort.
                        fb_name = fallback_font_for(cp)
                        if fb_name and cp < 0x10000:
                            # BMP: drawString works fine, just switch font
                            if fb_name != seg_font:
                                _flush_seg()
                                seg_chars.clear()
                                seg_font = fb_name
                            seg_chars.append(ch)
                            ci += 2 if has_vs16 else 1
                            continue
                        if fb_name:
                            opng = render_outline_png(ch, fb_name)
                            if opng:
                                _flush_seg()
                                seg_chars.clear(); seg_font = None
                                em = self._FONT_SIZE * 1.4
                                # Same vertical centering as color emoji above.
                                c.drawImage(opng, x, y - 3, em, em,
                                            mask="auto",
                                            preserveAspectRatio=True)
                                x += em
                                ci += 2 if has_vs16 else 1
                                continue
                    if ch == VARIATION_SEL:   # orphan VS16, strip
                        ci += 1; continue
                    fb = fallback_font_for(cp)
                    font = fb if fb else self._FONT
                    if font != seg_font:
                        _flush_seg()
                        seg_chars.clear()
                        seg_font = font
                    seg_chars.append(ch)
                    ci += 1
                _flush_seg()
            y -= self._LINE_H

        c.restoreState()


# ── HtmlImage Flowable ────────────────────────────────────────────────────────
class HtmlImage(Flowable):
    _MAX_H = 300

    def __init__(self, src: str, alt: str = ''):
        super().__init__()
        self.src = src
        self.alt = alt
        self.spaceBefore = 10      # space above image
        self.spaceAfter  = 4       # small space between image and caption
        self._path = self._resolve(src)
        if self._path is None:
            print(f"  [warn] image not found: {src}")
        self._px_w, self._px_h = self._get_size()
        self._rw = self._rh = self._offset = 0.0

    def __repr__(self):
        return f"HtmlImage({self.src!r}, {self._px_w}x{self._px_h})"

    def _resolve(self, src: str) -> str | None:
        p = PUBLIC_DIR / (src.lstrip('/') if src.startswith('/') else src)
        return str(p) if p.exists() else None

    def _get_size(self) -> tuple[int, int]:
        if not self._path:
            return (0, 0)
        try:
            with PILImage.open(self._path) as im:
                return im.size
        except Exception:
            return (0, 0)

    def wrap(self, availWidth, availHeight):
        if not self._px_w or not self._px_h:
            self._rw = self._rh = 0
            return (0, 0)
        scale = min(availWidth / self._px_w, self._MAX_H / self._px_h, 1.0)
        self._rw = self._px_w * scale
        self._rh = self._px_h * scale
        self._offset = (availWidth - self._rw) / 2
        return (availWidth, self._rh)

    def draw(self):
        if self._path and self._rw:
            self.canv.drawImage(self._path, self._offset, 0,
                                self._rw, self._rh, preserveAspectRatio=True)


# ── Blockquote Flowable ───────────────────────────────────────────────────────
class _BlockquoteFlowable(Flowable):
    _BAR = colors.HexColor('#d0d7de')
    _BAR_W = 3

    def __init__(self, xml_text: str):
        super().__init__()
        self.spaceAfter = 14      # generous bottom margin
        self._xml_text = xml_text
        self._para = Paragraph(xml_text, STYLES['Blockquote'])
        self._h = 0.0

    def __repr__(self):
        # _xml_text may not exist on instances built via __new__ in split(); use getattr
        snippet = (getattr(self, '_xml_text', '') or '')[:40]
        return f"_BlockquoteFlowable({snippet!r}…)"

    def wrap(self, availWidth, availHeight):
        _, self._h = self._para.wrap(availWidth - self._BAR_W - 4, availHeight)
        self._avail_w = availWidth
        return (availWidth, self._h)

    def split(self, availWidth, availHeight):
        """Split blockquote across pages via the inner Paragraph's own splitter."""
        inner_w = availWidth - self._BAR_W - 4
        parts = self._para.split(inner_w, availHeight)
        if not parts:
            return []
        result = []
        for part in parts:
            b = _BlockquoteFlowable.__new__(_BlockquoteFlowable)
            b.spaceAfter = self.spaceAfter
            b._BAR = self._BAR
            b._BAR_W = self._BAR_W
            b._para = part
            b._h = 0.0
            b._avail_w = availWidth
            result.append(b)
        return result

    def draw(self):
        c = self.canv
        c.setFillColor(self._BAR)
        c.rect(0, 0, self._BAR_W, self._h, fill=1, stroke=0)
        self._para.drawOn(c, self._BAR_W + 4, 0)


# ── Chapter marker (zero-size sentinel) ──────────────────────────────────────
class ChapterMarker(Flowable):
    def __init__(self, chapter_num: int, chapter_title: str):
        super().__init__()
        self.chapter_num = chapter_num
        self.chapter_title = chapter_title

    def wrap(self, w, h):   return (0, 0)
    def draw(self):         pass

    def __repr__(self):
        return f"ChapterMarker(#{self.chapter_num}, {self.chapter_title!r})"


# ── ToC entry (custom canvas-drawn flowable) ──────────────────────────────────
class ToCEntry(Flowable):
    _LINE_H = 18

    def __init__(self, chapter_num, chapter_label, title, page_num,
                 bold_font, reg_font, size=11):
        super().__init__()
        self.chapter_num   = chapter_num
        self.chapter_label = chapter_label
        self.title         = title
        self.page_num      = page_num
        self.bold_font     = bold_font
        self.reg_font      = reg_font
        self.size          = size
        self._avail_w      = CONTENT_W

    def wrap(self, availWidth, availHeight):
        self._avail_w = availWidth
        return (availWidth, self._LINE_H)

    def draw(self):
        c = self.canv
        baseline = 4
        label = f"{self.chapter_label} {self.chapter_num}"
        c.setFont(self.bold_font, self.size)
        c.setFillColor(colors.black)
        c.drawString(0, baseline, label)
        lw = c.stringWidth(label, self.bold_font, self.size)
        c.setFont(self.reg_font, self.size)
        c.drawString(lw + 10, baseline, self.title)
        c.drawRightString(self._avail_w, baseline, str(self.page_num))


# ── Frontmatter parsing ───────────────────────────────────────────────────────
def parse_frontmatter(text: str) -> tuple[dict, str]:
    m = re.match(r'^---\s*\n(.*?)\n---\s*\n', text, re.DOTALL)
    if not m:
        return {}, text
    fm = yaml.safe_load(m.group(1)) or {}
    return fm, text[m.end():]

def strip_author_sig(text: str) -> str:
    for pat in [
        r'\n---\n+<p align="right"><i>Игорь Казанова</i></p>\s*$',
        r'<p align="right"><i>Игорь Казанова</i></p>\s*$',
    ]:
        text = re.sub(pat, '', text, flags=re.MULTILINE)
    return text


# ── HTML block parsing ────────────────────────────────────────────────────────
_CENTER_P_RE      = re.compile(r'<p[^>]*align=["\']center["\'][^>]*>(.*?)</p>', re.DOTALL)
_RIGHT_P_RE       = re.compile(r'<p[^>]*align=["\']right["\'][^>]*>(.*?)</p>',  re.DOTALL)
_QUOTE_AUTHOR_RE  = re.compile(r'class=["\'][^"\']*inspiring-quote-author')

def _strip_tags(s: str) -> str:
    """Strip HTML tags, preserving <br/> as sentinel and converting <strong>/<em>
    to their Markdown equivalents so inline_to_rl renders them correctly.

    Conversion order matters:
      1. <br/> → sentinel (before tag stripping, so it is not lost).
      2. <strong>…</strong> → **…** and <em>…</em> → _…_ (DOTALL so they
         survive across embedded <br/> sentinels).
      3. Strip all remaining HTML tags.
    """
    s = re.sub(r'<br\s*/?>', '\x00BR\x00', s)
    s = re.sub(r'<strong>(.*?)</strong>', r'**\1**', s, flags=re.DOTALL)
    s = re.sub(r'<em>(.*?)</em>', r'_\1_', s, flags=re.DOTALL)
    return re.sub(r'<[^>]+>', '', s).strip()

def parse_html_block(tag_name: str, raw: str, footnotes: list) -> list:
    raw_stripped = raw.strip()

    # <img …>
    if tag_name == 'img':
        sm = re.search(r'src=["\']([^"\']+)["\']', raw)
        am = re.search(r'alt=["\']([^"\']*)["\']', raw)
        return [HtmlImage(sm.group(1), am.group(1) if am else '')] if sm else []

    # Author signature → drop
    if 'Игорь Казанова' in raw and 'inspiring-quote-author' not in raw:
        return []

    # Quote-author class → right-aligned italic
    if _QUOTE_AUTHOR_RE.search(raw):
        inner = _strip_tags(raw_stripped)
        return [Paragraph(inline_to_rl(inner, footnotes), STYLES['QuoteAuthor'])]

    # Right-aligned <p> (― author lines without class)
    m = _RIGHT_P_RE.match(raw_stripped)
    if m:
        inner = _strip_tags(m.group(1))
        if 'Игорь Казанова' in inner:
            return []
        return [Paragraph(inline_to_rl(inner, footnotes), STYLES['QuoteAuthor'])]

    # Center-aligned <p> (image captions, inspiring quotes)
    m = _CENTER_P_RE.match(raw_stripped)
    if m:
        inner = _strip_tags(m.group(1))
        return [Paragraph(inline_to_rl(inner, footnotes), STYLES['Caption'])]

    # Generic: strip tags and render as Normal
    inner = _strip_tags(raw_stripped)
    if not inner:
        return []
    return [Paragraph(inline_to_rl(inner, footnotes), STYLES['Normal'])]


# ── Markdown → flowables ──────────────────────────────────────────────────────
def md_to_flowables(body: str, footnotes: list) -> list:
    body = strip_author_sig(body)
    body = re.sub(r'<llm-exclude>.*?</llm-exclude>', '', body, flags=re.DOTALL)

    lines = body.split('\n')
    flowables: list = []
    para_buf: list[str] = []
    i = 0
    n = len(lines)

    def flush():
        if not para_buf:
            return
        # Process the whole paragraph text in a single inline_to_rl call so
        # that bold/italic markers spanning a hard-break boundary are resolved
        # correctly (the sentinel \x00BR\x00 is emitted as <br/> inline).
        joined = join_paragraph_lines(para_buf)
        xml = inline_to_rl(joined, footnotes)
        flowables.append(Paragraph(xml, STYLES['Normal']))
        para_buf.clear()

    while i < n:
        line = lines[i]

        # ── Fenced code block ──────────────────────────────────────────────
        if re.match(r'^```', line):
            flush()
            lang_m = re.match(r'^```(\w*)', line)
            lang = (lang_m.group(1) if lang_m and lang_m.group(1) else 'text')
            code_lines: list[str] = []
            i += 1
            while i < n and not re.match(r'^```\s*$', lines[i]):
                code_lines.append(lines[i]); i += 1
            i += 1  # closing ```
            flowables.append(CodeBlock('\n'.join(code_lines), lang))
            continue

        # ── HR ─────────────────────────────────────────────────────────────
        if re.match(r'^---\s*$', line) and not para_buf:
            flush()
            flowables.append(HRFlowable(width='100%', thickness=0.5,
                                         color=colors.HexColor('#d0d7de'), spaceAfter=8))
            i += 1; continue

        # ── HTML block ─────────────────────────────────────────────────────
        if re.match(r'^<\w', line):
            flush()
            tag_m = re.match(r'^<(\w+)', line)
            tag = tag_m.group(1) if tag_m else 'div'
            closing = f'</{tag}>'
            collected = [line]
            if closing not in line and not line.rstrip().endswith('/>'):
                i += 1
                while i < n:
                    collected.append(lines[i])
                    if closing in lines[i]:
                        i += 1; break
                    i += 1
            else:
                i += 1
            flowables.extend(parse_html_block(tag, ' '.join(collected), footnotes))
            continue

        # ── Inline image ───────────────────────────────────────────────────
        img_m = re.match(r'^!\[([^\]]*)\]\(([^)]+)\)\s*$', line)
        if img_m:
            flush()
            img_flow = HtmlImage(img_m.group(2), img_m.group(1))
            # Pair with following caption if present
            if i + 1 < n:
                nxt = lines[i+1].strip()
                cap_m = _CENTER_P_RE.match(nxt) or re.match(r'^<p[^>]*><i>(.*?)</i></p>$', nxt)
                if cap_m:
                    cap_xml = inline_to_rl(_strip_tags(cap_m.group(1)), footnotes)
                    cap_flow = Paragraph(cap_xml, STYLES['Caption'])
                    flowables.append(KeepTogether([img_flow, cap_flow]))
                    i += 2; continue
            flowables.append(img_flow)
            i += 1; continue

        # ── Heading ────────────────────────────────────────────────────────
        h_m = re.match(r'^(#{1,6})\s+(.*)', line)
        if h_m:
            flush()
            level = len(h_m.group(1))
            xml = inline_to_rl(h_m.group(2).strip(), footnotes)
            flowables.append(Paragraph(xml, STYLES.get(f'H{level}', STYLES['Normal'])))
            i += 1; continue

        # ── Blockquote ─────────────────────────────────────────────────────
        if line.startswith('>'):
            flush()
            bq: list[str] = []
            while i < n and lines[i].startswith('>'):
                bq.append(lines[i][1:].lstrip()); i += 1
            flowables.append(_BlockquoteFlowable(inline_to_rl(' '.join(bq), footnotes)))
            continue

        # ── Unordered list ─────────────────────────────────────────────────
        ul_m = re.match(r'^(\s*)[-*+]\s+(.*)', line)
        if ul_m:
            flush()
            depth = len(ul_m.group(1)) // 2
            # Accumulate CommonMark continuation lines (indented, not a new
            # block element) into the same bullet paragraph.
            bullet_lines = [ul_m.group(2)]
            while i + 1 < n:
                nxt = lines[i + 1]
                if (nxt and not re.match(r'^\s*[-*+]\s', nxt)
                        and not re.match(r'^\s*\d+\.\s', nxt)
                        and not re.match(r'^#{1,6}\s', nxt)
                        and not nxt.startswith('>')
                        and not nxt.startswith('```')
                        and nxt[:1] in (' ', '\t')):
                    bullet_lines.append(nxt.strip())
                    i += 1
                else:
                    break
            xml = inline_to_rl(' '.join(bullet_lines), footnotes)
            style = ParagraphStyle(f'Bullet{depth}', parent=STYLES['Bullet'],
                                    leftIndent=14 + depth * 16, bulletText='•')
            flowables.append(Paragraph(xml, style))
            i += 1; continue

        # ── Ordered list ───────────────────────────────────────────────────
        ol_m = re.match(r'^(\s*)(\d+)\.\s+(.*)', line)
        if ol_m:
            flush()
            # Accumulate CommonMark continuation lines (indented, not a new
            # block element) into the same list item paragraph.
            item_lines = [ol_m.group(3)]
            while i + 1 < n:
                nxt = lines[i + 1]
                if (nxt and not re.match(r'^\s*[-*+]\s', nxt)
                        and not re.match(r'^\s*\d+\.\s', nxt)
                        and not re.match(r'^#{1,6}\s', nxt)
                        and not nxt.startswith('>')
                        and not nxt.startswith('```')
                        and nxt[:1] in (' ', '\t')):
                    item_lines.append(nxt.strip())
                    i += 1
                else:
                    break
            xml = inline_to_rl(' '.join(item_lines), footnotes)
            style = ParagraphStyle('OL', parent=STYLES['Bullet'],
                                    leftIndent=20, bulletText=f'{ol_m.group(2)}.')
            flowables.append(Paragraph(xml, style))
            i += 1; continue

        # ── Empty line ─────────────────────────────────────────────────────
        if not line.strip():
            flush(); i += 1; continue

        # ── Regular paragraph ──────────────────────────────────────────────
        para_buf.append(line); i += 1

    flush()
    return flowables


def _heading_styles() -> set:
    return {STYLES.get(f'H{l}') for l in range(1, 7)} - {None}

def post_no_orphan_headings(flowables: list) -> list:
    """Keep each heading together with the first following non-Spacer flowable."""
    result: list = []
    hs = _heading_styles()
    i = 0
    while i < len(flowables):
        f = flowables[i]
        if isinstance(f, Paragraph) and f.style in hs:
            group = [f]
            j = i + 1
            while j < len(flowables) and isinstance(flowables[j], Spacer):
                group.append(flowables[j]); j += 1
            if j < len(flowables) and not isinstance(flowables[j], PageBreak):
                group.append(flowables[j]); j += 1
            result.append(KeepTogether(group))
            i = j
        else:
            result.append(f); i += 1
    return result

def post_keep_images(flowables: list) -> list:
    """Keep each HtmlImage with its preceding element and following caption."""
    result: list = []
    i = 0
    while i < len(flowables):
        f = flowables[i]
        if isinstance(f, HtmlImage):
            prev = result.pop() if result and not isinstance(result[-1], PageBreak) else None
            group = ([prev] if prev is not None else []) + [f]
            j = i + 1
            while j < len(flowables) and isinstance(flowables[j], Spacer):
                group.append(flowables[j]); j += 1
            if j < len(flowables) and not isinstance(flowables[j], (PageBreak, HtmlImage)):
                group.append(flowables[j]); j += 1
            result.append(KeepTogether(group))
            i = j
        else:
            result.append(f); i += 1
    return result


# ── Chapter loading ───────────────────────────────────────────────────────────
def load_chapters(locale_dir: Path) -> list[dict]:
    chapters = []
    for md_file in locale_dir.glob('*.md'):
        if md_file.name == 'index.md':
            continue
        text = md_file.read_text(encoding='utf-8')
        fm, body = parse_frontmatter(text)
        date_raw = fm.get('date', '9999-99-99')
        # PyYAML parses YYYY-MM-DD values as datetime.date objects.
        # Use isoformat() so sorting is always string-on-string and never
        # raises TypeError (datetime.date vs str comparison in Python 3).
        date = date_raw.isoformat() if hasattr(date_raw, 'isoformat') else str(date_raw)
        desc = fm.get('description', '') or ''
        if isinstance(desc, list):
            desc = ' '.join(str(x) for x in desc)
        h1_m = re.search(r'^#\s+(.*)', body, re.MULTILINE)
        title = h1_m.group(1).strip() if h1_m else md_file.stem
        # Remove the first H1 heading from the body: it's already rendered
        # explicitly as the chapter title above the content, so keeping it
        # would produce a visible duplicate on the first page of every chapter.
        if h1_m:
            body = body[:h1_m.start()] + body[h1_m.end():]
        chapters.append(dict(date=date, title=title, description=str(desc).strip(), body=body))
    chapters.sort(key=lambda c: c['date'])
    return chapters


# ── PDF document ──────────────────────────────────────────────────────────────
PRE_CHAPTER_PAGES = 2   # cover + ToC (not numbered)

class TrackingDoc(BaseDocTemplate):
    def __init__(self, path, **kw):
        super().__init__(path, **kw)
        self.chapter_page_map: dict[int, int] = {}
        self._numbering_started = False
        self._pre_chapter_pages = PRE_CHAPTER_PAGES

    def afterFlowable(self, flowable):
        if isinstance(flowable, ChapterMarker):
            self._numbering_started = True
            self.chapter_page_map[flowable.chapter_num] = self.page - self._pre_chapter_pages


def _make_templates(doc) -> list:
    fc = Frame(MARGIN_L, MARGIN_B, CONTENT_W, CONTENT_H, id='cover')
    ft = Frame(MARGIN_L, MARGIN_B, CONTENT_W, CONTENT_H, id='toc')
    fh = Frame(MARGIN_L, MARGIN_B, CONTENT_W, CONTENT_H, id='chapter')

    def on_cover(canvas, doc):
        canvas.saveState()
        # Full dark background — title and author use white text
        canvas.setFillColor(colors.HexColor('#1a1a2e'))
        canvas.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
        # Accent bars (slightly lighter shade) at top and bottom
        canvas.setFillColor(colors.HexColor('#16213e'))
        canvas.rect(0, PAGE_H - 80, PAGE_W, 80, fill=1, stroke=0)
        canvas.rect(0, 0, PAGE_W, 80, fill=1, stroke=0)
        canvas.restoreState()

    def on_chapter(canvas, doc):
        if not doc._numbering_started:
            return
        vp = doc.page - doc._pre_chapter_pages
        canvas.saveState()
        canvas.setFont('NotoSans', 9)
        canvas.setFillColor(colors.HexColor('#888888'))
        canvas.drawRightString(PAGE_W - MARGIN_R, MARGIN_B * 0.4, str(vp))
        canvas.restoreState()

    return [
        PageTemplate(id='Cover',   frames=[fc], onPage=on_cover),
        PageTemplate(id='TOC',     frames=[ft], onPage=lambda c, d: None),
        PageTemplate(id='Chapter', frames=[fh], onPage=on_chapter),
    ]


def _cover(title: str, author: str) -> list:
    return [
        NextPageTemplate('Cover'),
        Spacer(1, 120),
        Paragraph(title,  STYLES['CoverTitle']),
        Spacer(1, 20),
        Paragraph(author, STYLES['CoverAuthor']),
        NextPageTemplate('TOC'),
        PageBreak(),
    ]

def _toc(chapters: list, chapter_label: str, toc_title: str, toc_pages: dict) -> list:
    story = [Paragraph(toc_title, STYLES['ToCTitle']), Spacer(1, 10)]
    for idx, ch in enumerate(chapters, 1):
        story.append(ToCEntry(
            chapter_num=idx,
            chapter_label=chapter_label,
            title=ch['title'],
            page_num=toc_pages.get(idx, '—'),
            bold_font='NotoSans-Bold',
            reg_font='NotoSans',
        ))
        story.append(Spacer(1, 4))
    story += [NextPageTemplate('Chapter'), PageBreak()]
    return story

def _chapters(chapters: list, chapter_label: str) -> list:
    story = []
    for idx, ch in enumerate(chapters, 1):
        story.append(ChapterMarker(idx, ch['title']))
        # "Chapter N" super-label (small, grey)
        story.append(Paragraph(
            f'{chapter_label} {idx}',
            STYLES['ChapterLabel'],
        ))
        # Chapter title — same leftIndent=0 as the label above
        story.append(Paragraph(escape_xml(ch['title']), STYLES['H1']))
        # Subtitle — same leftIndent=0
        if ch['description']:
            story.append(Paragraph(
                f'<i>{escape_xml(ch["description"])}</i>',
                STYLES['ChapterSubtitle'],
            ))
        story.append(Spacer(1, 6))

        footnotes: list = []
        fls = md_to_flowables(ch['body'], footnotes)
        fls = post_no_orphan_headings(fls)
        fls = post_keep_images(fls)
        story.extend(fls)

        if footnotes:
            story.append(HRFlowable(width='40%', thickness=0.5,
                                     color=colors.grey, spaceAfter=4))
            for ref_n, url in enumerate(footnotes, 1):
                story.append(Paragraph(f'[{ref_n}] {escape_xml(url)}', STYLES['Footnote']))

        if idx < len(chapters):
            story.append(PageBreak())
    return story


def _build(path, book_title, author, chapters, chapter_label, toc_title, toc_pages):
    doc = TrackingDoc(
        str(path), pagesize=A4,
        leftMargin=MARGIN_L, rightMargin=MARGIN_R,
        topMargin=MARGIN_T,  bottomMargin=MARGIN_B,
    )
    doc.addPageTemplates(_make_templates(doc))
    story = (
        _cover(book_title, author)
        + _toc(chapters, chapter_label, toc_title, toc_pages)
        + _chapters(chapters, chapter_label)
    )
    doc.title  = book_title
    doc.author = author
    doc.build(story)
    return doc


def compress(src: str, dst: str) -> bool:
    """Compress PDF with Ghostscript; fall back to pikepdf if gs is absent."""
    # Try Ghostscript first (best compression, /ebook profile)
    try:
        r = subprocess.run(
            ['gs', '-sDEVICE=pdfwrite', '-dCompatibilityLevel=1.4',
             '-dPDFSETTINGS=/ebook', '-dNOPAUSE', '-dQUIET', '-dBATCH',
             f'-sOutputFile={dst}', src],
            capture_output=True,
        )
        if r.returncode == 0 and Path(dst).stat().st_size > 0:
            return True
        print(f"  Ghostscript failed (rc={r.returncode}): {r.stderr.decode(errors='replace').strip()}")
    except FileNotFoundError:
        pass

    # Fallback: pikepdf lossless recompression
    try:
        import pikepdf
        with pikepdf.open(src) as pdf:
            pdf.save(dst, compress_streams=True, recompress_flate=True,
                     object_stream_mode=pikepdf.ObjectStreamMode.generate)
        if Path(dst).stat().st_size > 0:
            print("  (compressed with pikepdf)")
            return True
    except Exception as e:
        print(f"  pikepdf compression failed: {e}")

    return False


def generate(locale: str, locale_dir: Path, cfg: dict) -> Path:
    print(f"\n── {locale} ──")
    chapters = load_chapters(locale_dir)
    for ch in chapters:
        print(f"  [{ch['date']}] {ch['title']}")

    title  = cfg['title']
    author = 'Igor Casanova'
    label  = cfg['chapter_label']
    toc_t  = cfg['toc_title']

    # Pass 1: dummy build to collect page numbers
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
        p1 = f.name
    doc1 = _build(p1, title, author, chapters, label, toc_t, {})
    toc_pages = doc1.chapter_page_map
    print(f"  ToC pages: {toc_pages}")

    # Pass 2: final build with correct page numbers
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
        p2 = f.name
    _build(p2, title, author, chapters, label, toc_t, toc_pages)

    out = OUTPUT_DIR / f"ocarina-{locale.lower()}.pdf"
    if compress(p2, str(out)):
        print(f"  → {out} (compressed)")
    else:
        import shutil
        shutil.copy(p2, out)
        print(f"  → {out} (uncompressed fallback)")

    for p in (p1, p2):
        try: os.unlink(p)
        except: pass

    return out


# ── Entry point ───────────────────────────────────────────────────────────────
LOCALES = {
    'EN': dict(dir=DOCS_DIR, title='The Ocarina Holy Book',
               chapter_label='Chapter', toc_title='Table of content'),
    'FR': dict(dir=DOCS_DIR / 'fr', title="Le livre sacré d'Ocarina",
               chapter_label='Chapitre', toc_title='Sommaire'),
}

if __name__ == '__main__':
    outputs = []
    for locale, cfg in LOCALES.items():
        out = generate(locale, cfg['dir'], cfg)
        outputs.append(out)
    print("\n── Done ──")
    for o in outputs:
        print(f"  {o}")
