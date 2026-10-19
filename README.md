# ಕನ್ನಡ ಲಿಪಿ ಮಿತ್ರ — Kannada Lipi Mitra

**Kannada Document AI & High-Fidelity OCR — turns Kannada document images into searchable, understandable, speakable digital text.**

> Entry for **Problem Statement 05 — Kannada Text Digitization**
> Kannada Digital Innovation Hackathon 2026 · Theme: *Code. Create. Celebrate Kannada.*
> Organized by HackerRank Campus Crew & The National Institute of Engineering (NIE), Mysuru

---

## 1. Problem Statement (PS-05)

Develop a solution that converts Kannada text from images, scanned documents, or handwritten material into searchable digital text and makes the content easier to understand and access.

**Who is affected & why it matters**

- Government circulars, school textbooks, land records, hospital notices and heritage manuscripts in Karnataka exist largely as **paper or scanned images** — invisible to search, screen readers, and translation tools.
- Citizens, students, researchers and visually impaired users **cannot copy, search, translate or hear** this content.
- Existing OCR tools struggle with Kannada's complex script (conjoined consonants, vowel signs, mixed English), producing garbled output that users cannot trust.

## 2. Existing System & Its Gaps

| Existing approach | Limitation |
|---|---|
| Traditional OCR (Tesseract + kanna traineddata) | Low accuracy on modern scans, notices, and mixed Kannada-English text; no understanding of context |
| General cloud OCR (Google Vision, AWS Textract) | Weak Indic-script support, pay-per-call pricing, no Kannada-specific validation |
| Manual transcription | Slow, expensive, error-prone, does not scale to thousands of documents |
| Static PDF text layers | Only works if the original PDF already contains text; useless for photos/scan images |

## 3. How Our Solution Is Different

1. **Engine-agnostic multi-engine architecture** — a pluggable `OCR Manager` routes the same image to **Gemini (multimodal LLM)**, **Groq (open vision LLM)**, or **Tesseract (offline)** via config or per-request override. No vendor lock-in; graceful degradation when a quota runs out.
2. **Script-distribution validation** — after extraction, output is analyzed for Kannada/Devanagari/Latin character shares. If the model "slips" into the wrong script, a **targeted retry prompt** runs automatically — catching errors traditional OCR never detects.
3. **Understand + hear, not just extract** — one-click translation to English/Hindi and authentic **Kannada text-to-speech** (browser native or gTTS backend fallback) make content accessible to non-readers and the visually impaired.
4. **Searchable from the moment it's extracted** — in-text search with match highlighting, editable transcription pane, copy / TXT export / print-to-PDF.
5. **Built for real documents** — upload, drag-and-drop, **camera capture on mobile** (photograph a notice in the wild), and ready-made sample documents (circular, public notice, textbook) for instant demos.

## 4. Approach & Workflow

```
Image OR PDF input (upload / camera / sample)
        │  PDF? render up to 10 pages → page-wise OCR
        ▼
FastAPI backend  ──►  UnifiedOCRManager
                          │  picks engine: gemini | groq | tesseract
                          │  not ready? auto-fallback to any ready engine
                          ▼
                   Vision / OCR engine  ──►  raw Kannada Unicode text
                          │
                          ▼
              Script-distribution check ── issue? one smart retry
                          │
                          ▼
        { text, word/char counts, script stats, engine used }
                          │
        ┌─────────────────┼──────────────────┐
        ▼                 ▼                  ▼
  Editable pane      Translate API       TTS API
  + search/highlight   (EN / HI)      (gTTS, lang='kn')
  + copy / TXT / PDF
```

**Key design decisions**

- *Why a manager pattern?* LLM APIs change quotas and pricing monthly; Tesseract is free but weaker. The manager makes the engine a **swap-able config value**, and the UI shows which engine produced a result.
- *Why post-hoc script validation?* LLMs occasionally answer in Devanagari or English for Indic OCR tasks. Measuring Unicode ranges is cheap, deterministic, and fixes a whole class of silent failures.
- *Why a same-origin deployment?* The FastAPI app serves the built frontend, so the live demo is **one URL, zero CORS issues**.

## 5. Tech Stack & Architecture

| Layer | Technology |
|---|---|
| Frontend | Vanilla JS (ES modules), HTML5, CSS3, Vite 6 (build tooling) |
| Backend | Python 3.12, FastAPI, Uvicorn, Pydantic, pypdfium2 (PDF page rendering) |
| OCR engines | Google Gemini (gemini-2.0-flash), Groq vision LLM, Tesseract + OpenCV (offline) |
| Translation | LLM-based (Gemini / Groq) Kannada → English / Hindi |
| Text-to-Speech | Web Speech API (browser) with gTTS (`lang='kn'`) server fallback |
| Deployment | Render (single web service), config via `render.yaml` + env vars |

**Architecture**

```
┌────────────────────────── Browser ──────────────────────────┐
│  Split-view UI: document image │ editable Kannada text      │
│  search+highlight · translate · TTS · copy · TXT · print/PDF │
└──────────────────────────────┬───────────────────────────────┘
                               │ REST (JSON / multipart / mp3)
                    ┌──────────▼──────────┐
                    │  FastAPI (main.py)  │  serves API + static frontend
                    │  /api/ocr           │
                    │  /api/translate     │
                    │  /api/tts           │
                    │  /api/health        │
                    └──────────┬──────────┘
                    ┌──────────▼──────────┐
                    │ UnifiedOCRManager   │  engine selection & status
                    └──┬───────┬───────┬──┘
                       ▼       ▼       ▼
                   Gemini    Groq   Tesseract
                  (LLM)    (LLM)   (offline OCR)
                       │       │       │
                       └───────┴───────┘
                    script validation + retry
                    translation · gTTS fallback
```

## 6. Features

- **Multi-engine OCR** — Gemini, Groq, or Tesseract; pick the engine from the **header dropdown** (or Auto = backend default), see status live in the badge — and if an engine isn't ready, the manager **auto-falls back** to any other ready engine
- **Image + PDF input** — file upload, drag-and-drop, mobile camera capture, multi-page **PDF** (rendered page-wise with per-page markers), plus 4 built-in sample documents including a **simulated handwritten note**
- **Script validation** — Kannada/Devanagari/Latin share analysis with automatic corrective retry and user-facing warnings
- **Split-view workstation** — original image (zoomable) beside an *editable* transcription
- **In-text search** — live match counter and highlight inside extracted text
- **Translation** — Kannada → English or Hindi on demand
- **Read aloud** — native browser Kannada voice, backend gTTS fallback (`/api/tts`)
- **Export** — copy, download `.txt`, print / save as PDF with a formatted digital-copy header
- **Rate-limit UX** — 429 detection, bilingual alert banner, countdown, one-click retry

## 7. Repository Structure

```
Kannada/
├── backend/
│   ├── main.py            # FastAPI app: /api/ocr, /api/translate, /api/tts, static serving
│   ├── ocr_service.py     # Engines (Gemini, Groq, Tesseract) + UnifiedOCRManager
│   ├── requirements.txt
│   ├── .env.example       # copy to .env and fill in keys
│   ├── create_samples.py  # generates the sample document images
│   ├── create_handwriting_sample.py  # generates the simulated handwriting sample
│   └── fonts/             # Noto Sans Kannada (for sample rendering)
├── frontend/
│   ├── index.html         # split-view UI
│   ├── main.js            # app controller
│   ├── style.css
│   ├── public/samples/    # demo documents served at /samples
│   └── dist/              # production build (served by the backend)
├── docs/                  # presentation, video script
├── render.yaml            # one-click deployment config
└── README.md
```

## 8. Setup & Run Locally

**Backend**

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env    # Windows — then fill in at least one API key
uvicorn main:app --reload --port 8000
```

**Frontend (dev mode)**

```bash
cd frontend
npm install
npm run dev               # http://localhost:5173  (calls backend on :8000)
```

**All-in-one (production mode — same as the deployed site)**

```bash
cd frontend && npm run build
cd ../backend && uvicorn main:app --port 8000
# open http://localhost:8000  — frontend + API from one origin
```

**Environment variables** (see `backend/.env.example`)

| Variable | Purpose |
|---|---|
| `OCR_ENGINE` | `gemini` \| `groq` \| `tesseract` |
| `GEMINI_API_KEY` | Google AI Studio key (Gemini OCR + translation) |
| `GROQ_API_KEY` | Groq key (Groq OCR + translation) |
| `TESSERACT_CMD` | Optional path to the Tesseract binary (offline engine) |
| `CORS_ORIGINS` | Comma-separated origins for split deployments |

> Tesseract is fully offline — install [Tesseract-OCR](https://github.com/tesseract-ocr/tesseract) plus the `kann` language data to run with **zero API keys**.

## 9. API Reference

| Method & path | Description |
|---|---|
| `GET /api/health` | Backend status, active engine, readiness of every engine |
| `GET /api/info` | Project name, active engine |
| `POST /api/ocr` | `multipart file` (+ optional `?engine=`) → Kannada Unicode text, counts, script stats |
| `POST /api/translate` | `{text, target_lang: en\|hi}` → translation |
| `POST /api/tts` | `{text}` → `audio/mpeg` (Kannada voice via gTTS) |

Interactive docs: `/docs` (Swagger UI).

## 10. Deployment

The repo ships with **`render.yaml`** — on [Render](https://render.com): *New → Blueprint*, point at the GitHub repo, then set `GEMINI_API_KEY` and/or `GROQ_API_KEY` in the service dashboard. The build also installs **Tesseract with Kannada language data** on the server, so all three engines are available out of the box. The FastAPI service serves both API and UI at one URL; `GET /api/health` is the health check.

Alternatives: any Python host (Railway, Hugging Face Spaces, PythonAnywhere, a VM) — the only requirement is `pip install -r backend/requirements.txt` + the start command in `render.yaml`. Commit `frontend/dist` (or run `npm run build` in the deploy pipeline).

## 11. Limitations & Future Scope

**Limitations:** handwriting accuracy depends on engine quality; gTTS needs internet; free-tier LLM quotas can throttle heavy use (the UI surfaces this clearly).

**Future scope:** batch PDF ingestion with page-wise OCR, on-device IndicOCR fine-tune for offline handwriting, transliteration (Kannada → Latin), multi-dialect phrase bank for PS-04 crossover, and screen-reader-optimized accessibility mode.

---

**Certificate & contact:** submitted via Unstop for the Kannada Digital Innovation Hackathon 2026 · PS-05 · Individual participation.
*All API keys are loaded from environment variables — no secrets are stored in this repository.*
