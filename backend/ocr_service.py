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
    "6. ILLEGIBLE PARTS: For any unreadable, smudged, or blurred characters, numbers, or seals, write [illegible].\n"
    "7. PRESERVE LAYOUT: Preserve original line breaks, paragraphs, bullet points, headers, and document structure.\n"
    "8. RAW OUTPUT ONLY: Output ONLY the transcribed text directly. Do NOT include markdown code fences, conversational greetings, or explanations."
)

KANNADA_OCR_RETRY_PROMPT = (
    "CRITICAL CORRECTION REQUIRED:\n"
    "The previous transcription contained incorrect script (e.g. Devanagari script instead of Kannada, or Latin transliteration).\n"
    "Transcribe exactly what is visible in the document image, in Kannada Unicode characters ONLY (U+0C80 to U+0CFF).\n"
    "NEVER transliterate into Devanagari (e.g. NEVER write 'कर्नाटक', ALWAYS write 'ಕರ್ನಾಟಕ') or Latin.\n"
    "NEVER translate into English or Hindi. NEVER invent text.\n"
    "Write [illegible] for any unreadable parts.\n"
    "Output ONLY the exact transcribed text in authentic Kannada Unicode directly."
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
    def extract_text(self, image_bytes: bytes) -> Dict[str, Any]:
        """Extracts Kannada Unicode text from image bytes."""
        pass

    @abstractmethod
    def translate_text(self, kannada_text: str, target_lang: str) -> Dict[str, Any]:
        """Translates Kannada text to target_lang ('en' or 'hi')."""
        pass

# ==============================================================================
# 1. Google Gemini Engine
# ==============================================================================

class GeminiEngine(BaseOCREngine):
    @property
    def engine_name(self) -> str:
        return "gemini"

    def __init__(self):
        self._refresh_config()

    def _refresh_config(self):
        load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)
        self.api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.model_name = os.getenv("GEMINI_MODEL", "").strip()
        self._client = None
        self._legacy_model = None

        if self.api_key and self.model_name:
            # Try google.genai
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
                return
            except ImportError:
                pass

            # Fallback to google.generativeai
            try:
                import google.generativeai as genai_legacy
                genai_legacy.configure(api_key=self.api_key)
                self._legacy_model = genai_legacy.GenerativeModel(self.model_name)
            except ImportError:
                pass

    def check_ready(self) -> Dict[str, Any]:
        self._refresh_config()
        if not self.api_key:
            return {
                "ready": False,
                "engine": self.engine_name,
                "model": self.model_name or "Not configured",
                "error": "GEMINI_API_KEY is not configured in backend/.env"
            }
        if not self.model_name:
            return {
                "ready": False,
                "engine": self.engine_name,
                "model": "Not configured",
                "error": "GEMINI_MODEL is not configured in backend/.env"
            }
        return {
            "ready": True,
            "engine": self.engine_name,
            "model": self.model_name
        }

    def extract_text(self, image_bytes: bytes) -> Dict[str, Any]:
        ready = self.check_ready()
        if not ready["ready"]:
            return {"success": False, "error": ready["error"], "status_code": 400, "engine": self.engine_name}

        try:
            image = Image.open(io.BytesIO(image_bytes))
        except Exception as e:
            return {"success": False, "error": f"Invalid image file: {str(e)}", "status_code": 400, "engine": self.engine_name}

        try:
            raw_text = ""
            if self._client:
                response = self._client.models.generate_content(
                    model=self.model_name,
                    contents=[KANNADA_OCR_PROMPT, image]
                )
                raw_text = response.text or ""
            elif self._legacy_model:
                response = self._legacy_model.generate_content([KANNADA_OCR_PROMPT, image])
                raw_text = response.text or ""
            else:
                return {
                    "success": False,
                    "error": "Gemini SDK (google-genai or google-generativeai) is not available.",
                    "status_code": 500,
                    "engine": self.engine_name
                }

            text = clean_llm_output(raw_text)

            # Script distribution post-check
            script_stats = analyze_script_distribution(text)

            # Retry once if Devanagari share > 5% or almost no Kannada
            if script_stats["has_script_issue"]:
                try:
                    retry_raw = ""
                    if self._client:
                        resp = self._client.models.generate_content(
                            model=self.model_name,
                            contents=[KANNADA_OCR_RETRY_PROMPT, image]
                        )
                        retry_raw = resp.text or ""
                    elif self._legacy_model:
                        resp = self._legacy_model.generate_content([KANNADA_OCR_RETRY_PROMPT, image])
                        retry_raw = resp.text or ""

                    retry_text = clean_llm_output(retry_raw)
                    retry_stats = analyze_script_distribution(retry_text)
                    if retry_stats["kannada_share"] >= script_stats["kannada_share"]:
                        text = retry_text
                        script_stats = retry_stats
                except Exception as retry_err:
                    print(f"[GeminiEngine] Script validation retry failed: {retry_err}")

            word_count, char_count = count_words_and_chars(text)
            return {
                "success": True,
                "text": text,
                "word_count": word_count,
                "char_count": char_count,
                "engine": self.engine_name,
                "model_used": self.model_name,
                "warning": script_stats.get("warning"),
                "script_stats": script_stats
            }
        except Exception as e:
            err = str(e)
            if "429" in err or "RESOURCE_EXHAUSTED" in err or "quota" in err.lower():
                return {
                    "success": False,
                    "error": (
                        "Gemini API ದರ ಮಿತಿ ತಲುಪಿದೆ (Gemini API rate limit or quota exceeded). "
                        "ದಯವಿಟ್ಟು 30 ಸೆಕೆಂಡುಗಳ ನಂತರ ಪುನಃ ಪ್ರಯತ್ನಿಸಿ (Please retry in 30s) or check your Google AI Studio quota."
                    ),
                    "is_rate_limit": True,
                    "status_code": 429,
                    "engine": self.engine_name
                }
            return {
                "success": False,
                "error": f"Gemini OCR error: {err}",
                "status_code": 500,
                "engine": self.engine_name
            }

    def translate_text(self, kannada_text: str, target_lang: str) -> Dict[str, Any]:
        ready = self.check_ready()
        if not ready["ready"]:
            return {"success": False, "error": ready["error"], "status_code": 400, "engine": self.engine_name}

        prompt = build_translation_prompt(kannada_text, target_lang)
        try:
            raw_text = ""
            if self._client:
                response = self._client.models.generate_content(
                    model=self.model_name,
                    contents=[prompt]
                )
                raw_text = response.text or ""
            elif self._legacy_model:
                response = self._legacy_model.generate_content(prompt)
                raw_text = response.text or ""

            translation = clean_llm_output(raw_text)
            return {
                "success": True,
                "translation": translation,
                "target_lang": target_lang,
                "engine": self.engine_name,
                "model_used": self.model_name
            }
        except Exception as e:
            err = str(e)
            if "429" in err or "RESOURCE_EXHAUSTED" in err or "quota" in err.lower():
                return {
                    "success": False,
                    "error": "Gemini API ದರ ಮಿತಿ ತಲುಪಿದೆ (Rate limit reached). Please wait a moment and retry.",
                    "is_rate_limit": True,
                    "status_code": 429,
                    "engine": self.engine_name
                }
            return {
                "success": False,
                "error": f"Gemini translation error: {err}",
                "status_code": 500,
                "engine": self.engine_name
            }

# ==============================================================================
# 2. Groq Engine (OpenAI-Compatible Vision & Text Models)
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

    def extract_text(self, image_bytes: bytes) -> Dict[str, Any]:
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

        endpoint = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.vision_model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": KANNADA_OCR_PROMPT},
                        {"type": "image_url", "image_url": {"url": image_data_uri}}
                    ]
                }
            ],
            "temperature": 0.1
        }

        try:
            with httpx.Client(timeout=60.0) as client:
                res = client.post(endpoint, headers=headers, json=payload)
                if res.status_code == 429:
                    # Automatic retry after backoff
                    retry_after = res.headers.get("retry-after")
                    wait_time = float(retry_after) if retry_after and retry_after.isdigit() else 6.0
                    time.sleep(min(wait_time, 15.0))
                    res = client.post(endpoint, headers=headers, json=payload)

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

            data = res.json()
            raw_text = data["choices"][0]["message"]["content"]
            text = clean_llm_output(raw_text)

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
                    "temperature": 0.05
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
            return {"success": False, "error": ready["error"], "status_code": 400, "engine": self.engine_name}

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
# 3. Tesseract Offline Engine (pytesseract + OpenCV preprocessing)
# ==============================================================================

class TesseractEngine(BaseOCREngine):
    @property
    def engine_name(self) -> str:
        return "tesseract"

    def __init__(self):
        self._refresh_config()

    def _refresh_config(self):
        self.tesseract_cmd = os.getenv("TESSERACT_CMD", "").strip()
        self.tessdata_prefix = os.getenv("TESSDATA_PREFIX", "").strip()
        self._pytesseract_available = False
        self._cv2_available = False

        try:
            import pytesseract
            self.pytesseract = pytesseract
            self._pytesseract_available = True
            
            # Configure custom command path if provided or common Windows paths
            if self.tesseract_cmd and os.path.exists(self.tesseract_cmd):
                self.pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd
            else:
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

        if self.tessdata_prefix:
            os.environ["TESSDATA_PREFIX"] = self.tessdata_prefix

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
            # Check available languages
            langs = self.pytesseract.get_languages()
            has_kannada = "kan" in langs
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

    def extract_text(self, image_bytes: bytes) -> Dict[str, Any]:
        ready = self.check_ready()
        if not ready["ready"]:
            return {"success": False, "error": ready["error"], "status_code": 400, "engine": self.engine_name}

        try:
            processed_img = self._preprocess_image(image_bytes)
            # Custom tesseract config for Indic text
            custom_config = r"--oem 1 --psm 6"
            raw_text = self.pytesseract.image_to_string(processed_img, lang="kan", config=custom_config)
            
            clean_text = raw_text.strip()
            script_stats = analyze_script_distribution(clean_text)
            word_count, char_count = count_words_and_chars(clean_text)

            return {
                "success": True,
                "text": clean_text,
                "word_count": word_count,
                "char_count": char_count,
                "engine": self.engine_name,
                "model_used": "tesseract-kan",
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
        """Tesseract is an offline OCR engine and cannot translate. Delegates to Gemini or Groq if available."""
        # Check if Gemini or Groq is configured
        gemini = GeminiEngine()
        if gemini.check_ready()["ready"]:
            return gemini.translate_text(kannada_text, target_lang)

        groq = GroqEngine()
        if groq.check_ready()["ready"]:
            return groq.translate_text(kannada_text, target_lang)

        return {
            "success": False,
            "error": "Tesseract is an offline OCR engine and does not support translation. Please configure GEMINI_API_KEY or GROQ_API_KEY in backend/.env for translation.",
            "status_code": 400,
            "engine": self.engine_name
        }

# ==============================================================================
# Unified OCR Engine Manager
# ==============================================================================

class UnifiedOCRManager:
    def __init__(self):
        self.engines: Dict[str, BaseOCREngine] = {
            "gemini": GeminiEngine(),
            "groq": GroqEngine(),
            "tesseract": TesseractEngine()
        }

    def get_configured_engine_name(self) -> str:
        load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)
        return os.getenv("OCR_ENGINE", "gemini").strip().lower()

    def get_engine(self, engine_name: Optional[str] = None) -> BaseOCREngine:
        name = (engine_name or self.get_configured_engine_name()).lower()
        if name not in self.engines:
            # Fallback to gemini if unrecognized
            name = "gemini"
        return self.engines[name]

    def check_all_engines(self) -> Dict[str, Any]:
        """Returns readiness and configuration status for every engine."""
        return {name: eng.check_ready() for name, eng in self.engines.items()}

    def extract_text(self, image_bytes: bytes, engine_name: Optional[str] = None) -> Dict[str, Any]:
        engine = self.get_engine(engine_name)
        return engine.extract_text(image_bytes)

    def translate_text(self, kannada_text: str, target_lang: str, engine_name: Optional[str] = None) -> Dict[str, Any]:
        engine = self.get_engine(engine_name)
        return engine.translate_text(kannada_text, target_lang)

    def check_ready(self, engine_name: Optional[str] = None) -> Dict[str, Any]:
        return self.get_engine(engine_name).check_ready()

# Singleton manager instance
ocr_manager = UnifiedOCRManager()
ocr_service = ocr_manager

