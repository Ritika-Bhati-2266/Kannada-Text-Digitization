"""Generate a simulated handwritten Kannada note sample (for the handwriting OCR demo).
Writes the PNG to samples/ and frontend/public/samples/, plus ground truth samples/<name>.txt.
"""
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

random.seed(42)

ROOT = Path(__file__).resolve().parent
FONT_PATH = ROOT / "fonts" / "NotoSansKannada-Regular.ttf"
OUT_PATHS = [
    ROOT.parent / "samples" / "sample_handwriting.png",
    ROOT.parent / "frontend" / "public" / "samples" / "sample_handwriting.png",
]
GROUND_TRUTH_PATH = ROOT.parent / "samples" / "sample_handwriting.txt"

W, H = 1100, 780
INK = (36, 42, 58)
PAPER = (252, 248, 235)

LINES = [
    "ಪ್ರಿಯ ಗೆಳೆಯರೇ,",
    "ನಾಳೆ ಬೆಳಿಗ್ಗೆ ೧೦ ಗಂಟೆಗೆ",
    "ಶಾಲೆಯಲ್ಲಿ ಕನ್ನಡ ಸಾಹಿತ್ಯ ಸಭೆ ಇದೆ.",
    "ದಯವಿಟ್ಟು ಸಮಯಕ್ಕೆ ಸರಿಯಾಗಿ ಬನ್ನಿ.",
    "",
    "— ರಮೇಶ್, ೫ನೇ ತರಗತಿ, ಸರ್ಕಾರಿ ಶಾಲೆ",
]


def render_word(word, font_size, ink_color):
    """Render a whole word with the Kannada font (keeps conjuncts/shaping intact),
    then apply random rotation, vertical drift, and slight scale jitter to mimic
    the irregularity of real handwriting."""
    font = ImageFont.truetype(str(FONT_PATH), font_size)
    pad = font_size // 3
    box = font.getbbox(word)
    w = max(box[2] - box[0], 1) + pad * 2
    h = font_size + pad * 2
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.text((pad - box[0], pad), word, font=font, fill=ink_color + (255,))
    # Wider slant range than before for a more hand-drawn feel
    angle = random.uniform(-7, 7)
    img = img.rotate(angle, resample=Image.BICUBIC, expand=True)
    # Subtle scale jitter (±4%) — handwriting never keeps identical letter size
    scale = random.uniform(0.96, 1.04)
    if abs(scale - 1.0) > 0.01:
        new_size = (max(1, int(img.width * scale)), max(1, int(img.height * scale)))
        img = img.resize(new_size, Image.LANCZOS)
    return img


def random_ink():
    """Slight pen-pressure / ink-density variation per word."""
    drift = random.randint(-12, 8)
    return tuple(max(20, min(80, c + drift)) for c in INK)


def main():
    paper = Image.new("RGB", (W, H), PAPER)
    draw = ImageDraw.Draw(paper)

    # Faint ruled lines
    for y in range(90, H - 40, 64):
        draw.line([(50, y), (W - 50, y)], fill=(210, 200, 178), width=1)

    # Margin line
    draw.line([(90, 40), (90, H - 40)], fill=(224, 168, 160), width=2)

    y = 70
    for line in LINES:
        x = 110 + random.randint(-6, 10)
        # Per-line baseline drift — handwriting rarely sits perfectly level
        line_drift = random.randint(-4, 4)
        if line:
            for word in line.split(" "):
                size = random.randint(35, 43)
                glyph = render_word(word, size, random_ink())
                gy = y + line_drift + random.randint(-5, 5)
                paper.paste(glyph, (int(x), int(gy)), glyph)
                x += glyph.width + random.randint(6, 18)
        y += 92

    # Paper texture: random specks + faint smudge patches
    for _ in range(400):
        px, py = random.randint(0, W - 1), random.randint(0, H - 1)
        c = random.randint(200, 232)
        paper.putpixel((px, py), (c, c - 5, c - 15))
    for _ in range(6):
        cx, cy = random.randint(80, W - 80), random.randint(50, H - 50)
        cr = random.randint(8, 22)
        for ox in range(-cr, cr + 1):
            for oy in range(-cr, cr + 1):
                if ox * ox + oy * oy <= cr * cr:
                    nx, ny = cx + ox, cy + oy
                    if 0 <= nx < W and 0 <= ny < H:
                        r, g, b = paper.getpixel((nx, ny))
                        paper.putpixel((nx, ny), (max(0, r - 6), max(0, g - 6), max(0, b - 8)))

    for out in OUT_PATHS:
        out.parent.mkdir(parents=True, exist_ok=True)
        paper.save(out, "PNG")
        print(f"Saved: {out}")

    GROUND_TRUTH_PATH.parent.mkdir(parents=True, exist_ok=True)
    GROUND_TRUTH_PATH.write_text("\n".join(LINES) + "\n", encoding="utf-8")
    print(f"Saved ground truth: {GROUND_TRUTH_PATH}")


if __name__ == "__main__":
    main()
