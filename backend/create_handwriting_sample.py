"""Generate a simulated handwritten Kannada note sample (for the handwriting OCR demo).
Writes the PNG to backend/test_images/, samples/, and frontend/public/samples/.
"""
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

random.seed(42)

ROOT = Path(__file__).resolve().parent
FONT_PATH = ROOT / "fonts" / "NotoSansKannada-Regular.ttf"
OUT_PATHS = [
    ROOT / "test_images" / "sample_handwriting.png",
    ROOT.parent / "samples" / "sample_handwriting.png",
    ROOT.parent / "frontend" / "public" / "samples" / "sample_handwriting.png",
]

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


def render_word(word, font_size):
    """Render a whole word with the Kannada font (keeps conjuncts/shaping intact),
    then tilt it slightly to mimic handwriting."""
    font = ImageFont.truetype(str(FONT_PATH), font_size)
    pad = font_size // 3
    box = font.getbbox(word)
    w = max(box[2] - box[0], 1) + pad * 2
    h = font_size + pad * 2
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.text((pad - box[0], pad), word, font=font, fill=INK + (255,))
    angle = random.uniform(-4, 4)
    return img.rotate(angle, resample=Image.BICUBIC, expand=True)


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
        x = 110 + random.randint(-4, 8)
        if line:
            for word in line.split(" "):
                size = random.randint(36, 41)
                glyph = render_word(word, size)
                gy = y + random.randint(-3, 3)
                paper.paste(glyph, (int(x), int(gy)), glyph)
                x += glyph.width + random.randint(8, 14)
        y += 92

    # Slight paper texture: random specks
    for _ in range(350):
        px, py = random.randint(0, W - 1), random.randint(0, H - 1)
        c = random.randint(205, 230)
        paper.putpixel((px, py), (c, c - 5, c - 15))

    for out in OUT_PATHS:
        out.parent.mkdir(parents=True, exist_ok=True)
        paper.save(out, "PNG")
        print(f"Saved: {out}")


if __name__ == "__main__":
    main()
