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
| Raw OCR out of the box (Tesseract + `kan` traineddata) | Low accuracy on modern scans and mixed Kannada-English text — no preprocessing, no script validation, no cross-check (our app adds all three, with an optional Groq vision model on top) |
| General cloud OCR (Google Vision, AWS Textract) | Weak Indic-script support, pay-per-call pricing, no Kannada-specific validation |
| Manual transcription | Slow, expensive, error-prone, does not scale to thousands of documents |
| Static PDF text layers | Only works if the original PDF already contains text; useless for photos/scan images |

## 3. How Our Solution Is Different

1. **Two engines, one sensible default** — a pluggable `OCR Manager` routes the same image to **Tesseract (offline, default)** or to the optional **Groq (open vision LLM)** via config or per-request override. Tesseract runs with **zero API keys**; Groq is opt-in when a key is configured. No vendor lock-in.
2. **Script-distribution validation** — after extraction, output is analyzed for Kannada/Devanagari/Latin character shares and surfaced to the user. On the **Groq path only** (the vision model), a wrong-script answer triggers an automatic **targeted retry prompt**; Tesseract output gets the same analysis and warnings, but no retry — its failures already show up as low Kannada share.
3. **Understand + hear, not just extract** — one-click translation to English/Hindi and authentic **Kannada text-to-speech** (browser native or gTTS backend fallback) make content accessible to non-readers and the visually impaired.
4. **Handwriting mode (experimental)** — a dedicated toggle switches both engines to handwriting-tuned pipelines. Tesseract runs **both** preprocessing variants (adaptive threshold + deskew + stroke reconnection, and standard Otsu) and keeps the higher-confidence result. The Groq vision path gets a handwriting-aware prompt that transcribes only what is visible and writes `[illegible]` when unsure. Auto-enabled for the built-in handwriting sample. **Caveat:** tested only on one *simulated* handwriting sample, where Tesseract picked the print pipeline (same output as print mode). Tesseract `kan` is trained on printed text; no real-handwriting accuracy has been measured.
5. **Searchable from the moment it's extracted** — in-text search with match highlighting, editable transcription pane, copy / TXT export / print-to-PDF.
6. **Built for real documents** — upload, drag-and-drop, **camera capture on mobile** (photograph a notice in the wild), and ready-made sample documents (circular, public notice, textbook, handwritten note) for instant demos.
7. **Honest output** — when the optional vision model returns far more text than offline Tesseract finds on the same image, the result carries a **"machine-read text, please verify"** warning; handwriting results always carry a verify prompt.

## 4. Approach & Workflow

```
Image OR PDF input (upload / camera / sample)
        │  PDF? render up to 10 pages → page-wise OCR
        ▼
FastAPI backend  ──►  UnifiedOCRManager
                          │  picks engine: tesseract (default) | groq (optional)
                          │  Groq not configured? Tesseract still runs offline
                          ▼
                   Vision / OCR engine  ──►  raw Kannada Unicode text
                          │
                          ▼
               Script-distribution check (both engines)
               Groq path only: issue? one smart retry
                          │
                          ▼
        { text, word/char counts, script stats, engine used }
                          │
        ┌─────────────────┼──────────────────┐
        ▼                 ▼                  ▼
  Editable pane      Translate API       TTS API
  + search/highlight  (EN / HI, needs     (gTTS, lang='kn')
  + copy / TXT / PDF   optional Groq key)
```

**Key design decisions**

- *Why a manager pattern?* LLM APIs change quotas and pricing monthly; Tesseract is free but weaker. The manager makes the engine a **swap-able config value**, and the UI shows which engine produced a result.
- *Why post-hoc script validation?* LLMs occasionally answer in Devanagari or English for Indic OCR tasks. Measuring Unicode ranges is cheap and deterministic and fixes a whole class of silent failures — the corrective **retry runs only on the Groq path**, where the failure mode exists.
- *Why a same-origin deployment?* The FastAPI app serves the built frontend, so the live demo is **one URL, zero CORS issues**.

## 5. Tech Stack & Architecture

| Layer | Technology |
|---|---|
| Frontend | Vanilla JS (ES modules), HTML5, CSS3, Vite 6 (build tooling) |
| Backend | Python 3.12, FastAPI, Uvicorn, Pydantic, pypdfium2 (PDF page rendering) |
| OCR engines | Tesseract + OpenCV (offline, **default**), Groq vision LLM (optional) |
| Translation | LLM-based (Groq) Kannada → English / Hindi |
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
                    └──┬──────────┬───┘
                       ▼          ▼
                   Tesseract    Groq
                (offline,     (optional
                  default)    vision LLM)
                       │          │
                       └────┬─────┘
                            ▼
                    script stats + warnings
                    Groq path: smart retry +
                    Tesseract cross-check warning
                    translation (needs GROQ_API_KEY)
                    · gTTS fallback
```

## 6. Features

- **Two engines, one default** — Tesseract (offline) is the default, Groq is optional; pick the engine from the **header dropdown** (Groq · Tesseract offline, default), see status live in the badge
- **Multi-variant real-world preprocessing** — Tesseract print mode automatically runs **two pipelines** (standard Otsu + scan/photo-tuned CLAHE-adaptive-deskew) and picks the higher-confidence result, so unevenly-lit phone photos and real scans are handled without a manual toggle
- **Image + PDF input** — file upload, drag-and-drop, mobile camera capture, multi-page **PDF** (rendered page-wise with per-page markers), plus 4 built-in sample documents
- **Handwriting mode (experimental)** — toggle switches to handwriting-tuned preprocessing (adaptive threshold, deskew, stroke reconnection) on Tesseract and a handwriting-aware vision prompt on Groq; auto-enabled for sample 4 (simulated handwriting generated by script). Tested on one simulated sample only; Tesseract `kan` is print-trained — no real-handwriting accuracy claimed
- **Script validation** — Kannada/Devanagari/Latin share analysis with user-facing warnings on both engines; on the **Groq path only**, an automatic corrective retry plus a **machine-read text, please verify** cross-check notice when the vision model's output is inflated vs Tesseract
- **Searchable document library (corpus search)** — every OCR result is auto-saved to a local SQLite archive; open the **Library** drawer to search across *all* digitized documents at once, re-open any past transcription, or delete entries
- **Split-view workstation** — original image (zoomable) beside an *editable* transcription
- **In-text search** — live match counter and highlight inside extracted text
- **Transliteration** — one-click offline Kannada → Latin (ITRANS) transliteration via `indic-transliteration`; runs locally with no API key or network
- **Translation** — Kannada → English or Hindi on demand; needs the optional `GROQ_API_KEY`, and without it the UI says **"Translation needs the optional Groq key"** instead of a generic error (OCR keeps working offline)
- **Read aloud** — native browser Kannada voice, backend gTTS fallback (`/api/tts`)
- **Export** — copy, download `.txt`, print / save as PDF with a formatted digital-copy header
- **Rate-limit UX** — 429 detection, bilingual alert banner, countdown, one-click retry
- **PWA (installable)** — web-app manifest + service worker: the app shell caches for offline launch; OCR/API calls still require the backend

## 7. Repository Structure

```
Kannada/
├── backend/
│   ├── main.py            # FastAPI app: /api/ocr, /api/translate, /api/transliterate, /api/tts, /api/archive, static serving
│   ├── ocr_service.py     # Engines (Tesseract default, Groq optional) + UnifiedOCRManager
│   ├── archive.py         # SQLite searchable document archive
│   ├── requirements.txt
│   ├── .env.example       # copy to .env and fill in keys
│   ├── create_samples.py  # generates the sample document images
│   ├── create_handwriting_sample.py  # generates the simulated handwriting sample
│   └── fonts/             # Noto Sans Kannada (for sample rendering)
├── frontend/
│   ├── index.html         # split-view UI + library drawer
│   ├── main.js            # app controller
│   ├── style.css
│   ├── public/samples/    # demo documents served at /samples
│   ├── public/manifest.webmanifest  # PWA manifest
│   ├── public/sw.js       # service worker (offline shell)
│   └── dist/              # production build (served by the backend)
├── Dockerfile             # multi-stage: Node builds frontend → Python+Tesseract runtime
├── .dockerignore          # excludes .env, .git, node_modules, __pycache__, …
├── render.yaml            # one-click deployment config (Render Docker runtime)
└── README.md
```

## 8. Setup & Run Locally

**Backend**

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env    # Windows — Tesseract runs with no key; add GROQ_API_KEY for the optional Groq engine
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
| `OCR_ENGINE` | `tesseract` (default) \| `groq` (optional) |
| `GROQ_API_KEY` | Optional — enables Groq OCR + translation; without it the UI shows **"Translation needs the optional Groq key"** (Tesseract OCR still works) |
| `GROQ_MAX_TOKENS` | Max output tokens per Groq call (default `4096`) |
| `GROQ_MAX_ILLEGIBLE_RATIO` | Abort when more than this share of words is `[illegible]` (default `0.30`) |
| `TESSERACT_CMD` | Optional path to the Tesseract binary (offline engine) |
| `TESSERACT_PSM` | Tesseract page-segmentation mode (default `6`) |
| `CORS_ORIGINS` | Comma-separated origins for split deployments |

> Tesseract is fully offline — install [Tesseract-OCR](https://github.com/tesseract-ocr/tesseract) plus the `kan` language data (Debian/Ubuntu package: `tesseract-ocr-kan`) to run with **zero API keys**.

## 9. API Reference

| Method & path | Description |
|---|---|
| `GET /api/health` | Backend status, active engine, readiness of every engine |
| `GET /api/info` | Project name, active engine |
| `POST /api/ocr` | `multipart file` (+ optional `?engine=`, `?handwriting=true`) → Kannada Unicode text, counts, script stats; **auto-saved to archive** |
| `POST /api/translate` | `{text, target_lang: en\|hi}` → translation (needs Groq key) |
| `POST /api/transliterate` | `{text}` → offline Kannada → Latin (ITRANS) transliteration |
| `POST /api/tts` | `{text}` → `audio/mpeg` (Kannada voice via gTTS) |
| `GET /api/archive` | List/search all archived OCR results (`?q=`, `?limit=`) |
| `GET /api/archive/{id}` | Fetch one archived document with full text |
| `DELETE /api/archive/{id}` | Remove a document from the archive |

Interactive docs: `/docs` (Swagger UI).

## 10. Deployment

The repo ships with **`render.yaml`** — on [Render](https://render.com): *New → Blueprint*, point at the GitHub repo. The service uses Render's **Docker runtime** (`runtime: docker`, `dockerfilePath: ./Dockerfile`). The multi-stage `Dockerfile` builds the Vite frontend on Node, then copies `frontend/dist` into a `python:3.12-slim` image that installs **Tesseract and its Kannada language data** (`tesseract-ocr-kan`, language code **`kan`**). FastAPI runs uvicorn on `$PORT` and serves both API and UI at one URL; `GET /api/health` is the health check. The default engine is Tesseract — **no API keys at all**. To enable the optional Groq engine, set `GROQ_API_KEY` (and `OCR_ENGINE=groq`) in the service dashboard.

`.dockerignore` keeps `.env`, `.git`, `node_modules`, and `__pycache__` out of the build context. No secrets in the Dockerfile or `render.yaml` — pass `GROQ_API_KEY` (and optionally `OCR_ENGINE`) at runtime. Local Docker:

```bash
docker build -t kannada-lipi-mitra .
docker run -p 8000:8000 -e GROQ_API_KEY=... kannada-lipi-mitra
```

Non-Docker alternative: any Python host (Railway, Hugging Face Spaces, PythonAnywhere, a VM) — install Tesseract + `tesseract-ocr-kan`, run `pip install -r backend/requirements.txt`, run `cd frontend && npm ci && npm run build`, and start uvicorn.

## 11. Measured Accuracy

**Test set: 4 images, all synthetic.** Every PNG in `samples/` was rendered by our own generator scripts (`create_samples.py`, `create_handwriting_sample.py`) from known Kannada text. There are **zero real photographs, scans, or real handwriting** in this set — `sample_handwriting.png` is **simulated** pen-stroke rendering, not a photo of handwriting. Four documents is a **small test set**; these numbers are not a claim of production accuracy on arbitrary Karnataka government circulars, land records, or manuscripts.

**Metric: CER only, against ground-truth text files.** Reproduce with `python backend/compare_engines.py`. **CER** (character error rate) = Levenshtein distance over characters divided by reference length, computed **only** against the matching `samples/<name>.txt` (zero-width joiners stripped, whitespace collapsed). Lower is better; `0.00%` = exact match. No word-accuracy, no subjective scoring, no cherry-picked images. Failed or rate-limited runs are shown as failures, not omitted.

| Sample (4 total, 4 generated, 0 real) | Groq (vision LLM) | Tesseract psm 4 | Tesseract psm 6 (default) |
|---|---|---|---|
| `sample_circular.png` *(generated)* | 52.35% (48.2s) | 20.75% (1.63s) | **20.51%** (1.45s) |
| `sample_handwriting.png` *(simulated, not real handwriting)* | 47.06% (19.0s) | **11.03%** (0.56s) | 13.24% (0.63s) |
| `sample_notice.png` *(generated)* | 50.27% (91.6s) \* | 23.38% (1.46s) | **22.16%** (1.42s) |
| `sample_textbook.png` *(generated)* | 56.50% (90.1s) \* | 17.62% (1.65s) | **16.25%** (1.60s) |

\* Groq results vary between runs, and free-tier rate limits add long backoffs (visible in the run above) — they can also fail a call outright. On these generated samples the offline default is both **more accurate and far faster**, which is exactly why Tesseract is the default and Groq stays optional. The engine dropdown lets you compare both on your own documents.

**Reading these numbers honestly:** best Tesseract CER on this set is **11.03%** (handwriting sample, psm 4) and worst is **23.38%** (notice, psm 4) — i.e. roughly **11–23 characters wrong per 100**. That is usable as a draft transcription aid with the editable pane, **not** as unattended digitization. Groq CER on the same images is **47–57%**. We publish the bad numbers because hiding them would misrepresent readiness.

## 12. Limitations & Future Scope

**Limitations:** the built-in handwriting sample is **simulated handwriting generated by script, not a real pen-on-paper photo** — the handwriting mode is **experimental**: it was tested only on that one simulated sample (where Tesseract's confidence picker selected the print pipeline, producing the same output as print mode). Tesseract `kan` is trained on printed text; no real-handwriting accuracy has been measured or claimed. gTTS needs internet; free-tier Groq quotas can throttle or fail heavy use (the UI surfaces this clearly, and OCR keeps working offline).

**Future scope:** batch PDF ingestion with page-wise OCR, transliteration (Kannada → Latin), multi-dialect phrase bank for PS-04 crossover, screen-reader-optimized accessibility mode, and evaluation of on-device models for real handwriting (beyond today's simulated sample).

---

**Certificate & contact:** submitted via Unstop for the Kannada Digital Innovation Hackathon 2026 · PS-05 · Individual participation.
*All API keys are loaded from environment variables — no secrets are stored in this repository.*
