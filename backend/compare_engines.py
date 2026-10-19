"""
Engine Comparison Utility for Kannada Lipi Mitra
Runs all configured OCR engines (Gemini, Groq, Tesseract) on test images in backend/test_images/
and displays a side-by-side comparative benchmark table.
"""
import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

# Force UTF-8 stdout encoding for Kannada characters on Windows
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

# Load environment
BACKEND_DIR = Path(__file__).resolve().parent
load_dotenv(BACKEND_DIR / ".env")

from ocr_service import ocr_manager

TEST_IMAGES_DIR = BACKEND_DIR / "test_images"

def format_box(title: str, text: str, width: int = 80) -> str:
    line = "─" * (width - 2)
    preview = text.strip()
    if len(preview) > 300:
        preview = preview[:300] + " ... [TRUNCATED FOR DISPLAY]"
    return f"┌─ {title} {line[len(title) + 3:]}┐\n{preview}\n└{line}┘"

def run_engine_comparison():
    print("\n" + "=" * 80)
    print("   ಕನ್ನಡ ಲಿಪಿ ಮಿತ್ರ — OCR ENGINE COMPARISON & BENCHMARK")
    print("=" * 80)

    # 1. Discover test images
    if not TEST_IMAGES_DIR.exists():
        print(f"\n[ERROR] Directory not found: {TEST_IMAGES_DIR}")
        print("Please create 'backend/test_images/' and add sample Kannada images.")
        return

    images = list(TEST_IMAGES_DIR.glob("*.png")) + list(TEST_IMAGES_DIR.glob("*.jpg")) + list(TEST_IMAGES_DIR.glob("*.jpeg"))
    if not images:
        print(f"\n[WARN] No test images found in: {TEST_IMAGES_DIR}")
        print("Run 'python create_samples.py' to generate default sample documents.")
        return

    print(f"\nDiscovered {len(images)} test document(s) in {TEST_IMAGES_DIR.name}:")
    for idx, img in enumerate(images, 1):
        size_kb = img.stat().st_size / 1024
        print(f"  {idx}. {img.name} ({size_kb:.1f} KB)")

    # 2. Check engine status
    print("\n" + "─" * 80)
    print("ENGINE CONFIGURATION STATUS:")
    engines_status = ocr_manager.check_all_engines()
    active_engine_name = ocr_manager.get_configured_engine_name()

    for name, info in engines_status.items():
        is_active = (name == active_engine_name)
        active_badge = " [ACTIVE ENGINE in .env]" if is_active else ""
        if info.get("ready"):
            model_info = info.get("model") or f"{info.get('vision_model', '')} / {info.get('text_model', '')}"
            print(f"  • {name.upper()}{active_badge}: READY (Model: {model_info})")
        else:
            print(f"  • {name.upper()}{active_badge}: NOT READY ({info.get('error')})")

    # 3. Benchmark each image across all engines
    results = []
    
    for img_path in images:
        print("\n" + "=" * 80)
        print(f"TESTING DOCUMENT: {img_path.name}")
        print("=" * 80)

        with open(img_path, "rb") as f:
            image_bytes = f.read()

        image_results = {"image": img_path.name, "engines": {}}

        for eng_name, engine in ocr_manager.engines.items():
            print(f"\n[{eng_name.upper()}] Running OCR extraction...")
            status = engine.check_ready()

            if not status.get("ready"):
                print(f"  ↳ SKIPPED: {status.get('error')}")
                image_results["engines"][eng_name] = {
                    "status": "SKIPPED",
                    "error": status.get("error"),
                    "latency": 0.0,
                    "words": 0,
                    "chars": 0,
                    "text": ""
                }
                continue

            # Measure extraction time
            start_time = time.perf_counter()
            ocr_res = engine.extract_text(image_bytes)
            latency = time.perf_counter() - start_time

            if ocr_res.get("success"):
                words = ocr_res.get("word_count", 0)
                chars = ocr_res.get("char_count", 0)
                text = ocr_res.get("text", "")
                print(f"  ↳ SUCCESS ({latency:.2f}s) | Words: {words} | Chars: {chars} | Model: {ocr_res.get('model_used')}")
                print(format_box(f"{eng_name.upper()} EXTRACTED TEXT", text))

                image_results["engines"][eng_name] = {
                    "status": "SUCCESS",
                    "latency": latency,
                    "words": words,
                    "chars": chars,
                    "text": text,
                    "model": ocr_res.get("model_used")
                }
            else:
                err = ocr_res.get("error", "Unknown error")
                print(f"  ↳ FAILED ({latency:.2f}s): {err}")
                image_results["engines"][eng_name] = {
                    "status": "FAILED",
                    "latency": latency,
                    "error": err,
                    "words": 0,
                    "chars": 0,
                    "text": ""
                }

        results.append(image_results)

    # 4. Side-by-Side Benchmark Summary Table
    print("\n" + "=" * 80)
    print("SIDE-BY-SIDE OCR ENGINE BENCHMARK SUMMARY")
    print("=" * 80)
    print(f"{'Image':<22} | {'Engine':<10} | {'Status':<9} | {'Words':<6} | {'Chars':<6} | {'Latency':<8} | {'Model':<20}")
    print("-" * 88)

    for item in results:
        img_name = item["image"]
        for eng, d in item["engines"].items():
            stat = d["status"]
            words = str(d["words"]) if stat == "SUCCESS" else "-"
            chars = str(d["chars"]) if stat == "SUCCESS" else "-"
            lat = f"{d['latency']:.2f}s" if stat in ("SUCCESS", "FAILED") else "-"
            model = d.get("model", d.get("error", ""))[:20]
            print(f"{img_name:<22} | {eng:<10} | {stat:<9} | {words:<6} | {chars:<6} | {lat:<8} | {model:<20}")
        print("-" * 88)

    print("\nBenchmark complete! Switch active engine anytime via OCR_ENGINE in backend/.env")

if __name__ == "__main__":
    run_engine_comparison()
