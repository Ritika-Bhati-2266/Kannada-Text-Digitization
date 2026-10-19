import os
import sys
import json
import requests

sys.stdout.reconfigure(encoding="utf-8")

samples = [
    ("1. Education Circular (ಶಿಕ್ಷಣ ಇಲಾಖೆ ಸುತ್ತೋಲೆ)", "sample_circular.png"),
    ("2. Grama Panchayat Notice (ಗ್ರಾಮ ಪಂಚಾಯತಿ ಪ್ರಕಟಣೆ)", "sample_notice.png"),
    ("3. Kannada Textbook (ಕನ್ನಡ ಸಾಹಿತ್ಯ ಪಠ್ಯಪುಸ್ತಕ)", "sample_textbook.png")
]

results = []

for title, fname in samples:
    full_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "samples", fname))
    print("=" * 80)
    print(f"Testing OCR for: {title}")
    print(f"File: {full_path} ({os.path.getsize(full_path)} bytes)")
    
    with open(full_path, "rb") as f:
        files = {"file": (fname, f, "image/png")}
        res = requests.post("http://127.0.0.1:8000/api/ocr", files=files)
    
    print(f"Status Code: {res.status_code}")
    if res.status_code == 200:
        data = res.json()
        print(f"Engine Used: {data.get('engine_used')}")
        print(f"Model Used: {data.get('model_used')}")
        print(f"Warning: {data.get('warning')}")
        print(f"Script Stats: {json.dumps(data.get('script_stats'), ensure_ascii=False)}")
        print("\n--- Extracted Kannada Text ---")
        print(data.get("text"))
        results.append({
            "title": title,
            "filename": fname,
            "path": full_path,
            "text": data.get("text"),
            "stats": data.get("script_stats"),
            "warning": data.get("warning")
        })
    else:
        print(f"Error: {res.text}")
    import time
    time.sleep(5)

print("=" * 80)
print(f"Completed testing all {len(results)} samples.")
