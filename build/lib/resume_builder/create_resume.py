#!/usr/bin/env python3
"""
create_resume.py - build Resume.docx and Resume.pdf (2 pages, A4, two-column) from one TXT file.

The TXT file is the single source of truth. Wording, order, dates, contact
details, bullets and skills are never changed; only layout/styling is applied:
  * header (name, headline, contact line) across the top
  * first section (Experience) in a wide left column
  * every other section (Summary, Skills, Key Achievements, ...) in a right sidebar
  * skills shown as a clean two-column grid with thin grey underlines,
    "======" markers shown as a rule under headings

Install:
    pip install python-docx reportlab pypdf

Run:
    python create_resume.py                        # uses "New Resume (2) (1).txt"
    python create_resume.py "path/to/resume.txt"   # any TXT in the same format
    python create_resume.py resume.txt -o out_dir  # choose output folder
    python create_resume.py resume.txt --verify    # also check output text == TXT

Expected TXT format:
    line 1 = name, line 2 = headline, next lines = contact details
    "Heading" followed by a "======" line = section heading
    " - text" = bullet;  blank line = block separator
    job block = title / company / "MM/YYYY - MM/YYYY|Present" / location
"""
import argparse
import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas
from reportlab.platypus import Frame, Paragraph, Table, TableStyle

# ---- layout constants ------------------------------------------------------
FONT, FONT_B = "Helvetica", "Helvetica-Bold"
DOCX_FONT = "Arial"
BODY = 9.1                       # body size (pt)
ACCENT, DARK, GREY, CHIP = "1A5FB4", "14213D", "555555", "E8EEF7"
MX, MT, MB = 34, 30, 30          # page margins (pt): left/right, top, bottom
PAGE_W, PAGE_H = A4
LEFT_W, GUTTER = 318, 18         # left column width / gap (pt)
RIGHT_W = PAGE_W - 2 * MX - LEFT_W - GUTTER
HDR_H = 74
GAP = " " * 6               # spacing between meta items (no visible characters)

RULE_RE = re.compile(r"^=+\s*$")
BULLET_RE = re.compile(r"^\s*-\s+(.*)$")
# match http(s)://..., www...., and bare domains like linkedin.com/in/foo
URL_RE = re.compile(r"^(?:https?://)?(?:www\.)?[\w-]+(?:\.[\w-]+)+(?:/\S*)?$",
                    re.IGNORECASE)
EMAIL_RE = re.compile(r"^[\w.+-]+@[\w-]+(?:\.[\w-]+)+$")
DATE_RE = re.compile(r"^\d{2}/\d{4}\s*-\s*(\d{2}/\d{4}|Present)$")


# --------------------------------------------------------------------------
# Parsing
# --------------------------------------------------------------------------
def _raw_items(txt_path):
    lines = Path(txt_path).read_text(encoding="utf-8-sig").splitlines()
    items, in_header, hidx, block_start = [], True, 0, True
    n = len(lines)
    for i, raw in enumerate(lines):
        line = raw.rstrip()
        nxt = lines[i + 1].rstrip() if i + 1 < n else ""
        if RULE_RE.match(line):
            continue
        if not line.strip():
            block_start = True
            continue
        if RULE_RE.match(nxt):
            items.append(("heading", line.strip()))
            in_header, block_start = False, True
            continue
        if in_header:
            kind = ("name", "headline")[hidx] if hidx < 2 else "contact"
            items.append((kind, line.strip()))
            hidx += 1
            continue
        m = BULLET_RE.match(line)
        if m:
            items.append(("bullet", m.group(1).strip()))
            block_start = False
            continue
        multi = bool(nxt.strip()) and not RULE_RE.match(nxt)
        items.append(("first" if block_start and multi else "line", line.strip()))
        block_start = False
    return items


def parse(txt_path):
    """-> (header, main_blocks, side_blocks).
    header: dict(name, headline, contacts[]).
    blocks: heading, job(title,company,dates,loc), group(title,[skills]),
            pairs([(title,text)]), bullet, line."""
    raw = _raw_items(txt_path)
    header = {"name": "", "headline": "", "contacts": []}
    blocks, i, n = [], 0, len(raw)
    while i < n:
        kind, text = raw[i]
        if kind in ("name", "headline"):
            header[kind] = text
        elif kind == "contact":
            header["contacts"].append(text)
        elif kind == "first":
            four = raw[i:i + 4]
            if (len(four) == 4 and all(k == "line" for k, _ in four[1:])
                    and DATE_RE.match(four[2][1])):
                blocks.append(("job", four[0][1], four[1][1], four[2][1], four[3][1]))
                i += 4
                continue
            if i + 1 < n and raw[i + 1][0] == "line":
                pairs = []
                while i + 1 < n and raw[i][0] == "first" and raw[i + 1][0] == "line":
                    pairs.append((raw[i][1], raw[i + 1][1]))
                    i += 2
                blocks.append(("pairs", pairs))
                continue
            if i + 1 < n and raw[i + 1][0] == "bullet":
                j, items = i + 1, []
                while j < n and raw[j][0] == "bullet":
                    items.append(raw[j][1])
                    j += 1
                blocks.append(("group", text, items))
                i = j
                continue
            blocks.append(("line", text))
        else:
            blocks.append((kind, text))
        i += 1
    # first section (e.g. Experience) -> main column, the rest -> sidebar
    heads = [k for k, b in enumerate(blocks) if b[0] == "heading"]
    split = heads[1] if len(heads) > 1 else len(blocks)
    return header, blocks[:split], blocks[split:]


# --------------------------------------------------------------------------
# PDF
# --------------------------------------------------------------------------
def _styles():
    base = ParagraphStyle("base", fontName=FONT, fontSize=BODY, leading=BODY * 1.24,
                          textColor="#" + DARK)
    P = lambda name, **kw: ParagraphStyle(name, parent=base, **kw)
    return {
        "name": P("name", fontName=FONT_B, fontSize=27, leading=31),
        "headline": P("headline", fontName=FONT_B, fontSize=10, leading=13, textColor="#" + ACCENT),
        "contacts": P("contacts", fontSize=8, leading=11),
        "heading": P("heading", fontName=FONT_B, fontSize=12, leading=15, spaceBefore=11),
        "title": P("title", fontName=FONT_B, fontSize=10, leading=12.5, spaceBefore=8),
        "company": P("company", fontName=FONT_B, fontSize=BODY + 0.4, textColor="#" + ACCENT),
        "meta": P("meta", fontSize=8, leading=10.5, textColor="#" + GREY, spaceAfter=2.5),
        "bullet": P("bullet", leftIndent=10, bulletIndent=0, spaceAfter=2),
        "body": P("body", spaceAfter=2),
        "group": P("group", fontName=FONT_B, textColor="#" + ACCENT, spaceBefore=4, spaceAfter=2),
        "skill": P("skill", fontSize=8.2, leading=10.5, spaceAfter=0),
        "pairt": P("pairt", fontName=FONT_B, spaceBefore=5),
        "paird": P("paird", spaceAfter=2),
    }


def _link(text, size=None, width=None):
    t = escape(text)
    if EMAIL_RE.match(text):
        t = f'<a href="mailto:{t}" color="#{ACCENT}">{t}</a>'
    elif URL_RE.match(text):
        href = text if text.lower().startswith(("http://", "https://")) else "https://" + text
        t = f'<a href="{escape(href)}" color="#{ACCENT}">{t}</a>'
        if size and width:  # shrink long URLs so they never overflow the column
            w = stringWidth(text, FONT, size)
            if w > width:
                t = f'<font size="{size * width / w:.2f}">{t}</font>'
    return t


def _stack(parts, width):
    """Unbreakable unit: parts stacked in a zero-padding one-column table."""
    if len(parts) == 1:
        return parts[0]
    t = Table([[p] for p in parts], colWidths=[width])
    style = [("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
             ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]
    style.append(("TOPPADDING", (0, 0), (0, 0), parts[0].style.spaceBefore))
    if getattr(parts[0], "_rule", False):  # section heading: accent rule underneath
        style += [("LINEBELOW", (0, 0), (0, 0), 0.9, "#" + ACCENT), ("BOTTOMPADDING", (0, 0), (0, 0), 2),
                  ("BOTTOMPADDING", (0, 1), (0, 1), 0), ("TOPPADDING", (0, 1), (0, 1), 3)]
    t.setStyle(TableStyle(style))
    return t


def _units(blocks, S, width):
    """Blocks -> list of unbreakable units (each a list of flowables)."""
    units, pending, i = [], [], 0

    def put(parts):
        nonlocal pending
        units.append(pending + parts)
        pending = []

    while i < len(blocks):
        b = blocks[i]
        k = b[0]
        if k == "heading":
            hp = Paragraph(escape(b[1]), S["heading"])
            hp._rule = True
            pending = [hp]
        elif k == "job":
            _, title, company, dates, loc = b
            parts = [Paragraph(escape(title), S["title"]),
                     Paragraph(escape(company), S["company"]),
                     Paragraph(escape(dates) + GAP + escape(loc), S["meta"])]
            if i + 1 < len(blocks) and blocks[i + 1][0] == "bullet":
                parts.append(Paragraph(escape(blocks[i + 1][1]), S["bullet"], bulletText="•"))
                i += 1
            put(parts)
        elif k == "bullet":
            put([Paragraph(escape(b[1]), S["bullet"], bulletText="•")])
        elif k == "group":
            title = Paragraph(escape(b[1]), S["group"])
            items = b[2]
            if not items:
                put([title])
                i += 1
                continue
            gutter = 8
            col_w = width / 2.0
            rows = []
            for j in range(0, len(items), 2):
                left = Paragraph(escape(items[j]), S["skill"])
                right = (Paragraph(escape(items[j + 1]), S["skill"])
                         if j + 1 < len(items) else Paragraph("", S["skill"]))
                rows.append([left, right])
            skill_tbl = Table(rows, colWidths=[col_w, col_w])
            style = [
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (0, -1), gutter),   # gutter on left column
                ("RIGHTPADDING", (1, 0), (1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 1),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
            for j in range(len(items)):                      # underline filled cells only
                r, c = divmod(j, 2)
                style.append(("LINEBELOW", (c, r), (c, r), 0.5, "#" + GREY))
            skill_tbl.setStyle(TableStyle(style))
            put([title, skill_tbl])
        elif k == "pairs":
            for t, d in b[1]:
                put([Paragraph(escape(t), S["pairt"]),
                     Paragraph(_link(d, 8, width), S["paird"])])
        else:  # line
            put([Paragraph(escape(b[1]), S["body"])])
        i += 1
    return units


def build_pdf(header, main, side, out_path):
    S = _styles()
    full_w = PAGE_W - 2 * MX
    hdr = [Paragraph(escape(header["name"]), S["name"]),
           Paragraph(escape(header["headline"]), S["headline"]),
           Paragraph(GAP.join(_link(c) for c in header["contacts"]), S["contacts"])]
    left = [_stack(u, LEFT_W) for u in _units(main, S, LEFT_W)]
    right = [_stack(u, RIGHT_W) for u in _units(side, S, RIGHT_W)]

    c = canvas.Canvas(str(out_path), pagesize=A4)
    c.setTitle("Resume")
    pad = dict(leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0, showBoundary=0)
    page = 0
    while (left or right) and page < 6:
        top = PAGE_H - MT
        if page == 0:
            Frame(MX, top - HDR_H, full_w, HDR_H, **pad).addFromList(hdr, c)
            top -= HDR_H + 2
        h = top - MB
        Frame(MX, MB, LEFT_W, h, **pad).addFromList(left, c)
        Frame(MX + LEFT_W + GUTTER, MB, RIGHT_W, h, **pad).addFromList(right, c)
        c.showPage()
        page += 1
    c.save()
    return not (left or right) and page <= 2


# --------------------------------------------------------------------------
# DOCX
# --------------------------------------------------------------------------
def _font(style, size, bold=False, color="000000"):
    style.font.name, style.font.size, style.font.bold = DOCX_FONT, Pt(size), bold
    style.font.color.rgb = RGBColor.from_string(color)
    rpr = style.element.get_or_add_rPr()
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = OxmlElement("w:rFonts")
        rpr.append(rf)
    for a in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rf.set(qn(a), DOCX_FONT)


def _border_bottom(p, color=ACCENT, sz="8", space="1"):
    pb = OxmlElement("w:pBdr")
    b = OxmlElement("w:bottom")
    for k, v in (("val", "single"), ("sz", sz), ("space", space), ("color", color)):
        b.set(qn(f"w:{k}"), v)
    pb.append(b)
    p._p.get_or_add_pPr().append(pb)


def _shade(run, fill):
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    run._r.get_or_add_rPr().append(shd)


def _run(p, text, bold=False, color=None, size=None):
    r = p.add_run(text)
    r.bold = bold
    if color:
        r.font.color.rgb = RGBColor.from_string(color)
    if size:
        r.font.size = Pt(size)
    return r


def _fill(container, blocks, width):
    """Render blocks into a docx body or table cell."""
    i = 0
    while i < len(blocks):
        b = blocks[i]
        k = b[0]
        if k == "heading":
            p = container.add_paragraph(b[1], style="Heading 1")
            _border_bottom(p)
        elif k == "job":
            _, title, company, dates, loc = b
            p = container.add_paragraph()
            _run(p, title, bold=True, size=10)
            p.paragraph_format.space_before = Pt(8)
            p.paragraph_format.keep_with_next = True
            p = container.add_paragraph()
            _run(p, company, bold=True, color=ACCENT)
            p.paragraph_format.keep_with_next = True
            p = container.add_paragraph()
            _run(p, dates + GAP + loc, color=GREY, size=8)
            p.paragraph_format.keep_with_next = True
        elif k == "bullet":
            container.add_paragraph(b[1], style="List Bullet")
        elif k == "group":
            p = container.add_paragraph()
            _run(p, b[1], bold=True, color=ACCENT)
            p.paragraph_format.space_before = Pt(4)
            p.paragraph_format.space_after = Pt(3)
            p.paragraph_format.keep_with_next = True
            items = b[2]
            if items:
                nrows = (len(items) + 1) // 2
                tbl = container.add_table(rows=nrows, cols=2)
                tbl.autofit = False
                tblPr = tbl._tbl.tblPr
                borders = OxmlElement("w:tblBorders")   # no table borders
                for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
                    e = OxmlElement(f"w:{edge}")
                    e.set(qn("w:val"), "none")
                    e.set(qn("w:sz"), "0")
                    e.set(qn("w:space"), "0")
                    e.set(qn("w:color"), "auto")
                    borders.append(e)
                tblPr.append(borders)
                lay = OxmlElement("w:tblLayout")
                lay.set(qn("w:type"), "fixed")
                tblPr.append(lay)
                mar = OxmlElement("w:tblCellMar")
                for side_name in ("left", "right", "top", "bottom"):
                    e = OxmlElement(f"w:{side_name}")
                    e.set(qn("w:w"), "0")
                    e.set(qn("w:type"), "dxa")
                    mar.append(e)
                tblPr.append(mar)
                gutter_pt = 8
                col_w = width / 2.0
                for col in tbl.columns:
                    col.width = Pt(col_w)
                for row in tbl.rows:
                    for cell in row.cells:
                        cell.width = Pt(col_w)
                for idx, item in enumerate(items):
                    r, c = divmod(idx, 2)
                    cell = tbl.cell(r, c)
                    cp = cell.paragraphs[0]
                    _run(cp, item, size=8.2)
                    cp.paragraph_format.space_before = Pt(0)
                    cp.paragraph_format.space_after = Pt(2)
                    cp.paragraph_format.line_spacing = 1.0
                    _border_bottom(cp, color=GREY, sz="4", space="0")
                    if c == 0:  # gutter: right padding on the left cell
                        tcPr = cell._tc.get_or_add_tcPr()
                        tcMar = OxmlElement("w:tcMar")
                        rm = OxmlElement("w:right")
                        rm.set(qn("w:w"), str(int(gutter_pt * 20)))  # pt -> twips
                        rm.set(qn("w:type"), "dxa")
                        tcMar.append(rm)
                        tcPr.append(tcMar)
        elif k == "pairs":
            for t, d in b[1]:
                p = container.add_paragraph()
                _run(p, t, bold=True)
                p.paragraph_format.space_before = Pt(3)
                p.paragraph_format.keep_with_next = True
                p = container.add_paragraph()
                _run(p, d, size=8 if URL_RE.match(d) or EMAIL_RE.match(d) else None)
                p.paragraph_format.keep_together = True
        else:
            container.add_paragraph(b[1])
        i += 1


def build_docx(header, main, side, out_path):
    doc = Document()
    s = doc.sections[0]
    s.page_width, s.page_height = Pt(PAGE_W), Pt(PAGE_H)
    s.left_margin = s.right_margin = Pt(MX)
    s.top_margin, s.bottom_margin = Pt(MT), Pt(MB)

    n = doc.styles["Normal"]
    _font(n, BODY, color=DARK)
    n.paragraph_format.space_before, n.paragraph_format.space_after = Pt(0), Pt(1.5)
    n.paragraph_format.line_spacing = 1.08
    h1 = doc.styles["Heading 1"]
    _font(h1, 12, bold=True, color=DARK)
    h1.paragraph_format.space_before, h1.paragraph_format.space_after = Pt(11), Pt(3)
    h1.paragraph_format.keep_with_next = True
    bl = doc.styles["List Bullet"]
    _font(bl, BODY, color=DARK)
    bl.paragraph_format.space_after = Pt(2)
    bl.paragraph_format.left_indent = Pt(10)
    bl.paragraph_format.first_line_indent = Pt(-9)

    p = doc.add_paragraph()
    _run(p, header["name"], bold=True, size=27)
    p.paragraph_format.space_after = Pt(0)
    p = doc.add_paragraph()
    _run(p, header["headline"], bold=True, color=ACCENT, size=10)
    p.paragraph_format.space_after = Pt(2)
    p = doc.add_paragraph(GAP.join(header["contacts"]))
    for r in p.runs:
        r.font.size = Pt(8)
    p.paragraph_format.space_after = Pt(4)

    # layout table: left cell | gap | right cell (a row may break across pages)
    widths = [Pt(LEFT_W), Pt(GUTTER), Pt(RIGHT_W)]
    t = doc.add_table(rows=1, cols=3)
    t.alignment = WD_TABLE_ALIGNMENT.LEFT
    t.autofit = False
    tblPr = t._tbl.tblPr
    lay = OxmlElement("w:tblLayout")
    lay.set(qn("w:type"), "fixed")
    tblPr.append(lay)
    mar = OxmlElement("w:tblCellMar")
    for side_name in ("left", "right", "top", "bottom"):
        e = OxmlElement(f"w:{side_name}")
        e.set(qn("w:w"), "0")
        e.set(qn("w:type"), "dxa")
        mar.append(e)
    tblPr.append(mar)
    for cell, w in zip(t.rows[0].cells, widths):
        cell.width = w
    for col, w in zip(t.columns, widths):
        col.width = w
    for cell, blocks, w in ((t.rows[0].cells[0], main, LEFT_W),
                            (t.rows[0].cells[2], side, RIGHT_W)):
        _fill(cell, blocks, w)
        first = cell.paragraphs[0]  # remove the empty paragraph a new cell starts with
        if not first.text.strip():
            first._element.getparent().remove(first._element)
        cell.paragraphs[0].paragraph_format.keep_with_next = False
    doc.core_properties.title = "Resume"
    doc.save(out_path)


# --------------------------------------------------------------------------
# Verification
# --------------------------------------------------------------------------
def _expected_words(txt_path):
    out = []
    for raw in Path(txt_path).read_text(encoding="utf-8-sig").splitlines():
        s = raw.strip()
        if not s or RULE_RE.match(s):
            continue
        m = BULLET_RE.match(raw)
        out += (m.group(1) if m else s).split()
    return out


def _docx_words(path):
    body = Document(str(path)).element.body
    words = []
    for p in body.iter(qn("w:p")):  # document order, includes table cells
        words += "".join(t.text or "" for t in p.iter(qn("w:t"))).split()
    return words


def _expected_sections(txt_path):
    """Word lists: header, first section (main column), remaining sections (sidebar)."""
    lines = Path(txt_path).read_text(encoding="utf-8-sig").splitlines()
    parts, cur, heads = [[], [], []], 0, 0
    for i, raw in enumerate(lines):
        s = raw.strip()
        if not s or RULE_RE.match(s):
            continue
        nxt = lines[i + 1].strip() if i + 1 < len(lines) else ""
        if RULE_RE.match(nxt):
            heads += 1
            cur = 1 if heads == 1 else 2
        m = BULLET_RE.match(raw)
        parts[cur] += (m.group(1) if m else s).split()
    return parts


def _interleaves(stream, a, b):
    """True if `stream` is some interleaving of sequences a and b (order kept in each)."""
    if len(stream) != len(a) + len(b):
        return False
    reach = {0}  # i = words consumed from a, after k stream words (j = k - i from b)
    for k, w in enumerate(stream):
        nxt = set()
        for i in reach:
            j = k - i
            if i < len(a) and a[i] == w:
                nxt.add(i + 1)
            if j < len(b) and b[j] == w:
                nxt.add(i)
        if not nxt:
            return False
        reach = nxt
    return True


def _pdf_stream(path):
    from pypdf import PdfReader
    reader = PdfReader(str(path))
    text = "\n".join(p.extract_text() for p in reader.pages)
    return text.replace("\u2022", " ").replace("\x7f", " ").split(), len(reader.pages)


def verify(txt_path, docx_path, pdf_path):
    hdr, main, side = _expected_sections(txt_path)
    exp = hdr + main + side
    ok = True

    got = _docx_words(docx_path)
    if got == exp:
        print(f"DOCX OK: all {len(exp)} words match the TXT, in the same order")
    else:
        ok = False
        print(f"DOCX MISMATCH: expected {len(exp)} words, got {len(got)}")
        for k, (x, y) in enumerate(zip(exp, got)):
            if x != y:
                print(f"  first difference at word {k}: expected {x!r}, got {y!r}")
                break

    stream, pages = _pdf_stream(pdf_path)
    # two-column pages: file order is header, left col p1, right col p1, left col p2, right col p2
    if stream[:len(hdr)] == hdr and _interleaves(stream[len(hdr):], main, side):
        print(f"PDF  OK: all {len(exp)} words present; Experience and sidebar each keep TXT order")
    else:
        ok = False
        print("PDF MISMATCH: text differs from the TXT")
    print(f"PDF pages: {pages}")
    return ok and pages <= 2


# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Generate Resume.docx and Resume.pdf from a TXT file.")
    ap.add_argument("txt", nargs="?", default="New Resume.txt",
                    help="source TXT file")
    ap.add_argument("-o", "--out-dir", default=".", help="output folder (default: current)")
    ap.add_argument("--basename", default="Resume", help="output file name without extension")
    ap.add_argument("--verify", action="store_true", help="check outputs against the TXT")
    args = ap.parse_args()

    txt = Path(args.txt)
    if not txt.is_file():
        sys.exit(f"Input file not found: {txt}")
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    docx_path, pdf_path = out / f"{args.basename}.docx", out / f"{args.basename}.pdf"

    header, main_blocks, side_blocks = parse(txt)
    build_docx(header, main_blocks, side_blocks, docx_path)
    fits = build_pdf(header, main_blocks, side_blocks, pdf_path)
    print(f"Created {docx_path} and {pdf_path}")
    if not fits:
        print("WARNING: PDF content does not fit on 2 pages - reduce BODY or adjust column widths")
    if args.verify and not verify(txt, docx_path, pdf_path):
        sys.exit(1)


if __name__ == "__main__":
    main()