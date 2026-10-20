import os
import io
import re
import base64
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from PIL import Image
from dotenv import load_dotenv
import httpx

load_dotenv()

# ==============================================================================
# Helper Prompts for Kannada OCR & Translation
# ==============================================================================

KANNADA_OCR_PROMPT = (
    "You are an expert Kannada OCR and Document AI digitizer.\n"
    "Your task is to transcribe exactly what is visible in this document image.\n\n"
    "CRITICAL SCRIPT & ACCURACY RULES:\n"
    "1. SCRIPT REQUIREMENT: Transcribe in authentic Kannada Unicode characters ONLY (U+0C80 to U+0CFF).\n"
    "2. NO DEVANAGARI: NEVER transliterate or output in Devanagari script (e.g. NEVER write 'कर्नाटक' or Hindi letters). Always use authentic Kannada script (e.g. 'ಕರ್ನಾಟಕ').\n"
    "3. NO LATIN TRANSLITERATION: NEVER transliterate Kannada words into Latin/English alphabet. Only preserve Latin characters for existing English terms, reference codes, or acronyms directly printed in the image (e.g. 'BEO', 'PDO', 'SAMPLE', 'ED-2026').\n"
    "4. NO TRANSLATION: NEVER translate Kannada into English, Hindi, or any other language. Transcribe verbatim in Kannada.\n"
    "5. NO INVENTION: NEVER invent, extrapolate, or hallucinate text that is not clearly visible in the document.\n"
    "6. TRANSCRIBE ONLY, NEVER SUMMARIZE OR COMPLETE: Copy ONLY the characters physically visible, in the order they appear. NEVER summarize, paraphrase, complete, continue, or generate plausible-sounding sentences, list items, numbers, or dates. If a word, sentence, list item, number, or date is cut off, partial, or uncertain, transcribe only the clearly visible characters and write [illegible] for the uncertain remainder. Do not invent a likely ending.\n"
    "7. ILLEGIBLE PARTS: For any unreadable, smudged, or blurred characters, numbers, or seals, write [illegible].\n"
    "8. PRESERVE LAYOUT: Preserve original line breaks, paragraphs, bullet points, headers, and document structure. Keep numbered and bulleted lists exactly as shown, including their original numbering - never drop, merge, or renumber list items.\n"
    "9. RAW OUTPUT ONLY: Output ONLY the transcribed text directly. Do NOT include markdown code fences, conversational greetings, or explanations."
)

KANNADA_OCR_RETRY_PROMPT = (
    "CRITICAL CORRECTION REQUIRED:\n"
    "The previous transcription contained incorrect script (e.g. Devanagari script instead of Kannada, or Latin transliteration).\n"
    "Transcribe exactly what is visible in the document image, in Kannada Unicode characters ONLY (U+0C80 to U+0CFF).\n"
    "NEVER transliterate into Devanagari (e.g. NEVER write 'कर्नाटक', ALWAYS write 'ಕರ್ನಾಟಕ') or Latin.\n"
    "NEVER translate into English or Hindi. NEVER invent, summarize, complete, or extrapolate any text.\n"
    "Copy ONLY the visible characters in order; write [illegible] wherever text is uncertain or partially visible.\n"
    "Output ONLY the exact transcribed text in authentic Kannada Unicode directly."
)

KANNADA_HANDWRITING_PROMPT = (
    "You are an expert Kannada handwriting recognizer.\n"
    "The image contains HANDWRITTEN Kannada text (pen on paper, possibly with slant, "
    "irregular spacing, connected strokes, or light pressure).\n\n"
    "CRITICAL HANDWRITING RULES:\n"
    "1. Transcribe in authentic Kannada Unicode characters ONLY (U+0C80 to U+0CFF).\n"
    "2. Handwritten Kannada often has fused/merged aksharas — reconstruct the intended "
    "consonant+vowel combinations carefully (e.g. ಕ + ಿ = ಕಿ, conjuncts like ಕ್ಷ, ಜ್ಞ).\n"
    "3. Watch for matras (vowel signs) written above/below/around the base letter — "
    "they are part of the same akshara, not separate characters.\n"
    "4. NEVER output Devanagari or Latin transliteration. Preserve Latin only for "
    "printed English words, codes, or dates actually visible in the image.\n"
    "5. NEVER invent text. Transcribe ONLY visible characters in reading order.\n"
    "6. For unclear, smudged, or broken pen strokes write [illegible].\n"
    "7. Preserve line breaks as written. Do not normalize or reorder lines.\n"
    "8. Output ONLY the transcribed text — no greetings, no markdown fences, no explanations."
)

def analyze_script_distribution(text: str) -> Dict[str, Any]:
    """
    Counts characters per script:
    - Kannada: U+0C80 to U+0CFF
    - Devanagari: U+0900 to U+097F
    - Latin: ASCII A-Z, a-z
    - Other alphabetical characters
    Evaluates if Devanagari share > 5% or if there is almost no Kannada when text is present.
    """
    kannada_count = 0
    devanagari_count = 0
    latin_count = 0
    other_alpha_count = 0

    for ch in text:
        code = ord(ch)
        if 0x0C80 <= code <= 0x0CFF:
            kannada_count += 1
        elif 0x0900 <= code <= 0x097F:
            devanagari_count += 1
        elif (0x0041 <= code <= 0x005A) or (0x0061 <= code <= 0x007A):
            latin_count += 1
        elif ch.isalpha():
            other_alpha_count += 1

    total_letters = kannada_count + devanagari_count + latin_count + other_alpha_count
    devanagari_share = (devanagari_count / total_letters) if total_letters > 0 else 0.0
    kannada_share = (kannada_count / total_letters) if total_letters > 0 else 0.0

    has_script_issue = False
    warning = None

    if total_letters > 0:
        if devanagari_share > 0.05:
            has_script_issue = True
            warning = (
                f"ಲಿಪಿ ಎಚ್ಚರಿಕೆ / Script Validation Warning: Devanagari script detected ({devanagari_share * 100:.1f}%). "
                f"Document text must be in authentic Kannada Unicode (U+0C80–U+0CFF)."
            )
        elif total_letters >= 5 and (kannada_count == 0 or kannada_share < 0.10):
            has_script_issue = True
            warning = (
                f"ಲಿಪಿ ಎಚ್ಚರಿಕೆ / Script Validation Warning: Almost no Kannada script detected ({kannada_share * 100:.1f}%). "
                f"Expected Kannada Unicode (U+0C80–U+0CFF)."
            )

    return {
        "total_letters": total_letters,
        "kannada_count": kannada_count,
        "devanagari_count": devanagari_count,
        "latin_count": latin_count,
        "devanagari_share": round(devanagari_share, 4),
        "kannada_share": round(kannada_share, 4),
        "has_script_issue": has_script_issue,
        "warning": warning
    }

def build_translation_prompt(kannada_text: str, target_lang: str) -> str:
    lang_name = "English" if target_lang.lower() == "en" else "Hindi"
    return (
        f"You are a professional translator specializing in Kannada documents. "
        f"Translate the following Kannada text accurately into natural, clear {lang_name}.\n\n"
        f"RULES:\n"
        f"1. Preserve original paragraph structure, bullet points, numbers, and dates.\n"
        f"2. Keep official terminology and proper names accurate.\n"
        f"3. Do NOT add preamble or meta-commentary. Output only the translated {lang_name} text directly.\n\n"
        f"KANNADA TEXT:\n{kannada_text}"
    )

def clean_llm_output(text: str) -> str:
    """Removes stray markdown fences, XML tags, or quotes that LLMs might wrap text with."""
    cleaned = re.sub(r"^```[a-zA-Z]*\n?", "", text.strip())
    cleaned = re.sub(r"\n?```$", "", cleaned).strip()
    cleaned = re.sub(r"</?(?:transcription|transcription_start|transcription_end|kannada_ocr|ocr)[^>]*>", "", cleaned, flags=re.IGNORECASE).strip()
    return cleaned

def count_words_and_chars(text: str) -> tuple[int, int]:
    words = [w for w in text.split() if w]
    return len(words), len(text)

# Translation runs on the optional Groq text model; OCR never needs it.
TRANSLATION_NEEDS_GROQ_KEY = (
    "Translation needs the optional Groq key. "
    "Set GROQ_API_KEY in backend/.env (or the Render dashboard) to enable "
    "Kannada to English/Hindi translation. OCR works without it."
)

# Zero-width joiners that confuse word counting, search and screen readers
ZERO_WIDTH_JOINERS = "\u200c\u200d"

def strip_zero_width_joiners(text: str) -> str:
    """Removes U+200C (ZWNJ) and U+200D (ZWJ) from extracted text."""
    return text.translate({ord(ch): None for ch in ZERO_WIDTH_JOINERS})

def illegible_ratio(text: str) -> float:
    """Share of output words that are the '[illegible]' placeholder marker."""
    markers = len(re.findall(r"\[illegible\]", text, flags=re.IGNORECASE))
    tokens = len(text.split())
    return (markers / tokens) if tokens else 0.0

# ==============================================================================
# OCR Input Preprocessing: upscale + horizontal strip splitting
# ==============================================================================

MIN_UPSCALE_WIDTH = 1400       # small images are upscaled to at least this width
LINES_PER_STRIP = 7            # target 6-8 lines per strip
STRIP_OVERLAP_LINES = 1        # one line of overlap between consecutive strips
STRIP_PAD_PX = 10              # vertical padding around each strip crop

def upscale_if_small(image: Image.Image) -> Image.Image:
    """Upscale small images so thin Kannada glyphs stay legible for vision models."""
    if image.width < MIN_UPSCALE_WIDTH:
        factor = MIN_UPSCALE_WIDTH / float(image.width)
        image = image.resize(
            (max(1, int(image.width * factor)), max(1, int(image.height * factor))),
            Image.LANCZOS,
        )
    return image

def detect_text_line_bands(image: Image.Image) -> list:
    """Detect horizontal text-line bands via dark-pixel row projection.
    Returns [(top, bottom), ...] in pixels. Empty list if detection fails."""
    try:
        import numpy as np
    except ImportError:
        return []

    gray = np.asarray(image.convert("L"))
    dark_rows = (gray < 200).sum(axis=1)
    # ~1.5% of width: high enough to ignore page-border columns,
    # low enough to catch sparse text rows (matras/descenders)
    threshold = max(5, int(image.width * 0.015))
    is_text = dark_rows > threshold

    bands = []
    start = None
    for idx, flag in enumerate(is_text):
        if flag and start is None:
            start = idx
        elif not flag and start is not None:
            bands.append([start, idx])
            start = None
    if start is not None:
        bands.append([start, len(is_text)])

    # Merge bands separated by tiny gaps (within a line) and drop noise specks
    merged = []
    for band in bands:
        if merged and band[0] - merged[-1][1] < 6:
            merged[-1][1] = band[1]
        else:
            merged.append(band)
    return [(top, bottom) for top, bottom in merged if bottom - top >= 4]

def prepare_ocr_strips(image: Image.Image) -> list:
    """Upscale if small, then split tall multi-line documents into overlapping
    horizontal strips of 6-8 text lines for per-strip OCR. Returns a list of
    images (a single upscaled image when no split is needed)."""
    image = upscale_if_small(image)
    bands = detect_text_line_bands(image)
    if len(bands) <= LINES_PER_STRIP + 2:
        return [image]

    strips = []
    idx = 0
    while idx < len(bands):
        chunk = bands[idx:idx + LINES_PER_STRIP]
        top = max(0, chunk[0][0] - STRIP_PAD_PX)
        bottom = min(image.height, chunk[-1][1] + STRIP_PAD_PX)
        strips.append(image.crop((0, top, image.width, bottom)))
        if idx + LINES_PER_STRIP >= len(bands):
            break
        idx += LINES_PER_STRIP - STRIP_OVERLAP_LINES
    return strips

def _normalize_line(line: str) -> str:
    return " ".join(line.split()).lower()

def merge_strip_texts(parts: list) -> str:
    """Merge per-strip OCR texts, dropping the duplicated overlap line at strip boundaries."""
    merged: list = []
    for part in parts:
        part_lines = part.splitlines()
        while part_lines and merged and _normalize_line(part_lines[0]) == _normalize_line(merged[-1]):
            part_lines.pop(0)
        merged.extend(part_lines)
    return "\n".join(merged).strip()

# ==============================================================================
# Base OCR Engine Interface
# ==============================================================================

class BaseOCREngine(ABC):
    @property
    @abstractmethod
    def engine_name(self) -> str:
        pass

    @abstractmethod
    def check_ready(self) -> Dict[str, Any]:
        """Returns readiness, model name, and error if unconfigured."""
        pass

    @abstractmethod
    def extract_text(self, image_bytes: bytes, handwriting: bool = False) -> Dict[str, Any]:
        """Extracts Kannada Unicode text from image bytes."""
        pass

    @abstractmethod
    def translate_text(self, kannada_text: str, target_lang: str) -> Dict[str, Any]:
        """Translates Kannada text to target_lang ('en' or 'hi')."""
        pass

# ==============================================================================
# 1. Groq Engine (OpenAI-Compatible Vision & Text Models)
# ==============================================================================

class GroqEngine(BaseOCREngine):
    @property
    def engine_name(self) -> str:
        return "groq"

    def __init__(self):
        self._refresh_config()

    def _refresh_config(self):
        load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)
        self.api_key = os.getenv("GROQ_API_KEY", "").strip()
        self.vision_model = os.getenv("GROQ_VISION_MODEL", "").strip()
        self.text_model = os.getenv("GROQ_TEXT_MODEL", "").strip()
        self.base_url = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1").rstrip("/")
        try:
            self.max_tokens = int(os.getenv("GROQ_MAX_TOKENS", "4096"))
        except ValueError:
            self.max_tokens = 4096
        try:
            self.max_illegible_ratio = float(os.getenv("GROQ_MAX_ILLEGIBLE_RATIO", "0.30"))
        except ValueError:
            self.max_illegible_ratio = 0.30

    def check_ready(self) -> Dict[str, Any]:
        self._refresh_config()
        if not self.api_key:
            return {
                "ready": False,
                "engine": self.engine_name,
                "model": f"Vision: {self.vision_model or 'unset'}, Text: {self.text_model or 'unset'}",
                "error": "GROQ_API_KEY is not configured in backend/.env"
            }
        if not self.vision_model:
            return {
                "ready": False,
                "engine": self.engine_name,
                "model": "Vision model unset",
                "error": "GROQ_VISION_MODEL is not configured in backend/.env"
            }
        if not self.text_model:
            return {
                "ready": False,
                "engine": self.engine_name,
                "model": "Text model unset",
                "error": "GROQ_TEXT_MODEL is not configured in backend/.env"
            }
        return {
            "ready": True,
            "engine": self.engine_name,
            "vision_model": self.vision_model,
            "text_model": self.text_model,
            "base_url": self.base_url
        }

    def extract_text(self, image_bytes: bytes, handwriting: bool = False) -> Dict[str, Any]:
        ready = self.check_ready()
        if not ready["ready"]:
            return {"success": False, "error": ready["error"], "status_code": 400, "engine": self.engine_name}

        # Encode image to base64
        base64_img = base64.b64encode(image_bytes).decode("utf-8")
        
        # Detect mime type or default to image/jpeg
        mime_type = "image/jpeg"
        if image_bytes.startswith(b"\x89PNG"):
            mime_type = "image/png"
        elif image_bytes.startswith(b"RIFF") and b"WEBP" in image_bytes[:16]:
            mime_type = "image/webp"

        image_data_uri = f"data:{mime_type};base64,{base64_img}"
        ocr_prompt = KANNADA_HANDWRITING_PROMPT if handwriting else KANNADA_OCR_PROMPT

        endpoint = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        def _build_payload(uri: str) -> dict:
            return {
                "model": self.vision_model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": ocr_prompt},
                            {"type": "image_url", "image_url": {"url": uri}}
                        ]
                    }
                ],
                "temperature": 0.0,
                "max_tokens": self.max_tokens
            }

        # Preprocess: upscale small images; split tall documents into overlapping
        # 6-8 line strips, OCR each strip separately, then merge (dedupe overlap).
        strip_uris = [image_data_uri]
        try:
            pil_image = Image.open(io.BytesIO(image_bytes))
            strips = prepare_ocr_strips(pil_image)
            if len(strips) > 1:
                strip_uris = []
                for strip_image in strips:
                    buf = io.BytesIO()
                    strip_image.save(buf, format="PNG")
                    strip_uris.append(
                        "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("utf-8")
                    )
        except Exception as prep_err:
            print(f"[GroqEngine] Preprocessing skipped: {prep_err}")

        # Per-strip call with exponential backoff on 429 (image tokens burst TPM)
        BACKOFF_SECONDS = [5.0, 15.0, 45.0]
        try:
            strip_texts = []
            with httpx.Client(timeout=60.0) as client:
                for strip_idx, uri in enumerate(strip_uris):
                    payload = _build_payload(uri)
                    res = client.post(endpoint, headers=headers, json=payload)
                    for attempt in range(len(BACKOFF_SECONDS)):
                        if res.status_code != 429:
                            break
                        retry_after = (res.headers.get("retry-after") or "").strip()
                        try:
                            wait_time = float(retry_after) if retry_after else BACKOFF_SECONDS[attempt]
                        except ValueError:
                            wait_time = BACKOFF_SECONDS[attempt]
                        wait_time = min(wait_time, 60.0)
                        print(f"[GroqEngine] 429 rate limit — backing off {wait_time:.0f}s "
                              f"(attempt {attempt + 1}/{len(BACKOFF_SECONDS)})")
                        time.sleep(wait_time)
                        res = client.post(endpoint, headers=headers, json=payload)
                    if res.status_code != 200:
                        break  # shared error handling below uses `res`
                    data = res.json()
                    strip_texts.append(clean_llm_output(data["choices"][0]["message"]["content"]))
                    if strip_idx < len(strip_uris) - 1:
                        time.sleep(2.0)  # pace calls to stay within TPM window

            if res.status_code == 429:
                return {
                    "success": False,
                    "error": (
                        "Groq API ದರ ಮಿತಿ ತಲುಪಿದೆ (Groq API rate limit or quota exceeded). "
                        "ದಯವಿಟ್ಟು ಸ್ವಲ್ಪ ಸಮಯದ ನಂತರ ಪುನಃ ಪ್ರಯತ್ನಿಸಿ (Please retry shortly)."
                    ),
                    "is_rate_limit": True,
                    "status_code": 429,
                    "engine": self.engine_name
                }
            if res.status_code != 200:
                err_detail = res.text
                try:
                    err_json = res.json()
                    err_detail = err_json.get("error", {}).get("message", res.text)
                except Exception:
                    pass
                return {
                    "success": False,
                    "error": f"Groq Vision API Error ({res.status_code}): {err_detail}",
                    "status_code": res.status_code,
                    "engine": self.engine_name
                }

            text = merge_strip_texts(strip_texts)

            # Script distribution post-check
            script_stats = analyze_script_distribution(text)

            # Retry once if Devanagari share > 5% or almost no Kannada
            if script_stats["has_script_issue"]:
                retry_payload = {
                    "model": self.vision_model,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": KANNADA_OCR_RETRY_PROMPT},
                                {"type": "image_url", "image_url": {"url": image_data_uri}}
                            ]
                        }
                    ],
                    "temperature": 0.0,
                    "max_tokens": self.max_tokens
                }
                try:
                    with httpx.Client(timeout=60.0) as client:
                        retry_res = client.post(endpoint, headers=headers, json=retry_payload)
                        if retry_res.status_code == 429:
                            time.sleep(5.0)
                            retry_res = client.post(endpoint, headers=headers, json=retry_payload)
                        if retry_res.status_code == 200:
                            retry_data = retry_res.json()
                            retry_raw = retry_data["choices"][0]["message"]["content"]
                            retry_text = clean_llm_output(retry_raw)
                            retry_stats = analyze_script_distribution(retry_text)
                            if (retry_stats["kannada_share"] >= script_stats["kannada_share"] or 
                                retry_stats["devanagari_share"] <= script_stats["devanagari_share"]):
                                text = retry_text
                                script_stats = retry_stats
                except Exception as retry_err:
                    print(f"[GroqEngine] Script validation retry failed: {retry_err}")

            # Abort when the model read almost nothing and filled the page with
            # [illegible] placeholders — better to fail loudly than ship garbage.
            ratio = illegible_ratio(text)
            if ratio > self.max_illegible_ratio:
                return {
                    "success": False,
                    "error": (
                        f"Groq output rejected: {ratio * 100:.1f}% of the transcription is "
                        f"[illegible] (limit {self.max_illegible_ratio * 100:.0f}%). "
                        "The model could not reliably read this document."
                    ),
                    "status_code": 422,
                    "engine": self.engine_name,
                    "is_low_confidence": True,
                    "illegible_ratio": round(ratio, 4),
                    "text": text
                }

            word_count, char_count = count_words_and_chars(text)

            return {
                "success": True,
                "text": text,
                "word_count": word_count,
                "char_count": char_count,
                "engine": self.engine_name,
                "model_used": self.vision_model,
                "warning": script_stats.get("warning"),
                "script_stats": script_stats
            }
        except httpx.TimeoutException:
            return {
                "success": False,
                "error": "Groq API request timed out. Please try again.",
                "status_code": 504,
                "engine": self.engine_name
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Groq OCR error: {str(e)}",
                "status_code": 500,
                "engine": self.engine_name
            }

    def translate_text(self, kannada_text: str, target_lang: str) -> Dict[str, Any]:
        ready = self.check_ready()
        if not ready["ready"]:
            # Missing API key is the common, fixable case — say exactly what's needed
            error = TRANSLATION_NEEDS_GROQ_KEY if not self.api_key else ready["error"]
            return {"success": False, "error": error, "status_code": 400, "engine": self.engine_name}

        prompt = build_translation_prompt(kannada_text, target_lang)
        endpoint = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.text_model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2
        }

        try:
            with httpx.Client(timeout=45.0) as client:
                res = client.post(endpoint, headers=headers, json=payload)
                if res.status_code == 429:
                    time.sleep(3.0)
                    res = client.post(endpoint, headers=headers, json=payload)

            if res.status_code == 429:
                return {
                    "success": False,
                    "error": "Groq API ದರ ಮಿತಿ ತಲುಪಿದೆ (Groq rate limit exceeded). Please wait a moment and retry.",
                    "is_rate_limit": True,
                    "status_code": 429,
                    "engine": self.engine_name
                }
            if res.status_code != 200:
                err_detail = res.text
                try:
                    err_json = res.json()
                    err_detail = err_json.get("error", {}).get("message", res.text)
                except Exception:
                    pass
                return {
                    "success": False,
                    "error": f"Groq Text API Error ({res.status_code}): {err_detail}",
                    "status_code": res.status_code,
                    "engine": self.engine_name
                }

            data = res.json()
            raw_text = data["choices"][0]["message"]["content"]
            translation = clean_llm_output(raw_text)

            return {
                "success": True,
                "translation": translation,
                "target_lang": target_lang,
                "engine": self.engine_name,
                "model_used": self.text_model
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Groq translation error: {str(e)}",
                "status_code": 500,
                "engine": self.engine_name
            }

# ==============================================================================
# 2. Tesseract Offline Engine (pytesseract + OpenCV preprocessing)
# ==============================================================================

class TesseractEngine(BaseOCREngine):
    @property
    def engine_name(self) -> str:
        return "tesseract"

    def __init__(self):
        self._refresh_config()

    def _refresh_config(self):
        # Load backend/.env explicitly so TESSERACT_CMD / TESSDATA_PREFIX are read
        # no matter which directory the process was started from.
        load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)
        self.tesseract_cmd = os.getenv("TESSERACT_CMD", "").strip()
        self.tessdata_prefix = os.getenv("TESSDATA_PREFIX", "").strip()
        try:
            self.default_psm = int(os.getenv("TESSERACT_PSM", "6"))
        except ValueError:
            self.default_psm = 6
        self._pytesseract_available = False
        self._cv2_available = False

        try:
            import pytesseract
            self.pytesseract = pytesseract
            self._pytesseract_available = True

            # Point pytesseract at the binary configured in .env (TESSERACT_CMD)
            if self.tesseract_cmd and os.path.isfile(self.tesseract_cmd):
                self.pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd
            else:
                if self.tesseract_cmd:
                    print(f"[TesseractEngine] TESSERACT_CMD not found: {self.tesseract_cmd}")
                common_paths = [
                    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"
                ]
                for p in common_paths:
                    if os.path.exists(p):
                        self.pytesseract.pytesseract.tesseract_cmd = p
                        self.tesseract_cmd = p
                        break
        except ImportError:
            self.pytesseract = None

        # Only publish a TESSDATA_PREFIX that actually exists; a stale/invalid
        # value hides valid language data (e.g. kan.traineddata) from Tesseract.
        if self.tessdata_prefix:
            if os.path.isdir(self.tessdata_prefix):
                os.environ["TESSDATA_PREFIX"] = self.tessdata_prefix
            else:
                print(f"[TesseractEngine] TESSDATA_PREFIX does not exist: {self.tessdata_prefix}")
                os.environ.pop("TESSDATA_PREFIX", None)
        elif os.environ.get("TESSDATA_PREFIX") and not os.path.isdir(os.environ["TESSDATA_PREFIX"]):
            os.environ.pop("TESSDATA_PREFIX", None)

        try:
            import cv2
            import numpy as np
            self.cv2 = cv2
            self.np = np
            self._cv2_available = True
        except ImportError:
            self.cv2 = None
            self.np = None

    def check_ready(self) -> Dict[str, Any]:
        self._refresh_config()
        if not self._pytesseract_available:
            return {
                "ready": False,
                "engine": self.engine_name,
                "model": "tesseract-kan",
                "error": "pytesseract Python package is not installed."
            }
        if not self._cv2_available:
            return {
                "ready": False,
                "engine": self.engine_name,
                "model": "tesseract-kan",
                "error": "opencv-python package is not installed."
            }

        # Check binary availability
        try:
            ver = self.pytesseract.get_tesseract_version()
            # Check available languages (names may be prefixed with a path)
            langs = self.pytesseract.get_languages(config="")
            has_kannada = any(
                lang.strip().lower() == "kan" or lang.replace("\\", "/").rstrip("/").endswith("/kan")
                for lang in langs
            )
            if not has_kannada:
                return {
                    "ready": False,
                    "engine": self.engine_name,
                    "model": f"tesseract-{ver}",
                    "error": (
                        "Tesseract binary found, but 'kan' (Kannada) language data is missing. "
                        "Please download kan.traineddata to your tessdata directory."
                    )
                }
            return {
                "ready": True,
                "engine": self.engine_name,
                "model": f"tesseract-v{ver} (kan)",
                "tesseract_cmd": self.tesseract_cmd or "system PATH"
            }
        except Exception as e:
            return {
                "ready": False,
                "engine": self.engine_name,
                "model": "tesseract-kan",
                "error": (
                    f"Tesseract binary not found or inaccessible: {str(e)}. "
                    "Please install Tesseract-OCR with Kannada data or set TESSERACT_CMD in backend/.env"
                )
            }

    def _preprocess_image(self, image_bytes: bytes):
        """Applies OpenCV grayscale, rescale, Gaussian denoise, and Otsu binarization."""
        nparr = self.np.frombuffer(image_bytes, self.np.uint8)
        img = self.cv2.imdecode(nparr, self.cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("OpenCV failed to decode image bytes.")

        # 1. Grayscale
        gray = self.cv2.cvtColor(img, self.cv2.COLOR_BGR2GRAY)

        # 2. Rescale/upscale if width is smaller than 1200px (improves Indic OCR accuracy significantly)
        h, w = gray.shape[:2]
        if w < 1200:
            scale = 1200 / float(w)
            gray = self.cv2.resize(gray, (int(w * scale), int(h * scale)), interpolation=self.cv2.INTER_CUBIC)

        # 3. Denoise with Gaussian blur
        denoised = self.cv2.GaussianBlur(gray, (3, 3), 0)

        # 4. Otsu's optimal binarization
        _, thresh = self.cv2.threshold(denoised, 0, 255, self.cv2.THRESH_BINARY + self.cv2.THRESH_OTSU)
        return thresh

    def _preprocess_handwriting(self, image_bytes: bytes):
        """Handwriting-tuned pipeline: aggressive upscale, CLAHE contrast,
        adaptive threshold (handles uneven pen pressure), deskew, and a light
        morphological close to reconnect broken pen strokes."""
        nparr = self.np.frombuffer(image_bytes, self.np.uint8)
        img = self.cv2.imdecode(nparr, self.cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("OpenCV failed to decode image bytes.")

        gray = self.cv2.cvtColor(img, self.cv2.COLOR_BGR2GRAY)

        # Handwritten notes are often small phone photos — upscale harder than print mode
        h, w = gray.shape[:2]
        if w < 1600:
            scale = 1600 / float(w)
            gray = self.cv2.resize(gray, (int(w * scale), int(h * scale)), interpolation=self.cv2.INTER_CUBIC)

        # CLAHE evens out light/pale pen strokes against paper
        clahe = self.cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)

        # Light denoise — handwriting has thin strokes we must not erase
        denoised = self.cv2.bilateralFilter(gray, 5, 50, 50)

        # Adaptive Gaussian threshold copes with uneven lighting/pressure far
        # better than Otsu for handwriting
        block = max(15, (min(denoised.shape[:2]) // 16) | 1)
        thresh = self.cv2.adaptiveThreshold(
            denoised, 255, self.cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            self.cv2.THRESH_BINARY_INV, block, 12
        )

        # Deskew: rotate to make text lines horizontal again
        coords = self.np.column_stack(self.np.where(thresh > 0))
        if len(coords) >= 5:
            angle = self.cv2.minAreaRect(coords)[-1]
            if angle < -45:
                angle = -(90 + angle)
            else:
                angle = -angle
            if abs(angle) > 0.3 and abs(angle) < 15:
                (ch, cw) = thresh.shape[:2]
                matrix = self.cv2.getRotationMatrix2D((cw // 2, ch // 2), angle, 1.0)
                thresh = self.cv2.warpAffine(
                    thresh, matrix, (cw, ch),
                    flags=self.cv2.INTER_CUBIC,
                    borderMode=self.cv2.BORDER_REPLICATE
                )

        # Morphological close reconnects broken pen strokes without fattening glyphs much
        kernel = self.cv2.getStructuringElement(self.cv2.MORPH_RECT, (2, 2))
        thresh = self.cv2.morphologyEx(thresh, self.cv2.MORPH_CLOSE, kernel)

        # Tesseract expects white text on black for OCR of binary images;
        # invert back so glyphs are dark on light
        return self.cv2.bitwise_not(thresh)

    def extract_text(self, image_bytes: bytes, psm: Optional[int] = None, handwriting: bool = False) -> Dict[str, Any]:
        ready = self.check_ready()
        if not ready["ready"]:
            return {"success": False, "error": ready["error"], "status_code": 400, "engine": self.engine_name}

        try:
            psm_value = self.default_psm if psm is None else int(psm)
            custom_config = f"--oem 1 --psm {psm_value}"

            def _run_ocr(processed_img):
                # image_to_string for text + image_to_data for per-word confidence
                raw = self.pytesseract.image_to_string(processed_img, lang="kan", config=custom_config)
                clean = strip_zero_width_joiners(raw.strip())
                stats = analyze_script_distribution(clean)
                # Mean confidence of recognized word boxes (conf >= 0 filters noise)
                confidences = []
                try:
                    data = self.pytesseract.image_to_data(
                        processed_img, lang="kan", config=custom_config,
                        output_type=self.pytesseract.Output.DICT
                    )
                    for conf, txt in zip(data.get("conf", []), data.get("text", [])):
                        try:
                            c = float(conf)
                        except (TypeError, ValueError):
                            continue
                        if c >= 0 and (txt or "").strip():
                            confidences.append(c)
                except Exception:
                    pass
                mean_conf = sum(confidences) / len(confidences) if confidences else 0.0
                return clean, stats, mean_conf

            if handwriting:
                # Run BOTH pipelines; pick by Tesseract mean word-confidence —
                # a reliable proxy for which preprocessing produced cleaner glyphs.
                candidates = []
                for label, prep in (("handwriting", self._preprocess_handwriting), ("print", self._preprocess_image)):
                    try:
                        text, stats, conf = _run_ocr(prep(image_bytes))
                        candidates.append((label, text, stats, conf))
                    except Exception as prep_err:
                        print(f"[TesseractEngine] {label} preprocessing failed: {prep_err}")
                if not candidates:
                    raise ValueError("All preprocessing pipelines failed.")
                # Highest mean confidence wins; require some text to exist
                candidates.sort(key=lambda c: (c[3] if c[1].strip() else -1.0), reverse=True)
                mode_label, clean_text, script_stats, _conf = candidates[0]
                model_suffix = f"psm {psm_value} ({mode_label})"
            else:
                clean_text, script_stats, _conf = _run_ocr(self._preprocess_image(image_bytes))
                model_suffix = f"psm {psm_value}"

            word_count, char_count = count_words_and_chars(clean_text)

            return {
                "success": True,
                "text": clean_text,
                "word_count": word_count,
                "char_count": char_count,
                "engine": self.engine_name,
                "model_used": f"tesseract-kan ({model_suffix})",
                "warning": script_stats.get("warning"),
                "script_stats": script_stats
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Tesseract OCR processing failed: {str(e)}",
                "status_code": 500,
                "engine": self.engine_name
            }

    def translate_text(self, kannada_text: str, target_lang: str) -> Dict[str, Any]:
        """Tesseract is an offline OCR engine and cannot translate. Delegates to Groq if available."""
        groq = GroqEngine()
        ready = groq.check_ready()
        if ready["ready"]:
            return groq.translate_text(kannada_text, target_lang)

        return {
            "success": False,
            "error": TRANSLATION_NEEDS_GROQ_KEY if not groq.api_key else ready["error"],
            "status_code": 400,
            "engine": self.engine_name
        }

# ==============================================================================
# Unified OCR Engine Manager
# ==============================================================================

class UnifiedOCRManager:
    def __init__(self):
        self.engines: Dict[str, BaseOCREngine] = {
            "groq": GroqEngine(),
            "tesseract": TesseractEngine()
        }

    def get_configured_engine_name(self) -> str:
        load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)
        return os.getenv("OCR_ENGINE", "tesseract").strip().lower()

    def get_engine(self, engine_name: Optional[str] = None) -> BaseOCREngine:
        name = (engine_name or self.get_configured_engine_name()).lower()
        if name not in self.engines:
            # Default to Tesseract (offline) if the requested engine is unknown
            name = "tesseract"
        return self.engines[name]

    def check_all_engines(self) -> Dict[str, Any]:
        """Returns readiness and configuration status for every engine."""
        return {name: eng.check_ready() for name, eng in self.engines.items()}

    # If the AI (Groq) output is far larger than Tesseract's on the same image,
    # the model likely invented content — warn the user to verify.
    CROSSCHECK_CHAR_RATIO = 1.5
    CROSSCHECK_LINE_RATIO = 1.5
    CROSSCHECK_MIN_TESS_CHARS = 20
    CROSSCHECK_WARNING = "Machine-read text, please verify against the original."

    def _crosscheck_with_tesseract(self, result: Dict[str, Any], image_bytes: bytes) -> list:
        """Runs Tesseract on the same image; if the Groq output has far more
        characters or lines, returns a verification warning list. Returns []
        when Tesseract is unavailable or the check cannot run."""
        try:
            tess = self.engines.get("tesseract")
            if tess is None or not tess.check_ready().get("ready"):
                return []
            t_res = tess.extract_text(image_bytes)
            if not t_res.get("success"):
                return []

            t_text = t_res.get("text", "") or ""
            g_text = result.get("text", "") or ""
            t_chars = t_res.get("char_count", 0) or 0
            g_chars = result.get("char_count", 0) or 0
            t_lines = len([ln for ln in t_text.splitlines() if ln.strip()])
            g_lines = len([ln for ln in g_text.splitlines() if ln.strip()])

            if t_chars < self.CROSSCHECK_MIN_TESS_CHARS or t_lines == 0:
                return []

            if (g_chars > t_chars * self.CROSSCHECK_CHAR_RATIO or
                    g_lines > t_lines * self.CROSSCHECK_LINE_RATIO):
                return [self.CROSSCHECK_WARNING]
            return []
        except Exception as check_err:
            print(f"[UnifiedOCRManager] Tesseract cross-check skipped: {check_err}")
            return []

    def extract_text(self, image_bytes: bytes, engine_name: Optional[str] = None, handwriting: bool = False) -> Dict[str, Any]:
        engine = self.get_engine(engine_name)
        result = engine.extract_text(image_bytes, handwriting=handwriting)
        if result.get("success"):
            ocr_warnings = []
            if result.get("engine") == "groq":
                ocr_warnings.extend(self._crosscheck_with_tesseract(result, image_bytes))
            if handwriting:
                ocr_warnings.append(
                    "Handwriting mode active — accuracy is lower than printed text; please verify the transcription."
                )
            result["ocr_warnings"] = ocr_warnings
        return result

    def translate_text(self, kannada_text: str, target_lang: str, engine_name: Optional[str] = None) -> Dict[str, Any]:
        engine = self.get_engine(engine_name)
        return engine.translate_text(kannada_text, target_lang)

    def check_ready(self, engine_name: Optional[str] = None) -> Dict[str, Any]:
        return self.get_engine(engine_name).check_ready()

# Singleton manager instance
ocr_manager = UnifiedOCRManager()
ocr_service = ocr_manager

