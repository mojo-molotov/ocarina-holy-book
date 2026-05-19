# Ocarina PDF Generator

## What this is

A system that turns a VitePress `docs/` folder (Markdown + images) into three polished A4 PDFs — one English, one French, one Russian. The system is
two files: this prompt (the spec) and `script.py` (the implementation). They are designed to be used together in an agentic environment.

## How to run it

### Inputs you receive

1. **`docs.zip`** — a ZIP archive containing a VitePress `docs/` folder with `.md` files and images.
2. **Font files** — a set of Noto `.ttf` files. They are provided as a convenience to avoid download issues; they are ordinary fonts, nothing special.
3. **`prompt.md`** — this file.
4. **`script.py`** — the Python script.

### What you do

1. **Install dependencies:**

   ```bash
   pip install reportlab pillow pyyaml pygments pikepdf numpy arabic-reshaper python-bidi fonttools cairosvg black
   apt-get install -y ghostscript   # optional, pikepdf is the fallback compressor
   ```

   `arabic-reshaper` and `python-bidi` are **required**, not optional — they are imported at module level. `black` is optional but recommended (Python
   code blocks are reformatted with `black --line-length 75` before rendering; if absent, the original source is kept).

2. **Set up the workspace:**
   - Extract `docs.zip` to a working directory (e.g. `/home/claude/docs`).
   - Copy all font files to a single directory (e.g. `/home/claude/fonts`).

3. **Adapt `script.py` before running it** — all user-tunable settings are grouped at the top of the file in a single `CONFIG` block:

   ```python
   # ╔════════════════════════════════════════════════════════════════════════════╗
   # ║  CONFIG — adapt these to your environment, then run `python3 script.py`    ║
   # ╚════════════════════════════════════════════════════════════════════════════╝
   DOCS_DIR    = Path("/home/claude/docs")        # ← where you extracted the ZIP
   FONTS_DIR   = Path("/home/claude/fonts")       # ← where you put the font files
   OUTPUT_DIR  = Path("/mnt/user-data/outputs")
   PUBLIC_DIR  = DOCS_DIR / "public"              # images referenced by /assets/...
   # … page layout (margins, A4) and _CODE_WRAP_COL follow.
   ```

   The font filenames in `register_fonts()` must match what was provided. The emoji font is auto-discovered via
   `FONTS_DIR.glob("NotoColorEmoji*.ttf")`, so any of `NotoColorEmoji.ttf`, `NotoColorEmoji-Regular.ttf`, `NotoColorEmoji-flat.ttf` will be picked up.
   This 30-second pre-flight check is the whole point of providing this prompt alongside the script: you adapt the code to the environment, rather
   than the code growing runtime hacks to guess its environment.

4. **Run:**
   ```bash
   python3 script.py
   ```

### Outputs

Three compressed PDFs in `OUTPUT_DIR`:

- `ocarina-en.pdf` — _The Ocarina Holy Book_
- `ocarina-fr.pdf` — _Le livre sacré d'Ocarina_
- `ocarina-ru.pdf` — _Священная книга Ocarina_

---

## Architecture overview

The script is a single file (~1750 lines), by design. Here is what it does, in order:

### 1. Font registration

Nine font files are registered with ReportLab. The NotoSans family (Regular/Bold/Italic/BoldItalic) handles all prose. NotoMono handles code blocks.
NotoArabic handles Arabic script. NotoSymbols2 and NotoMath are fallbacks for symbols not covered by NotoSans.

NotoColorEmoji is loaded separately via fontTools for color emoji rasterization (see §3).

For coverage lookups, three cmaps (NotoSans, NotoSymbols2, NotoMath) are loaded **once at boot via fontTools** as plain `set[int]` of codepoints — no
redundant ReportLab `TTFont` parses just for character coverage.

### 2. Character routing

Every character in the document goes through a simple decision:

**Can a text font render it? → Use that font. End.**

Specifically:

- `_ns_cmap` (NotoSans coverage) is checked first. If the codepoint is there, it's plain text — `drawString` or `<font>` tag, nothing else.
- `fallback_font_for(cp)` (memoized via `lru_cache`) checks NotoSymbols2 then NotoMath. If either covers it, that font is used as text. Characters
  like → (U+2192), ≤ (U+2264), ≥, ≠, ± are rendered this way — they are **text**, not emoji, and are rendered as vector glyphs in the correct color
  and size.
- Only if _no_ text font covers a codepoint AND it falls in an emoji range (`_is_emoji_cp`) does it go through the emoji PNG pipeline.

One exception: **VS16 promotion**. Some codepoints are in NotoSans (e.g. ℹ U+2139) but when followed by U+FE0F they should render as color emoji (ℹ️).
The script checks for this before the regular text path.

### 3. Color emoji rendering

NotoColorEmoji is a COLR v1 / SVG font. **Pillow cannot render it** (Pillow only supports CBDT/CBLC bitmap color fonts —
`draw.text(..., embedded_color=True)` produces empty images for this font).

The script uses fontTools + cairosvg instead:

1. Parse the font's SVG table with `fontTools.ttLib.TTFont`.
2. For a requested codepoint, look up the glyph ID via cmap (and cmap14 for VS16 sequences).
3. Find the SVG document covering that glyph ID, extract `<g id="glyphN">…</g>` via balanced-tag scan.
4. Prepend the shared `<defs>` block (needed for `xlink:href` gradient references).
5. Wrap in `<svg viewBox="0 -920 1280 1140">…</svg>` and render with `cairosvg.svg2png()` at **512×512 px**.

The viewBox `"0 -920 1280 1140"` matches the actual coordinate space of NotoColorEmoji glyphs (Y-down, negative = above baseline). **No `scale(1,-1)`
flip** — the SVG coordinates are already in screen convention.

Emoji are displayed at **13×13 pt** in inline text (valign=-2) and at `fontSize * 1.4` in code blocks. The high rasterization resolution (512 px)
ensures they remain crisp at normal zoom levels and in print, even though they are bitmap images embedded in a vector PDF.

The PNG cache is persistent across builds: it lives in `~/.cache/ocarina-pdf/emoji/` (not `/tmp`), so subsequent runs reuse already-rasterized glyphs.

Outline rasterization (`render_outline_png`) exists as a last resort for supplementary-plane symbols (cp ≥ U+10000) where ReportLab's `drawString` has
a glyph-index encoding bug. For BMP symbols, `drawString` with the fallback font works correctly.

### 4. Markdown parsing

A line-by-line state machine (no external Markdown library) that produces ReportLab `Flowable` objects. Handles:

- Fenced code blocks → `CodeBlock`
- Headings (H1–H6) → styled `Paragraph`
- Blockquotes → `_BlockquoteFlowable` (with left accent bar, supports page-splitting)
- Lists (ordered/unordered, with CommonMark continuation lines; both space- and tab-indented continuations are accepted)
- Images → `HtmlImage` (centered, max 300pt height; missing images log `[warn] image not found: …` at parse time, not silently)
- HTML blocks (`<p align="center">`, author signatures, etc.)
- Inline: bold, italic, code spans, links (with footnotes), autolinks

### 5. Inline parser (`inline_to_rl`)

Character-by-character loop that converts Markdown inline syntax to ReportLab Paragraph XML. The priority order matters:

1. Code spans (`` ` ``)
2. Bold-italic (`***`), bold (`**`)
3. Italic `_` (snake_case-safe) and `*`
4. Autolinks (`<https://…>`) and links (`[text](url)`)
5. VS16 strip (standalone variation selectors)
6. Arabic runs (reshaped via `arabic_reshaper` + `python-bidi`, then visually reversed for LTR display in a ReportLab Paragraph)
7. VS16 emoji promotion (NotoSans codepoint + FE0F → try color emoji)
8. Symbol/emoji runs (fallback font or emoji PNG)
9. Plain characters

`escape_xml` decodes HTML entities, normalizes NBSP, and escapes `&`, `<`, `>`, `"`, `'` for ReportLab's XML parser.

### 6. Code blocks

`CodeBlock` is a custom `Flowable` with:

- Pygments syntax highlighting (GitHub light theme)
- Pre-processing pipeline for Python: Black reformatting (`--line-length 75`) → comment wrapping. Black is gated strictly on
  `lang in ('python', 'py')`; blocks tagged `bash`, `text`, or untagged skip Black but still go through comment wrapping (any line over 75 cols
  starting with `#` is reflowed).
- Per-character font fallback in `draw()`: NotoMono for ASCII, NotoMath/NotoSymbols2 for BMP symbols (as text, via `drawString`), emoji PNGs for
  actual emoji, outline PNGs only for supplementary-plane symbols
- `split()` for pagination (avoids `LayoutError`)

### 7. Book structure

- **Cover**: dark background, white title/author. The author name defaults to `Igor Casanova`; a locale may override it via the `author` key in
  `LOCALES` (the Russian book uses the Cyrillic `Игорь Казанова`, matching the in-page signatures).
- **Table of Contents**: custom `ToCEntry` flowables with right-aligned page numbers
- **Chapters**: ordered by frontmatter `date` field, each starting with a `ChapterMarker` sentinel

Page numbering starts at 1 on the first chapter page. Cover and ToC are not numbered.

### 8. Two-pass build

The ToC needs page numbers that are only known after layout. Pass 1 builds with placeholder page numbers; `TrackingDoc.afterFlowable()` records the
actual page for each `ChapterMarker`. Pass 2 rebuilds with correct numbers.

### 9. Compression

Ghostscript (`/ebook` profile) → pikepdf (lossless recompression) → uncompressed copy. Each step is a fallback for the previous, with explicit logging
of failures (return code + stderr).

---

## Known constraints and pitfalls

These are things that have caused bugs in past iterations. They are documented here so they are not re-introduced.

### Emoji / symbol rendering

- **Pillow cannot render NotoColorEmoji.** Do not use `ImageFont.truetype` + `embedded_color=True` for this font. It produces empty images.
- **NotoColorEmoji SVG coordinates are Y-down.** `viewBox="0 -920 1280 1140"`, no `scale(1,-1)`. Adding a Y-flip puts the glyph in the bottom corner.
- **→ and ≤ are text, not emoji.** They are covered by NotoMath. Routing them through the emoji pipeline produces ugly small PNG artefacts. The
  `_ns_cmap` / `fallback_font_for` check must happen before `_is_emoji_cp`.
- **BMP symbols in code blocks use `drawString`, not PNG.** ReportLab's glyph-index bug only affects supplementary-plane characters (cp ≥ 0x10000).
  For BMP symbols like ≤, `drawString` with the fallback font works correctly and preserves the Pygments syntax color.
- **Emoji vertical alignment in code blocks.** `drawString` puts text on the baseline at `y`; `drawImage` puts the image's _bottom_ at the given `y`.
  A naive `drawImage(png, x, y, em, em)` puts the emoji's bottom on the baseline, which makes it sit visually high above the text. The image must be
  lowered so that its center sits on the text's x-height. For NotoMono at `_FONT_SIZE = 8` (so `em = 11.2`), the right offset is `y - 3`. If you
  change `_FONT_SIZE`, retune that offset — it's not perfectly linear because NotoColorEmoji has some padding inside its viewBox.
- **Do not substitute emoji with ASCII placeholders.** Emoji in code blocks are rendered via the same per-character fallback pipeline (color PNG at
  512 px or fallback font). Replacing them with text like `[ok]` or `[book]` loses information and looks worse.

### Date sorting

PyYAML parses `YYYY-MM-DD` as `datetime.date`, not `str`. Use `.isoformat()` before sorting to avoid `TypeError`.

### Arabic text

`arabic_reshaper` + `python-bidi` are **required dependencies**, imported at module level. The script will `ImportError` at boot if they are missing.
There is no built-in fallback — install the pip packages.

### Blockquote pagination

`_BlockquoteFlowable.split()` must be implemented. Without it, a blockquote spanning a full page raises `LayoutError`.

### `\x00BR\x00` sentinel length

The hard-break sentinel `'\x00BR\x00'` is **4 characters** (`\x00` + `B` + `R` + `\x00`). The check in `inline_to_rl` must use `text[i:i+4]` and
`i += 4`. Using `i:i+7` (or any value ≠ 4) means the slice never matches, the sentinel is emitted as raw text, the null bytes are stripped by
ReportLab, and a literal `BR` appears in the rendered PDF.

### Bold/italic spanning hard-break lines

A Markdown paragraph like:

```
**Opening sentence that is long enough to need a hard-break.
Closing sentence.**
```

has its closing `**` on a different physical line from the opening `**`. The trailing `  ` on the first line is a CommonMark hard-break. If `flush()`
splits the paragraph into per-segment strings (one per `<br/>`) and calls `inline_to_rl` separately on each segment, the opening `**` and closing `**`
will never be in the same call — neither is bold. The fix: `join_paragraph_lines` must return a **single string** with `\x00BR\x00` sentinels (not a
list of strings), and `flush()` must call `inline_to_rl` on the whole joined string in a single pass. `inline_to_rl` recognizes `\x00BR\x00` and emits
`<br/>` directly.

### `<br/>` in HTML blocks

`_strip_tags` originally used a plain `re.sub(r'<[^>]+>', '', s)` which removes **all** HTML tags, including `<br/>`. This caused `<br/>` tags inside
`<p align="center">` blocks to be silently dropped. Fix: `_strip_tags` must replace `<br/>` / `<br>` with `\x00BR\x00` **before** stripping other
tags. Since `inline_to_rl` already converts `\x00BR\x00` to `<br/>`, the line break is preserved end-to-end.

### `<strong>` and `<em>` in HTML blocks

Same root cause as `<br/>` above. `_strip_tags` stripped `<strong>` and `<em>` tags along with everything else, so bold and italic formatting inside
`<p align="center"><strong>…</strong></p>` blocks was lost. Fix: `_strip_tags` must convert `<strong>…</strong>` → `**…**` and `<em>…</em>` → `_…_`
before stripping remaining tags, so `inline_to_rl` receives Markdown markup it can render.

### `_flush_seg` in `CodeBlock.draw()`

Uses `nonlocal x`. The older `return x or old_x` pattern fails when `x == 0.0` (falsy).

### Ghostscript error logging

Non-zero return codes and stderr are logged. Earlier versions silently swallowed failures.

### Font filename variation

NotoColorEmoji ships under several names depending on the source (`NotoColorEmoji.ttf` from apt, `NotoColorEmoji-Regular.ttf` from upstream, etc.).
The script auto-discovers via `FONTS_DIR.glob("NotoColorEmoji*.ttf")`. The other fonts are looked up by exact filename in `register_fonts()` — if your
files are named differently, edit that one function.
