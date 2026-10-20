"""Generate the hackathon submission PPT for Kannada Lipi Mitra (PS-05).
Run:  python docs/make_ppt.py   ->  docs/Kannada_Lipi_Mitra_Presentation.pptx
"""
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Inches, Pt

OUT = Path(__file__).resolve().parent / "Kannada_Lipi_Mitra_Presentation.pptx"

# Palette (Karnataka flag inspired)
RED = RGBColor(0xC6, 0x28, 0x28)
GOLD = RGBColor(0xFF, 0xB3, 0x00)
NAVY = RGBColor(0x1A, 0x23, 0x3B)
DARK = RGBColor(0x24, 0x2B, 0x3D)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT = RGBColor(0xF5, 0xF6, 0xFA)
GREY = RGBColor(0x5A, 0x64, 0x72)
TEAL = RGBColor(0x00, 0x79, 0x6B)

W, H = Inches(13.333), Inches(7.5)


def blank_slide(prs, bg=WHITE):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = bg
    return slide


def box(slide, x, y, w, h, fill=None, line=None, text="", size=16, color=DARK,
        bold=False, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.MIDDLE, radius=True):
    shape_type = MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE
    sp = slide.shapes.add_shape(shape_type, x, y, w, h)
    if fill is None:
        sp.fill.background()
    else:
        sp.fill.solid()
        sp.fill.fore_color.rgb = fill
    if line is None:
        sp.line.fill.background()
    else:
        sp.line.color.rgb = line
        sp.line.width = Pt(1.25)
    tf = sp.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = Inches(0.12)
    tf.margin_right = Inches(0.12)
    tf.margin_top = Inches(0.05)
    tf.margin_bottom = Inches(0.05)
    p = tf.paragraphs[0]
    p.alignment = align
    r = p.add_run()
    r.text = text
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.color.rgb = color
    r.font.name = "Segoe UI"
    return sp


def textbox(slide, x, y, w, h, lines, size=18, color=DARK, bold=False,
            align=PP_ALIGN.LEFT, spacing=1.0, bullet=False):
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.space_after = Pt(size * 0.45)
        p.line_spacing = spacing
        r = p.add_run()
        r.text = ("•  " + line) if bullet else line
        r.font.size = Pt(size)
        r.font.bold = bold
        r.font.color.rgb = color
        r.font.name = "Segoe UI"
    return tb


def header(slide, title, subtitle=None):
    box(slide, Inches(0), Inches(0), W, Inches(0.16), fill=RED, radius=False)
    textbox(slide, Inches(0.6), Inches(0.35), Inches(12.1), Inches(0.8),
            [title], size=32, color=NAVY, bold=True)
    if subtitle:
        textbox(slide, Inches(0.6), Inches(1.05), Inches(12.1), Inches(0.5),
                [subtitle], size=15, color=GREY)


def footer(slide, n, total=9):
    textbox(slide, Inches(0.6), Inches(7.05), Inches(9), Inches(0.35),
            ["ಕನ್ನಡ ಲಿಪಿ ಮಿತ್ರ · Kannada Digital Innovation Hackathon 2026 · PS-05"],
            size=10, color=GREY)
    textbox(slide, Inches(12.2), Inches(7.05), Inches(0.8), Inches(0.35),
            [f"{n}/{total}"], size=10, color=GREY, align=PP_ALIGN.RIGHT)


def arrow(slide, x, y, w=Inches(0.45), h=Inches(0.22)):
    sp = slide.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, x, y, w, h)
    sp.fill.solid()
    sp.fill.fore_color.rgb = GOLD
    sp.line.fill.background()
    return sp


def down_arrow(slide, x, y, w=Inches(0.22), h=Inches(0.4)):
    sp = slide.shapes.add_shape(MSO_SHAPE.DOWN_ARROW, x, y, w, h)
    sp.fill.solid()
    sp.fill.fore_color.rgb = GOLD
    sp.line.fill.background()
    return sp


prs = Presentation()
prs.slide_width, prs.slide_height = W, H

# ── 1. Title ────────────────────────────────────────────────────────────
s = blank_slide(prs, NAVY)
box(s, Inches(0), Inches(3.45), W, Inches(0.08), fill=GOLD, radius=False)
textbox(s, Inches(1), Inches(1.6), Inches(11.3), Inches(1.2),
        ["ಕನ್ನಡ ಲಿಪಿ ಮಿತ್ರ"], size=54, color=WHITE, bold=True, align=PP_ALIGN.CENTER)
textbox(s, Inches(1), Inches(2.7), Inches(11.3), Inches(0.6),
        ["Kannada Lipi Mitra — Kannada Document AI & High-Fidelity OCR"],
        size=22, color=GOLD, align=PP_ALIGN.CENTER)
textbox(s, Inches(1), Inches(3.8), Inches(11.3), Inches(1.6), [
    "Turns Kannada document images into searchable, understandable, speakable digital text",
    "Problem Statement 05 · Kannada Text Digitization",
], size=17, color=WHITE, align=PP_ALIGN.CENTER)
textbox(s, Inches(1), Inches(5.6), Inches(11.3), Inches(1.0), [
    "Participant: Ritika Bhati · github.com/Ritika-Bhati-2266/Kannada-Text-Digitization",
    "Kannada Digital Innovation Hackathon 2026 · Theme: Code. Create. Celebrate Kannada.",
    "Organized by HackerRank Campus Crew & The National Institute of Engineering (NIE), Mysuru",
], size=13, color=RGBColor(0xB8, 0xC0, 0xD0), align=PP_ALIGN.CENTER)

# ── 2. Problem Statement ────────────────────────────────────────────────
s = blank_slide(prs)
header(s, "Problem Statement — PS-05: Kannada Text Digitization",
       "The assignment: convert Kannada text from images, scanned documents or handwritten material into searchable digital text — and make it easier to understand and access")
box(s, Inches(0.6), Inches(1.75), Inches(12.1), Inches(1.15), fill=LIGHT, line=RED,
    text='"Develop a solution that converts Kannada text from images, scanned documents, or handwritten '
         'material into searchable digital text and makes the content easier to understand and access."',
    size=16, color=NAVY)
textbox(s, Inches(0.6), Inches(3.2), Inches(5.9), Inches(0.5), ["Who is affected"], size=20, color=RED, bold=True)
textbox(s, Inches(0.6), Inches(3.8), Inches(5.9), Inches(3.0), [
    "Students & researchers — textbook pages locked inside scans",
    "Citizens — govt. circulars, notices, land & health records on paper",
    "Visually impaired users — no search, no screen reader, no speech",
    "Archives & museums — heritage manuscripts never digitized",
], size=15, color=DARK, bullet=True)
textbox(s, Inches(6.9), Inches(3.2), Inches(5.8), Inches(0.5), ["Why it matters"], size=20, color=RED, bold=True)
textbox(s, Inches(6.9), Inches(3.8), Inches(5.8), Inches(3.0), [
    "Kannada is spoken by 40M+ people — content must be digital to be accessed",
    "Paper documents are invisible to search, translation & assistive tech",
    "Scale: thousands of pages exist only as photos and scans today",
    "Every un-digitized document is language heritage at risk",
], size=15, color=DARK, bullet=True)
footer(s, 2)

# ── 3. Existing Systems & Gaps ──────────────────────────────────────────
s = blank_slide(prs)
header(s, "Existing Systems & Their Gaps")
rows = [
    ("Traditional OCR\n(Tesseract + kan data)", "Cheap & offline", "Fails on modern scans & mixed Kannada-English; silent garbage output"),
    ("General cloud OCR\n(Google Vision, Textract)", "Mature platforms", "Weak Indic-script accuracy; pay-per-call; no Kannada validation"),
    ("Manual transcription", "Accurate text", "Slow, costly, impossible at archive scale"),
    ("Static PDF text layers", "Searchable if present", "Useless for photos & image-only scans"),
]
y = Inches(1.55)
box(s, Inches(0.6), y, Inches(3.6), Inches(0.5), fill=NAVY, text="Existing approach", size=14, color=WHITE, bold=True, align=PP_ALIGN.CENTER)
box(s, Inches(4.3), y, Inches(3.2), Inches(0.5), fill=NAVY, text="Strength", size=14, color=WHITE, bold=True, align=PP_ALIGN.CENTER)
box(s, Inches(7.6), y, Inches(5.1), Inches(0.5), fill=RED, text="Gap / limitation", size=14, color=WHITE, bold=True, align=PP_ALIGN.CENTER)
y = Inches(2.15)
for approach, strength, gap in rows:
    box(s, Inches(0.6), y, Inches(3.6), Inches(0.95), fill=LIGHT, text=approach, size=13, color=NAVY, bold=True)
    box(s, Inches(4.3), y, Inches(3.2), Inches(0.95), fill=WHITE, line=GREY, text=strength, size=13, color=GREY)
    box(s, Inches(7.6), y, Inches(5.1), Inches(0.95), fill=RGBColor(0xFD, 0xEC, 0xEC), text=gap, size=13, color=RED)
    y += Inches(1.08)
box(s, Inches(0.6), Inches(6.5), Inches(12.1), Inches(0.45), fill=GOLD,
    text="Common gap: nobody verifies the output is actually Kannada — and nobody helps you understand the text afterwards.",
    size=14, color=NAVY, bold=True, align=PP_ALIGN.CENTER)
footer(s, 3)

# ── 4. How Our Solution Is Different ────────────────────────────────────
s = blank_slide(prs)
header(s, "How Our Solution Is Different")
items = [
    ("Offline-first, two engines", "One OCR Manager routes to offline Tesseract (default) or the optional Groq vision model — pick via the header dropdown. No API key needed: Tesseract runs end to end offline."),
    ("Script-distribution validation", "Post-extraction Unicode analysis (Kannada / Devanagari / Latin shares) on every result; on the Groq path, a wrong-script answer triggers one targeted retry — a class of silent failure raw OCR never reports."),
    ("Images, PDFs & samples", "Upload, drag-drop, camera capture or multi-page PDF (page-wise OCR with per-page markers); plus four sample documents — sample 4 is simulated handwriting generated by script, not real handwriting."),
    ("Understand + hear, not just extract", "One-click translation to English/Hindi (needs the optional Groq key; the UI says so plainly when it's missing) and authentic Kannada text-to-speech — plus in-text search, editable text, copy / TXT / print-to-PDF."),
]
y = Inches(1.6)
for i, (t, d) in enumerate(items, 1):
    box(s, Inches(0.6), y, Inches(0.55), Inches(1.15), fill=RED, text=str(i), size=20, color=WHITE, bold=True, align=PP_ALIGN.CENTER)
    box(s, Inches(1.3), y, Inches(11.4), Inches(1.15), fill=LIGHT, line=None, text="", size=12)
    textbox(s, Inches(1.55), y + Inches(0.08), Inches(11.0), Inches(0.4), [t], size=17, color=NAVY, bold=True)
    textbox(s, Inches(1.55), y + Inches(0.48), Inches(11.0), Inches(0.6), [d], size=13, color=DARK)
    y += Inches(1.3)
footer(s, 4)

# ── 5. Approach & Workflow ──────────────────────────────────────────────
s = blank_slide(prs)
header(s, "Approach — Methodology & Workflow")
steps_top = [
    ("Input\nimage · camera · PDF · samples", NAVY),
    ("FastAPI\n/api/ocr endpoint", DARK),
    ("UnifiedOCRManager\nengine selection", RED),
    ("OCR engine\ntesseract (default) | groq", TEAL),
]
x = Inches(0.55)
for t, c in steps_top:
    box(s, x, Inches(1.6), Inches(2.85), Inches(1.0), fill=c, text=t, size=13, color=WHITE, bold=True, align=PP_ALIGN.CENTER)
    if x < Inches(8.6):
        arrow(s, x + Inches(2.95), Inches(1.99))
    x += Inches(3.2)
down_arrow(s, Inches(6.55), Inches(2.7))
box(s, Inches(3.9), Inches(3.2), Inches(5.5), Inches(0.95), fill=GOLD,
    text="Script-distribution check (both engines)\nGroq path only: issue? one smart retry", size=14, color=NAVY, bold=True, align=PP_ALIGN.CENTER)
down_arrow(s, Inches(6.55), Inches(4.2))
box(s, Inches(3.9), Inches(4.7), Inches(5.5), Inches(0.8), fill=DARK,
    text="{ text · word/char counts · script stats · engine used }", size=14, color=WHITE, align=PP_ALIGN.CENTER)
outs = [("Editable pane\nsearch + highlight\ncopy · TXT · print/PDF", NAVY),
        ("Translate API\nKannada → EN / HI\nneeds optional Groq key", TEAL),
        ("TTS API\nKannada speech\ngTTS fallback", RED)]
x = Inches(1.3)
for t, c in outs:
    box(s, x, Inches(5.8), Inches(3.4), Inches(1.05), fill=c, text=t, size=13, color=WHITE, bold=True, align=PP_ALIGN.CENTER)
    x += Inches(3.8)
textbox(s, Inches(0.6), Inches(7.0), Inches(12), Inches(0.4),
        ["Design decisions: manager pattern (engine = config) · deterministic Unicode validation · Groq path adds retry + Tesseract cross-check · same-origin deploy"],
        size=11, color=GREY)
footer(s, 5)

# ── 6. Tech Stack ───────────────────────────────────────────────────────
s = blank_slide(prs)
header(s, "Tech Stack")
cols = [
    ("Frontend", NAVY, ["Vanilla JS (ES modules)", "HTML5 · CSS3 · responsive", "Vite 6 build tooling", "Web Speech API (TTS)"]),
    ("Backend", RED, ["Python 3.12 · FastAPI", "Uvicorn · Pydantic", "Pillow · OpenCV", "gTTS (lang='kn')"]),
    ("AI Engines", TEAL, ["Tesseract + OpenCV (offline, default)", "Groq open vision LLM (optional)", "Script stats + user warnings", "Groq path: smart retry + cross-check", "Translation needs optional Groq key"]),
    ("DevOps", RGBColor(0x6A, 0x1B, 0x9A), ["Render Docker runtime", "Dockerfile: Tesseract + tesseract-ocr-kan", "multi-stage: Node build → Python image", "env-var secrets (never committed)", "GitHub · Swagger /docs"]),
]
x = Inches(0.6)
for title, color, items in cols:
    box(s, x, Inches(1.7), Inches(2.95), Inches(0.6), fill=color, text=title, size=17, color=WHITE, bold=True, align=PP_ALIGN.CENTER)
    box(s, x, Inches(2.35), Inches(2.95), Inches(3.4), fill=LIGHT, text="", size=12)
    textbox(s, x + Inches(0.2), Inches(2.55), Inches(2.6), Inches(3.0), items, size=13, color=DARK, bullet=True, spacing=1.05)
    x += Inches(3.2)
box(s, Inches(0.6), Inches(6.15), Inches(12.1), Inches(0.65), fill=NAVY,
    text="One repository · one deployment · runs with API keys OR fully offline on Tesseract",
    size=15, color=GOLD, bold=True, align=PP_ALIGN.CENTER)
footer(s, 6)

# ── 7. Architecture Diagram ─────────────────────────────────────────────
s = blank_slide(prs)
header(s, "Architecture — Components & Data Flow")
box(s, Inches(0.9), Inches(1.6), Inches(11.5), Inches(1.15), fill=LIGHT, line=NAVY, text="", size=12)
textbox(s, Inches(1.1), Inches(1.68), Inches(11), Inches(0.35), ["Browser — Split-view UI"], size=15, color=NAVY, bold=True)
textbox(s, Inches(1.1), Inches(2.05), Inches(11), Inches(0.6),
        ["image upload | camera capture | multi-page PDF (page-wise) | sample docs  →  edit · search · translate · TTS · export"],
        size=12, color=DARK)
down_arrow(s, Inches(6.5), Inches(2.85), h=Inches(0.35))
textbox(s, Inches(6.9), Inches(2.88), Inches(3.5), Inches(0.3), ["REST: /api/ocr · /api/translate · /api/tts"], size=11, color=GREY)
box(s, Inches(2.5), Inches(3.3), Inches(8.3), Inches(0.7), fill=DARK,
    text="FastAPI (main.py) — API endpoints + serves built frontend (same origin)", size=14, color=WHITE, bold=True, align=PP_ALIGN.CENTER)
down_arrow(s, Inches(6.5), Inches(4.1), h=Inches(0.35))
box(s, Inches(2.5), Inches(4.55), Inches(8.3), Inches(0.7), fill=RED,
    text="UnifiedOCRManager — engine selection & readiness checks", size=14, color=WHITE, bold=True, align=PP_ALIGN.CENTER)
engines = [("Tesseract + OpenCV\noffline OCR (default)", GREY), ("Groq\nopen vision LLM (optional)", RGBColor(0x02, 0x77, 0xBD))]
x = Inches(3.6)
for t, c in engines:
    box(s, x, Inches(5.55), Inches(2.9), Inches(0.95), fill=c, text=t, size=13, color=WHITE, bold=True, align=PP_ALIGN.CENTER)
    x += Inches(3.2)
down_arrow(s, Inches(6.5), Inches(6.55), h=Inches(0.3))
textbox(s, Inches(3.2), Inches(6.6), Inches(7), Inches(0.4),
        ["script stats + warnings · Groq path: retry + cross-check · translation (optional key) · gTTS fallback"], size=12, color=NAVY, bold=True)
footer(s, 7)

# ── 8. Measured accuracy ────────────────────────────────────────────────
s = blank_slide(prs)
header(s, "Measured Accuracy — CER from compare_engines.py",
       "Character error rate vs ground-truth text (lower is better, 0.00% = exact) · reproduce: python backend/compare_engines.py")
acc_cols = [
    ("Sample", Inches(0.6), Inches(3.7), NAVY),
    ("Groq (vision LLM)", Inches(4.35), Inches(2.7), RGBColor(0x02, 0x77, 0xBD)),
    ("Tesseract psm 4", Inches(7.1), Inches(2.7), GREY),
    ("Tesseract psm 6 (default)", Inches(9.85), Inches(2.85), TEAL),
]
y = Inches(1.7)
for t, x, w, c in acc_cols:
    box(s, x, y, w, Inches(0.5), fill=c, text=t, size=13, color=WHITE, bold=True, align=PP_ALIGN.CENTER)
acc_rows = [
    ("sample_circular.png", "52.35%  (48.9s)", "20.75%  (0.84s)", "20.51%  (0.66s)"),
    ("sample_handwriting.png (simulated)", "35.29%  (20.9s)", "13.24%  (0.35s)", "13.97%  (0.28s)"),
    ("sample_notice.png", "50.27%  (99.5s)", "23.38%  (0.71s)", "22.16%  (2.60s)"),
    ("sample_textbook.png", "rate-limited  ✗", "17.62%  (0.94s)", "16.25%  (0.92s)"),
]
y = Inches(2.3)
for row in acc_rows:
    for i, (t, x, w, c) in enumerate(acc_cols):
        box(s, x, y, w, Inches(0.62), fill=LIGHT if i == 0 else WHITE, line=GREY if i else None,
            text=row[i], size=12, color=NAVY if i == 0 else (RED if "✗" in row[i] else DARK),
            bold=(i == 0), align=PP_ALIGN.CENTER if i else PP_ALIGN.LEFT)
    y += Inches(0.72)
box(s, Inches(0.6), Inches(5.4), Inches(12.1), Inches(1.25), fill=RGBColor(0xFD, 0xEC, 0xEC), line=RED,
    text="Groq varies run to run and free-tier rate limits can fail a call outright (textbook row above). "
         "On these samples the offline default is both more accurate and ~30× faster — that's why "
         "Tesseract is the default and Groq stays optional. Both are one dropdown apart; compare on your own documents.",
    size=13, color=NAVY, align=PP_ALIGN.CENTER)
footer(s, 8)

# ── 9. Conclusion ───────────────────────────────────────────────────────
s = blank_slide(prs)
header(s, "Conclusion & Future Scope")
textbox(s, Inches(0.6), Inches(1.65), Inches(12.1), Inches(0.5), ["Impact"], size=20, color=RED, bold=True)
textbox(s, Inches(0.6), Inches(2.2), Inches(12.1), Inches(1.8), [
    "Any Kannada document image becomes text you can search, edit, hear, translate and share",
    "Handles images and multi-page PDFs, plus an honestly-labelled simulated handwriting sample",
    "Groq-path validation (script retry + Tesseract cross-check) flags silent failures raw OCR never reports",
    "Offline-first core runs with zero API keys; an optional Groq key adds the vision LLM and translation",
    "Directly fulfils PS-05: searchable digital text + easier to understand and access",
], size=15, color=DARK, bullet=True)
textbox(s, Inches(0.6), Inches(4.3), Inches(12.1), Inches(0.5), ["Future Scope"], size=20, color=RED, bold=True)
textbox(s, Inches(0.6), Inches(4.85), Inches(12.1), Inches(1.6), [
    "Batch PDF ingestion with page-wise OCR and bulk export",
    "Real handwriting recognition research (today's demo sample is simulated)",
    "Kannada → Latin transliteration and dual-script reading mode",
    "Screen-reader-optimized accessibility mode for low-vision users",
], size=15, color=DARK, bullet=True)
box(s, Inches(0.6), Inches(6.45), Inches(12.1), Inches(0.55), fill=NAVY,
    text="Code. Create. Celebrate Kannada.  ·  ಧನ್ಯವಾದಗಳು  ·  Thank you",
    size=16, color=GOLD, bold=True, align=PP_ALIGN.CENTER)
footer(s, 9)

prs.save(OUT)
print(f"Saved: {OUT}")
