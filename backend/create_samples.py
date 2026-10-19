"""
Generates clean, authentic Kannada sample documents labeled clearly as SAMPLE.
Uses downloaded Noto Sans Kannada font for Kannada script and Arial for Latin characters.
Checks RAQM layout engine support for complex script conjunct shaping.
"""
import os
import re
import shutil
from PIL import Image, ImageDraw, ImageFont, features

# 1. Check RAQM availability
HAS_RAQM = features.check("raqm")
print(f"[Font Engine Diagnostics] features.check('raqm'): {HAS_RAQM}")
if not HAS_RAQM:
    print("[Font Engine Diagnostics] NOTE: 'raqm' is missing in this Python/Pillow build on Windows.")
    print("[Font Engine Diagnostics] Pillow will fall back to ImageFont.Layout.BASIC.")

BACKEND_DIR = os.path.abspath(os.path.dirname(__file__))
FONTS_DIR = os.path.join(BACKEND_DIR, "fonts")
os.makedirs(FONTS_DIR, exist_ok=True)

FONT_KN_REG = os.path.join(FONTS_DIR, "NotoSansKannada-Regular.ttf")
FONT_KN_BOLD = os.path.join(FONTS_DIR, "NotoSansKannada-Bold.ttf")

FONT_URLS = {
    FONT_KN_REG: "https://raw.githubusercontent.com/googlefonts/noto-fonts/main/hinted/ttf/NotoSansKannada/NotoSansKannada-Regular.ttf",
    FONT_KN_BOLD: "https://raw.githubusercontent.com/googlefonts/noto-fonts/main/hinted/ttf/NotoSansKannada/NotoSansKannada-Bold.ttf",
}

def ensure_fonts_downloaded():
    """Downloads Noto Sans Kannada (.ttf) into backend/fonts/ if missing."""
    import urllib.request
    for path, url in FONT_URLS.items():
        if not os.path.exists(path) or os.path.getsize(path) < 10000:
            print(f"[Font Manager] Downloading {os.path.basename(path)} from {url}...")
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = resp.read()
                    with open(path, "wb") as f:
                        f.write(data)
                print(f"[Font Manager] Downloaded {os.path.basename(path)} ({len(data)} bytes).")
            except Exception as e:
                print(f"[Font Manager] Failed to download {url}: {e}")

# Ensure fonts exist immediately
ensure_fonts_downloaded()

# Windows system fonts for Latin characters (English, numbers, symbols)
FONT_EN_REG = "C:/Windows/Fonts/arial.ttf" if os.path.exists("C:/Windows/Fonts/arial.ttf") else FONT_KN_REG
FONT_EN_BOLD = "C:/Windows/Fonts/arialbd.ttf" if os.path.exists("C:/Windows/Fonts/arialbd.ttf") else FONT_KN_BOLD

OUTPUT_DIRS = [
    os.path.abspath(os.path.join(BACKEND_DIR, "..", "samples")),
    os.path.abspath(os.path.join(BACKEND_DIR, "..", "frontend", "public", "samples")),
    os.path.abspath(os.path.join(BACKEND_DIR, "..", "frontend", "dist", "samples")),
]
for d in OUTPUT_DIRS:
    os.makedirs(d, exist_ok=True)

def load_font(font_path: str, size: int):
    """
    Loads font with layout_engine=ImageFont.Layout.RAQM for complex Indic conjunct shaping.
    Falls back gracefully if RAQM is missing in the Pillow environment.
    """
    if font_path and os.path.exists(font_path):
        try:
            return ImageFont.truetype(font_path, size, layout_engine=ImageFont.Layout.RAQM)
        except Exception:
            return ImageFont.truetype(font_path, size)
    return ImageFont.load_default()

def draw_mixed_text(draw: ImageDraw.ImageDraw, xy: tuple, text: str, font_kn, font_en, fill: str):
    """
    Renders text by routing Kannada characters (U+0C80 to U+0CFF) to Noto Sans Kannada
    and Latin/ASCII characters to Arial, preventing empty boxes (tofu) for mixed text.
    """
    x, y = xy
    # Tokenize by script runs (Kannada block with ZWJ/ZWNJ vs other)
    parts = re.split(r'([\u0C80-\u0CFF\u200C\u200D]+)', text)
    for part in parts:
        if not part:
            continue
        is_kannada = bool(re.search(r'[\u0C80-\u0CFF]', part))
        font = font_kn if is_kannada else font_en
        draw.text((x, y), part, fill=fill, font=font)
        bbox = draw.textbbox((x, y), part, font=font)
        x += (bbox[2] - bbox[0])
    return x

def create_document_image(filename: str, title: str, subtitle: str, paragraphs: list, metadata: dict):
    width, height = 950, 1150
    img = Image.new("RGB", (width, height), color="#FAF9F6")
    draw = ImageDraw.Draw(img)

    # Fonts
    font_title_kn = load_font(FONT_KN_BOLD, 28)
    font_title_en = load_font(FONT_EN_BOLD, 26)

    font_sub_kn = load_font(FONT_KN_REG, 20)
    font_sub_en = load_font(FONT_EN_REG, 19)

    font_body_kn = load_font(FONT_KN_REG, 21)
    font_body_en = load_font(FONT_EN_REG, 20)

    font_meta_key_kn = load_font(FONT_KN_BOLD, 18)
    font_meta_key_en = load_font(FONT_EN_BOLD, 17)
    font_meta_val_kn = load_font(FONT_KN_REG, 18)
    font_meta_val_en = load_font(FONT_EN_REG, 17)

    font_wm_kn = load_font(FONT_KN_BOLD, 20)
    font_wm_en = load_font(FONT_EN_BOLD, 19)

    # Outer and inner border
    draw.rectangle([(25, 25), (width - 25, height - 25)], outline="#2C3E50", width=2)
    draw.rectangle([(32, 32), (width - 32, height - 32)], outline="#BDC3C7", width=1)

    # Top SAMPLE Banner
    draw.rectangle([(25, 25), (width - 25, 70)], fill="#C0392B")
    draw_mixed_text(draw, (width // 2 - 210, 34), "ಮಾದರಿ ದಾಖಲೆ / FOR DEMO ONLY (SAMPLE)", font_wm_kn, font_wm_en, "#FFFFFF")

    # Document Header
    y = 95
    draw_mixed_text(draw, (60, y), title, font_title_kn, font_title_en, "#1A252F")
    y += 45
    draw_mixed_text(draw, (60, y), subtitle, font_sub_kn, font_sub_en, "#5A6B7C")
    y += 35
    draw.line([(60, y), (width - 60, y)], fill="#BDC3C7", width=1)
    y += 20

    # Metadata box
    draw.rectangle([(60, y), (width - 60, y + 90)], fill="#F0F4F8", outline="#CBD5E1", width=1)
    meta_y = y + 12
    for k, v in metadata.items():
        key_end_x = draw_mixed_text(draw, (80, meta_y), f"{k}:", font_meta_key_kn, font_meta_key_en, "#1E293B")
        draw_mixed_text(draw, (max(key_end_x + 16, 260), meta_y), str(v), font_meta_val_kn, font_meta_val_en, "#334155")
        meta_y += 26
    y += 115

    # Paragraphs / Body text
    for p in paragraphs:
        words = p.split(" ")
        line = ""
        for word in words:
            test_line = f"{line} {word}".strip()
            if len(test_line) > 52:
                draw_mixed_text(draw, (60, y), line, font_body_kn, font_body_en, "#1E293B")
                y += 38
                line = word
            else:
                line = test_line
        if line:
            draw_mixed_text(draw, (60, y), line, font_body_kn, font_body_en, "#1E293B")
            y += 48

    # Bottom Seal & Sign
    y = height - 130
    draw.rectangle([(width - 290, y), (width - 60, y + 65)], outline="#7F8C8D", width=1)
    draw_mixed_text(draw, (width - 275, y + 10), "ಸಹಿ ಮತ್ತು ಮೊಹರು", font_meta_key_kn, font_meta_key_en, "#334155")
    draw_mixed_text(draw, (width - 275, y + 35), "[ಸಕ್ಷಮ ಪ್ರಾಧಿಕಾರ / AUTHORITY]", font_meta_val_kn, font_meta_val_en, "#64748B")

    # Save to all target output directories
    for d in OUTPUT_DIRS:
        out_path = os.path.join(d, filename)
        img.save(out_path, "PNG")
        print(f"[OK] Generated: {out_path} ({os.path.getsize(out_path)} bytes)")

    return img

def generate_all_samples():
    print(f"Generating authentic Kannada sample documents (RAQM={HAS_RAQM})...")
    
    # 1. Government Circular (ಶಿಕ್ಷಣ ಇಲಾಖೆ ಸುತ್ತೋಲೆ)
    create_document_image(
        filename="sample_circular.png",
        title="ಕರ್ನಾಟಕ ಸರ್ಕಾರ — ಸಾರ್ವಜನಿಕ ಶಿಕ್ಷಣ ಇಲಾಖೆ",
        subtitle="ಅಧಿಕೃತ ಪ್ರಕಟಣೆ ಮತ್ತು ಸುತ್ತೋಲೆ (Official Government Circular)",
        paragraphs=[
            "ವಿಷಯ: ೨೦೨೬-೨೭ ನೇ ಸಾಲಿನ ಕನ್ನಡ ಭಾಷಾ ಸಂವರ್ಧನಾ ಸಪ್ತಾಹ ಆಚರಣೆ ಕುರಿತು.",
            "ರಾಜ್ಯದ ಎಲ್ಲಾ ಸರ್ಕಾರಿ ಮತ್ತು ಅನುದಾನಿತ ಪ್ರಾಥಮಿಕ ಹಾಗೂ ಪ್ರೌಢಶಾಲೆಗಳಲ್ಲಿ ಕನ್ನಡ ಭಾಷೆ ಮತ್ತು ಸಂಸ್ಕೃತಿಯನ್ನು ಉತ್ತೇಜಿಸಲು ವಿಶೇಷ ಕಾರ್ಯಕ್ರಮಗಳನ್ನು ಹಮ್ಮಿಕೊಳ್ಳಲು ಈ ಮೂಲಕ ನಿರ್ದೇಶಿಸಲಾಗಿದೆ.",
            "ಪ್ರಮುಖ ಚಟುವಟಿಕೆಗಳು: ೧. ಕನ್ನಡ ಗದ್ಯ ಮತ್ತು ಪದ್ಯ ವಾಚನ ಸ್ಪರ್ಧೆ. ೨. ಸುಭಾಷಿತ ಹಾಗೂ ಗಾದೆ ಮಾತುಗಳ ವಿಶ್ಲೇಷಣೆ. ೩. ಸ್ಥಳೀಯ ಸಾಹಿತಿಗಳ ಮತ್ತು ಇತಿಹಾಸಕಾರರ ಉಪನ್ಯಾಸ ಕಾರ್ಯಕ್ರಮ.",
            "ಸದರಿ ಕಾರ್ಯಕ್ರಮಗಳ ವರದಿಯನ್ನು ಸಂಬಂಧಪಟ್ಟ ಕ್ಷೇತ್ರ ಶಿಕ್ಷಣಾಧಿಕಾರಿಗಳಿಗೆ (BEO) ದಿನಾಂಕ ೧೫-೧೧-೨೦೨೬ ರೊಳಗೆ ಸಲ್ಲಿಸತಕ್ಕದ್ದು.",
            "ಸರ್ಕಾರದ ಆದೇಶದಂತೆ ಕಟ್ಟುನಿಟ್ಟಾಗಿ ಪಾಲಿಸಲು ಕೋರಲಾಗಿದೆ."
        ],
        metadata={
            "ಸುತ್ತೋಲೆ ಸಂಖ್ಯೆ": "ED-2026-KN-0492/SAMPLE",
            "ದಿನಾಂಕ": "೨೪ ಅಕ್ಟೋಬರ್ ೨೦೨೬ (24-10-2026)",
            "ಸ್ಥಳ": "ಬೆಂಗಳೂರು, ಕರ್ನಾಟಕ"
        }
    )

    # 2. Grama Panchayat Notice (ಗ್ರಾಮ ಪಂಚಾಯತಿ ಸಾರ್ವಜನಿಕ ಪ್ರಕಟಣೆ)
    create_document_image(
        filename="sample_notice.png",
        title="ಗ್ರಾಮ ಪಂಚಾಯತಿ ಕಾರ್ಯಾಲಯ — ಶ್ರೀರಂಗಪಟ್ಟಣ",
        subtitle="ಸಾರ್ವಜನಿಕ ಮಾಹಿತಿ ಪ್ರಕಟಣೆ (Public Notice)",
        paragraphs=[
            "ವಿಷಯ: ಮುಂಗಾರು ಮಳೆ ಮುನ್ಸೂಚನೆ ಹಾಗೂ ಕುಡಿಯುವ ನೀರಿನ ಶುದ್ಧೀಕರಣ ಅಭಿಯಾನ.",
            "ಗ್ರಾಮ ಪಂಚಾಯತಿ ವ್ಯಾಪ್ತಿಯ ಸಮಸ್ತ ನಾಗರಿಕರಿಗೆ ತಿಳಿಸುವುದೇನೆಂದರೆ, ಮುಂಬರುವ ವಾರದಲ್ಲಿ ಕುಡಿಯುವ ನೀರಿನ ಓವರ್‌ಹೆಡ್ ಟ್ಯಾಂಕ್‌ಗಳನ್ನು ಶುದ್ಧೀಕರಿಸುವ ಕಾರ್ಯ ನಡೆಯಲಿದೆ.",
            "ಆದ್ದರಿಂದ ಗ್ರಾಮಸ್ಥರು ದಿನಾಂಕ ೨೬-೧೦-೨೦೨೬ ರಂದು ಬೆಳಿಗ್ಗೆ ೮:೦೦ ಗಂಟೆಯಿಂದ ಸಂಜೆ ೬:೦೦ ಗಂಟೆಯವರೆಗೆ ಪರ್ಯಾಯ ನೀರಿನ ವ್ಯವಸ್ಥೆ ಮಾಡಿಕೊಳ್ಳಲು ಕೋರಲಾಗಿದೆ.",
            "ಹೆಚ್ಚಿನ ಮಾಹಿತಿಗಾಗಿ ಗ್ರಾಮ ಪಂಚಾಯತಿ ಅಭಿವೃದ್ಧಿ ಅಧಿಕಾರಿಗಳನ್ನು (PDO) ಸಂಪರ್ಕಿಸಬಹುದು.",
            "ಸ್ವಚ್ಛ ಗ್ರಾಮ, ಆರೋಗ್ಯವಂತ ಸಮಾಜ ನಮ್ಮೆಲ್ಲರ ಗುರಿ."
        ],
        metadata={
            "ಪ್ರಕಟಣೆ ಸಂಖ್ಯೆ": "GP-SRP-2026-NOTICE/SAMPLE",
            "ದಿನಾಂಕ": "೨೨ ಅಕ್ಟೋಬರ್ ೨೦೨೬ (22-10-2026)",
            "ತಾಲ್ಲೂಕು": "ಶ್ರೀರಂಗಪಟ್ಟಣ, ಮಂಡ್ಯ ಜಿಲ್ಲೆ"
        }
    )

    # 3. Kannada Textbook / Literature Excerpt (ಕನ್ನಡ ಸಾಹಿತ್ಯ ಪಠ್ಯಪುಸ್ತಕ)
    create_document_image(
        filename="sample_textbook.png",
        title="೮ ನೇ ತರಗತಿ ಕನ್ನಡ ಸಾಹಿತ್ಯ ದರ್ಶನ",
        subtitle="ಪಾಠ ೪: ರಾಷ್ಟ್ರಕವಿ ಕುವೆಂಪು ಅವರ ನಿಸರ್ಗ ಪ್ರೇಮ",
        paragraphs=[
            "ಕುಪ್ಪಳ್ಳಿ ವೆಂಕಟಪ್ಪ ಪುಟ್ಟಪ್ಪನವರು ಕನ್ನಡದ ಅಗ್ರಮಾನ್ಯ ಕವಿ ಹಾಗೂ ಜ್ಞಾನಪೀಠ ಪ್ರಶಸ್ತಿ ಪುರಸ್ಕೃತ ಮಹಾನ್ ಸಾಹಿತಿ.",
            "ಅವರ 'ಜಯ ಭಾರತ ಜನನಿಯ ತನುಜಾತೆ' ಗೀತೆಯು ಕರ್ನಾಟಕದ ನಾಡಗೀತೆಯಾಗಿ ನಾಡಿನಾದ್ಯಂತ ಹೆಮ್ಮೆಯಿಂದ ಹಾಡಲ್ಪಡುತ್ತದೆ.",
            "ಮಲೆನಾಡಿನ ಹಸಿರು ವನರಾಶಿ, ತುಂಗಾ ನದಿಯ ಹರಿವು ಮತ್ತು ಸಹ್ಯಾದ್ರಿಯ ಬೆಟ್ಟಗುಡ್ಡಗಳು ಕುವೆಂಪು ಅವರ ಕಾವ್ಯಕ್ಕೆ ಸದಾ ಸ್ಪೂರ್ತಿಯಾಗಿದ್ದವು.",
            "ಅವರು ಸಾರಿದ 'ವಿಶ್ವಮಾನವ ಸಂದೇಶ'ವು ಜಾತಿ, ಮತ, ಪಂಥಗಳ ಬೇಲಿಗಳನ್ನು ಮೀರಿ ಮನುಕುಲವೆಲ್ಲ ಒಂದೇ ಎಂಬ ಉನ್ನತ ಮಾನವೀಯ ಮೌಲ್ಯವನ್ನು ಪ್ರತಿಪಾದಿಸುತ್ತದೆ.",
            "ಅಭ್ಯಾಸ ಪ್ರಶ್ನೆಗಳು: ೧. ಕುವೆಂಪು ಅವರ ಜನ್ಮಸ್ಥಳ ಯಾವುದು? ೨. ಕರ್ನಾಟಕದ ನಾಡಗೀತೆ ರಚಿಸಿದವರು ಯಾರು?"
        ],
        metadata={
            "ಪಠ್ಯಪುಸ್ತಕ ಭಾಗ": "ಗದ್ಯ ವಿಭಾಗ (Prose Section) / SAMPLE",
            "ಪ್ರಕಾಶಕರು": "ಕರ್ನಾಟಕ ಪಠ್ಯಪುಸ್ತಕ ಸಂಘ (KTBS)",
            "ಮುದ್ರಣ ವರ್ಷ": "೨೦೨೬ ನೇ ಆವೃತ್ತಿ"
        }
    )
    print("All sample documents regenerated successfully!")

if __name__ == "__main__":
    generate_all_samples()
