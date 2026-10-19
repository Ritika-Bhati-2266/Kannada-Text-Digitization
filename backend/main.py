import os
import io
from typing import Optional
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException, Response, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from gtts import gTTS
from dotenv import load_dotenv
import pypdfium2 as pdfium

from ocr_service import ocr_manager, analyze_script_distribution, count_words_and_chars

load_dotenv()

app = FastAPI(
    title="ಕನ್ನಡ ಲಿಪಿ ಮಿತ್ರ (Kannada Lipi Mitra) API",
    description="Engine-Agnostic Kannada Document AI, OCR, Translation & Text-to-Speech API",
    version="2.0.0"
)

# CORS configuration
origins_str = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000")
allowed_origins = [o.strip() for o in origins_str.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TranslationRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Kannada text to translate")
    target_lang: str = Field(..., pattern="^(en|hi)$", description="Target language: 'en' or 'hi'")
    engine: Optional[str] = Field(None, description="Optional engine override: gemini | groq | tesseract")

class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Kannada text to convert to audio")

@app.get("/api/info")
def project_info():
    active_engine = ocr_manager.get_configured_engine_name()
    return {
        "project": "ಕನ್ನಡ ಲಿಪಿ ಮಿತ್ರ (Kannada Lipi Mitra)",
        "tagline": "Kannada Document AI & Multi-Engine OCR Engine",
        "active_engine": active_engine,
        "docs": "/docs",
        "health": "/api/health"
    }

@app.get("/api/health")
def health_check():
    """Returns backend status, active engine, and readiness of all configured engines."""
    all_status = ocr_manager.check_all_engines()
    active_engine_name = ocr_manager.get_configured_engine_name()
    active_engine_info = all_status.get(active_engine_name, {})

    return {
        "status": "online",
        "service": "kannada-lipi-mitra-backend",
        "active_engine": active_engine_name,
        "active_engine_ready": active_engine_info.get("ready", False),
        "engines": all_status
    }

MAX_PDF_PAGES = 10
PDF_RENDER_SCALE = 2.0


def _is_pdf(file: UploadFile, filename: str) -> bool:
    return (file.content_type or "").lower() == "application/pdf" or filename.lower().endswith(".pdf")


def _render_pdf_to_images(contents: bytes, max_pages: int = MAX_PDF_PAGES):
    """Render PDF pages to PNG image bytes. Returns (pages, total_page_count)."""
    pdf = pdfium.PdfDocument(contents)
    try:
        total = len(pdf)
        pages = []
        for i in range(min(total, max_pages)):
            bitmap = pdf[i].render(scale=PDF_RENDER_SCALE)
            pil_image = bitmap.to_pil().convert("RGB")
            buf = io.BytesIO()
            pil_image.save(buf, format="PNG")
            pages.append((i + 1, buf.getvalue()))
        return pages, total
    finally:
        pdf.close()


@app.post("/api/ocr")
async def extract_ocr(
    file: UploadFile = File(...),
    engine: Optional[str] = Query(None, description="Optional OCR engine override: gemini | groq | tesseract")
):
    """
    Receives a document image file (PNG/JPG/WEBP/BMP) OR a multi-page PDF
    and extracts Kannada Unicode text using the active or specified OCR engine.
    PDFs are rendered page-by-page (up to 10 pages) and transcribed with page markers.
    """
    allowed_types = ["image/jpeg", "image/png", "image/webp", "image/bmp", "image/tiff", "application/pdf"]
    if file.content_type and file.content_type.lower() not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{file.content_type}'. Please upload a PNG, JPG, WEBP image or a PDF."
        )

    try:
        contents = await file.read()
        if len(contents) == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")
        if len(contents) > 15 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File size exceeds 15MB limit.")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read file: {str(e)}")

    # ── PDF path: render pages, OCR each, concatenate with page markers ──
    if _is_pdf(file, file.filename or ""):
        try:
            pages, total_pages = _render_pdf_to_images(contents)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Could not read PDF: {str(e)}")

        if not pages:
            raise HTTPException(status_code=400, detail="PDF contains no readable pages.")

        page_texts = []
        engine_used = model_used = None
        warnings = []
        for page_no, image_bytes in pages:
            result = ocr_manager.extract_text(image_bytes, engine_name=engine)
            if not result["success"]:
                raise HTTPException(
                    status_code=result.get("status_code", 500),
                    detail={
                        "message": f"OCR failed on page {page_no}: {result['error']}",
                        "engine": result.get("engine"),
                        "is_rate_limit": result.get("is_rate_limit", False)
                    }
                )
            page_texts.append(f"—— ಪುಟ / Page {page_no} ——\n{result['text']}")
            engine_used = result.get("engine")
            model_used = result.get("model_used")
            if result.get("warning"):
                warnings.append(f"Page {page_no}: {result['warning']}")

        combined_text = "\n\n".join(page_texts)
        word_count, char_count = count_words_and_chars(combined_text)
        script_stats = analyze_script_distribution(combined_text)

        return {
            "filename": file.filename,
            "text": combined_text,
            "word_count": word_count,
            "char_count": char_count,
            "engine_used": engine_used,
            "model_used": model_used,
            "warning": warnings[0] if warnings else None,
            "script_stats": script_stats,
            "page_count": total_pages,
            "pages_processed": len(pages)
        }

    # ── Single-image path ──
    result = ocr_manager.extract_text(contents, engine_name=engine)

    if not result["success"]:
        status_code = result.get("status_code", 500)
        raise HTTPException(
            status_code=status_code,
            detail={
                "message": result["error"],
                "engine": result.get("engine", engine or ocr_manager.get_configured_engine_name()),
                "is_rate_limit": result.get("is_rate_limit", False)
            }
        )

    return {
        "filename": file.filename,
        "text": result["text"],
        "word_count": result["word_count"],
        "char_count": result["char_count"],
        "engine_used": result.get("engine"),
        "model_used": result.get("model_used"),
        "warning": result.get("warning"),
        "script_stats": result.get("script_stats")
    }

@app.post("/api/translate")
def translate_kannada(payload: TranslationRequest):
    """
    On-demand translation of current Kannada text into English ('en') or Hindi ('hi').
    Uses active engine or specified engine (gemini or groq).
    """
    result = ocr_manager.translate_text(payload.text, payload.target_lang, engine_name=payload.engine)

    if not result["success"]:
        status_code = result.get("status_code", 500)
        raise HTTPException(
            status_code=status_code,
            detail={
                "message": result["error"],
                "engine": result.get("engine", payload.engine or ocr_manager.get_configured_engine_name()),
                "is_rate_limit": result.get("is_rate_limit", False)
            }
        )

    return {
        "translation": result["translation"],
        "target_lang": result["target_lang"],
        "engine_used": result.get("engine"),
        "model_used": result.get("model_used")
    }

@app.post("/api/tts")
def text_to_speech_kannada(payload: TTSRequest):
    """
    Fallback Kannada Text-to-Speech using gTTS with lang='kn'.
    Ensures that if the user's browser lacks a native Kannada voice,
    authentic Kannada spoken audio is streamed without English voice corruption.
    """
    clean_text = payload.text.strip()
    if not clean_text:
        raise HTTPException(status_code=400, detail="Text cannot be empty.")

    if len(clean_text) > 3000:
        clean_text = clean_text[:3000]

    try:
        mp3_fp = io.BytesIO()
        tts = gTTS(text=clean_text, lang="kn", slow=False)
        tts.write_to_fp(mp3_fp)
        mp3_fp.seek(0)

        return Response(
            content=mp3_fp.read(),
            media_type="audio/mpeg",
            headers={"Content-Disposition": "inline; filename=kannada_speech.mp3"}
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Kannada TTS generation failed: {str(e)}"
        )

# ==============================================================================
# Static Files & Frontend Serving
# ==============================================================================
FRONTEND_ROOT = Path(__file__).resolve().parent.parent / "frontend"
_DIST_DIR = FRONTEND_ROOT / "dist"
# Prefer the production Vite build (frontend/dist) when it exists; fall back to source files.
FRONTEND_DIR = _DIST_DIR if (_DIST_DIR / "index.html").exists() else FRONTEND_ROOT

for _samples_candidate in (FRONTEND_ROOT / "public" / "samples", _DIST_DIR / "samples"):
    if _samples_candidate.exists():
        app.mount("/samples", StaticFiles(directory=str(_samples_candidate)), name="samples")
        break

if FRONTEND_DIR.exists() and (FRONTEND_DIR / "index.html").exists():
    @app.get("/")
    def serve_frontend():
        return FileResponse(FRONTEND_DIR / "index.html")

    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run("main:app", host=host, port=port, reload=True)

