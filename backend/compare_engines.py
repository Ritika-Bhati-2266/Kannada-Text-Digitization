"""
OCR Engine Benchmark for Kannada Lipi Mitra.

Runs every ready engine on samples/*.png (the documents the UI serves) and
reports CER (Character Error Rate) against the ground truth captured from the
sample sources in samples/<name>.txt.

Usage:
    python compare_engines.py            # benchmark + one summary table
    python compare_engines.py -v         # also print each engine's raw output
"""
import os
import re
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

BACKEND_DIR = Path(__file__).resolve().parent
SAMPLES_DIR = BACKEND_DIR.parent / "samples"
VERBOSE = any(arg in ("-v", "--verbose") for arg in sys.argv[1:])

load_dotenv(BACKEND_DIR / ".env")

from ocr_service import ocr_manager, strip_zero_width_joiners


def normalize_for_cer(text: str) -> str:
    """CER normalization: drop zero-width joiners, collapse all whitespace."""
    return re.sub(r"\s+", " ", strip_zero_width_joiners(text)).strip()


def character_error_rate(reference: str, hypothesis: str) -> float:
    """Levenshtein distance over characters, divided by reference length."""
    ref = normalize_for_cer(reference)
    hyp = normalize_for_cer(hypothesis)
    if not ref:
        return 0.0 if not hyp else 1.0

    prev = list(range(len(hyp) + 1))
    for i, ref_char in enumerate(ref, 1):
        curr = [i] + [0] * len(hyp)
        for j, hyp_char in enumerate(hyp, 1):
            curr[j] = min(
                prev[j] + 1,          # deletion
                curr[j - 1] + 1,      # insertion
                prev[j - 1] + (ref_char != hyp_char),  # substitution / match
            )
        prev = curr
    return prev[-1] / len(ref)


def build_engine_runs() -> list:
    """Returns [(label, callable), ...] for every engine that is ready."""
    status = ocr_manager.check_all_engines()
    active = ocr_manager.get_configured_engine_name()

    print("\nENGINE STATUS:")
    for name, info in status.items():
        badge = " [ACTIVE in .env]" if name == active else ""
        if info.get("ready"):
            model = info.get("model") or f"{info.get('vision_model', '')} / {info.get('text_model', '')}"
            print(f"  - {name.upper()}{badge}: READY ({model})")
        else:
            print(f"  - {name.upper()}{badge}: NOT READY ({info.get('error')})")

    runs = []
    if status.get("groq", {}).get("ready"):
        groq = ocr_manager.engines["groq"]
        runs.append(("groq", lambda data: groq.extract_text(data)))
    if status.get("tesseract", {}).get("ready"):
        tesseract = ocr_manager.engines["tesseract"]
        runs.append(("tesseract psm 4", lambda data: tesseract.extract_text(data, psm=4)))
        runs.append(("tesseract psm 6", lambda data: tesseract.extract_text(data, psm=6)))
    return runs


def print_table(rows: list) -> None:
    col_image = max([len("Image")] + [len(row[0]) for row in rows])
    col_engine = max([len("Engine")] + [len(row[1]) for row in rows])

    print("\n" + "=" * (col_image + col_engine + 26))
    print("OCR BENCHMARK — CER vs GROUND TRUTH")
    print("=" * (col_image + col_engine + 26))
    print(f"{'Image':<{col_image}} | {'Engine':<{col_engine}} | {'CER':>7} | {'Latency':>8}")
    print("-" * (col_image + col_engine + 26))
    for image, engine, cer, latency in rows:
        cer_txt = f"{cer * 100:6.2f}%" if cer is not None else "     —"
        print(f"{image:<{col_image}} | {engine:<{col_engine}} | {cer_txt} | {latency:6.2f}s")
    print("-" * (col_image + col_engine + 26))


def run_benchmark() -> None:
    print("\n" + "=" * 80)
    print("   ಕನ್ನಡ ಲಿಪಿ ಮಿತ್ರ — OCR ENGINE BENCHMARK (CER)")
    print("=" * 80)

    if not SAMPLES_DIR.exists():
        print(f"\n[ERROR] Samples directory not found: {SAMPLES_DIR}")
        return

    images = sorted(SAMPLES_DIR.glob("*.png"))
    if not images:
        print(f"\n[ERROR] No PNG samples in: {SAMPLES_DIR}")
        print("Run 'python create_samples.py' to generate the sample documents.")
        return

    print(f"\nSamples ({len(images)}) in {SAMPLES_DIR}:")
    for img in images:
        gt_path = img.with_suffix(".txt")
        gt_state = "ground truth OK" if gt_path.exists() else "MISSING ground truth .txt"
        print(f"  - {img.name} ({img.stat().st_size / 1024:.1f} KB) [{gt_state}]")

    runs = build_engine_runs()
    if not runs:
        print("\n[ERROR] No OCR engine is ready. Configure backend/.env first.")
        return

    rows = []
    for img_path in images:
        gt_path = img_path.with_suffix(".txt")
        if not gt_path.exists():
            print(f"\n[SKIP] {img_path.name}: no ground truth file {gt_path.name}")
            continue

        ground_truth = gt_path.read_text(encoding="utf-8")
        image_bytes = img_path.read_bytes()

        print("\n" + "-" * 80)
        print(f"DOCUMENT: {img_path.name}")
        print("-" * 80)

        for label, extract in runs:
            start = time.perf_counter()
            result = extract(image_bytes)
            latency = time.perf_counter() - start

            if result.get("success"):
                cer = character_error_rate(ground_truth, result.get("text", ""))
                rows.append((img_path.name, label, cer, latency))
                print(f"  {label:<18} CER {cer * 100:6.2f}%  {latency:6.2f}s")
                if VERBOSE:
                    print("  " + (result.get("text", "") or "").replace("\n", "\n  "))
            else:
                rows.append((img_path.name, label, None, latency))
                print(f"  {label:<18} FAILED ({latency:6.2f}s): {result.get('error', 'unknown error')}")

    if rows:
        print_table(rows)
    else:
        print("\n[ERROR] No results produced.")
    print("CER = character errors / reference characters (0.00% = exact match).")


if __name__ == "__main__":
    run_benchmark()
