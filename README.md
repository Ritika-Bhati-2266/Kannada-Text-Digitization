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
- **Two preprocessing variants, confidence picker** — Tesseract print mode runs **two pipelines** (standard Otsu + a CLAHE/adaptive-threshold/deskew variant) and keeps whichever gets the **higher Tesseract mean word-confidence**. Confidence is not accuracy: this variant switch has **not** been measured on real photos or scans, and the only benchmark we have is the synthetic set in §11 (print-mode confidence picker in `TesseractEngine.extract_text()`)
- **Optional Latin-junk cleanup (default `false`)** — `kan+eng` sometimes emits a short, low-confidence Latin word where Kannada was printed. With `LATIN_CLEANUP=true` the winning image is scanned for pure-ASCII words (no digits, not ALL-CAPS, mean confidence below `LATIN_MIN_CONF`, default 80), each such word's crop is re-OCR'd with `lang="kan"` psm 7, and the Kannada result is spliced in **only if one comes back** — nothing is ever dropped (`TesseractEngine._reocr_latin_word()`, `TesseractEngine._apply_latin_cleanup()`, both applied in `TesseractEngine.extract_text()`). Off by default; §11 has the measured before/after on all four samples
- **Image + PDF input** — file upload, drag-and-drop, mobile camera capture, multi-page **PDF** (rendered page-wise with per-page markers), plus 4 built-in sample documents
- **Handwriting mode (experimental)** — toggle switches to handwriting-tuned preprocessing (adaptive threshold, deskew, stroke reconnection) on Tesseract and a handwriting-aware vision prompt on Groq; auto-enabled for sample 4 (simulated handwriting generated by script). Tested on one simulated sample only; Tesseract `kan` is print-trained — no real-handwriting accuracy claimed. The handwriting mode runs **both** pipelines (handwriting + print) and keeps the higher-mean-confidence result (handwriting confidence picker in `TesseractEngine.extract_text()`)
- **Script validation** — Kannada/Devanagari/Latin share analysis with user-facing warnings on both engines; on the **Groq path only**, an automatic corrective retry plus a **machine-read text, please verify** cross-check notice when the vision model's output is inflated vs Tesseract
- **Searchable document library (corpus search)** — **opt-in, off by default**: set `ENABLE_ARCHIVE=true` to auto-save every OCR result to a local SQLite archive; then the **Library** drawer lets you search across *all* digitized documents at once, re-open any past transcription, or delete entries. When off: `/api/archive` returns 404, nothing is saved, and the Library button is hidden
- **Split-view workstation** — original image (zoomable) beside an *editable* transcription
- **In-text search** — live match counter and highlight inside extracted text
- **Transliteration** — one-click offline Kannada → Latin (ITRANS) transliteration via `indic-transliteration`; runs locally with no API key or network
- **Translation** — Kannada → English or Hindi on demand; needs the optional `GROQ_API_KEY`, and without it the UI says **"Translation needs the optional Groq key"** instead of a generic error (OCR keeps working offline)
- **Read aloud** — native browser Kannada voice, backend gTTS fallback (`/api/tts`)
- **Export** — copy, download `.txt`, print / save as PDF with a formatted digital-copy header
- **Rate-limit UX** — 429 detection, bilingual alert banner, countdown, one-click retry
- **PWA (installable)** — web-app manifest + service worker: the app shell caches for offline launch; **`/api/*` responses are never cached**, and OCR still requires the backend
- **Privacy by default** — images are processed in memory and are stored **only** if you opt in with `ENABLE_ARCHIVE=true`. The dropzone states where text goes: *"Read Aloud uses the browser voice first; otherwise text goes to Google (gTTS). Translation text goes to Groq API."* (headless Chromium test had 0 Kannada voices; real browsers vary. Fallback is gTTS (Google) — 5 voices total, see §11)

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
| `LATIN_CLEANUP` | `false` (default) — set `true` to re-OCR low-confidence Latin junk words back to Kannada (Tesseract path only; measured in §11) |
| `LATIN_MIN_CONF` | `80` (default) — Latin words with mean confidence at or above this are never touched by `LATIN_CLEANUP` |
| `CORS_ORIGINS` | Comma-separated origins for split deployments |
| `ENABLE_ARCHIVE` | `false` (default) — set `true` to enable `/api/archive`, OCR auto-save and the Library UI; when false the archive routes return 404 |

> Tesseract is fully offline — install [Tesseract-OCR](https://github.com/tesseract-ocr/tesseract) plus the `kan` language data (Debian/Ubuntu package: `tesseract-ocr-kan`) to run with **zero API keys**.

## 9. API Reference

| Method & path | Description |
|---|---|
| `GET /api/health` | Backend status, active engine, readiness of every engine |
| `GET /api/info` | Project name, active engine |
| `POST /api/ocr` | `multipart file` (+ optional `?engine=`, `?handwriting=true`) → Kannada Unicode text, counts, script stats; **auto-saved to archive only when `ENABLE_ARCHIVE=true`** |
| `POST /api/translate` | `{text, target_lang: en\|hi}` → translation (needs Groq key) |
| `POST /api/transliterate` | `{text}` → offline Kannada → Latin (ITRANS) transliteration |
| `POST /api/tts` | `{text}` → `audio/mpeg` (Kannada voice via gTTS) |
| `GET /api/archive` | List/search all archived OCR results (`?q=`, `?limit=`) — **404 unless `ENABLE_ARCHIVE=true`** |
| `GET /api/archive/{id}` | Fetch one archived document with full text — **404 unless `ENABLE_ARCHIVE=true`** |
| `DELETE /api/archive/{id}` | Remove a document from the archive — **404 unless `ENABLE_ARCHIVE=true`** |

Interactive docs: `/docs` (Swagger UI).

## 10. Deployment

The repo ships with **`render.yaml`** — on [Render](https://render.com): *New → Blueprint*, point at the GitHub repo. The service uses Render's **Docker runtime** (`runtime: docker`, `dockerfilePath: ./Dockerfile`). The multi-stage `Dockerfile` builds the Vite frontend on Node, then copies `frontend/dist` into a `python:3.12-slim` image that installs **Tesseract and its Kannada language data** (`tesseract-ocr-kan`, language code **`kan`**). FastAPI runs uvicorn on `$PORT` and serves both API and UI at one URL; `GET /api/health` is the health check. The default engine is Tesseract — **no API keys at all**. To enable the optional Groq engine, set `GROQ_API_KEY` (and `OCR_ENGINE=groq`) in the service dashboard.

On Render's free plan OCR takes about 2 minutes per document (measured); locally it takes a few seconds.

`.dockerignore` keeps `.env`, `.git`, `node_modules`, and `__pycache__` out of the build context. No secrets in the Dockerfile or `render.yaml` — pass `GROQ_API_KEY` (and optionally `OCR_ENGINE`) at runtime. Local Docker:

```bash
docker build -t kannada-lipi-mitra .
docker run -p 8000:8000 -e GROQ_API_KEY=... kannada-lipi-mitra
```

Non-Docker alternative: any Python host (Railway, Hugging Face Spaces, PythonAnywhere, a VM) — install Tesseract + `tesseract-ocr-kan`, run `pip install -r backend/requirements.txt`, run `cd frontend && npm ci && npm run build`, and start uvicorn.

## 11. Measured Accuracy

**Test set: 4 images, all synthetic.** Every PNG in `samples/` was rendered by our own generator scripts (`create_samples.py`, `create_handwriting_sample.py`) from known Kannada text. There are **zero real photographs, scans, or real handwriting** in this set — `sample_handwriting.png` is **simulated** pen-stroke rendering, not a photo of handwriting. Four documents is a **small test set**; these numbers are not a claim of production accuracy on arbitrary Karnataka government circulars, land records, or manuscripts.

**One real phone photo of ruled handwriting:** first run (toggle off) gave unusable noise (880 words / 3214 chars for ~124 words); later run readable with many errors. No CER. Clean screenshots not same as phone photos.

**Metric: CER only, against ground-truth text files.** Reproduce with `python backend/compare_engines.py`. **CER** (character error rate) = Levenshtein distance over characters divided by reference length, computed **only** against the matching `samples/<name>.txt` (zero-width joiners stripped, whitespace collapsed). Lower is better; `0.00%` = exact match. No word-accuracy, no subjective scoring, no cherry-picked images. Failed or rate-limited runs are shown as failures, not omitted.

| Sample (4 total, 4 generated, 0 real) | Groq (vision LLM) | Tesseract psm 4 | Tesseract psm 6 (default) |
|---|---|---|---|
| `sample_circular.png` *(generated)* | 52.35% (50.58s) | 15.92% (5.52s) | **15.80%** (5.75s) |
| `sample_handwriting.png` *(simulated, not real handwriting)* | 47.06% (12.27s) | **15.44%** (2.05s) | 17.65% (2.05s) |
| `sample_notice.png` *(generated)* | 50.27% (91.59s) | 18.65% (5.44s) | **17.84%** (6.24s) |
| `sample_textbook.png` *(generated)* | 56.50% (49.0s) † | **12.00%** (6.43s) | 12.62% (6.29s) |

**Measured 22 Oct 2026, local, Tesseract 5.5.3 — the Groq rows come from separate runs**, because every Groq document hit repeated `429` rate-limit backoffs: circular, handwriting and notice are from one run; the textbook row (†) is from a later re-run of the same image, which succeeded at **56.50% (49.0s)** after the benchmark attempt failed — `chat/completions failed after 25.4s` / *"Groq did not respond in 25s, try again or check the key."* Failures are recorded as failures, not omitted or back-filled. Groq here is `qwen/qwen3.8-27b`. On these generated samples the offline default is both more accurate and far faster, which is why Tesseract is the default and Groq stays optional.

**Numbers measured locally on Tesseract 5.5.3; live Render image runs 5.3.0 and was not re-measured.**

**Hallucinated lines (measured 22 Oct 2026):** every successful Groq output contains lines that are **not in the image** — verified absent from the matching ground-truth `.txt`:

- *notice:* `ಗ್ರಾಮೀಣ ವಲಯದಲ್ಲಿ ವ್ಯಾಪಕವಾಗಿ ಸಮಸ್ಯೆ ಸೃಷ್ಟಿಸಲಾಗಿದೆ.` · `…೧೦ ಜನರು ಸಾವನ್ನಪ್ಪಿದ್ದಾರೆ.` (an invented casualty count) · `ಅಧ್ಯಕ್ಷರಾದ ಗೌರವಮಾನ್ಯರು ದ್ವಾರಕೆ ೨೬-೦೦-೨೦೨೬ ರಂದು…`
- *circular:* `ಸರ್ಕಾರದ ಅನುಮೋದನೆ ಕಟ್ಟುವಿಕೆಗಳ ಮೇಲೆ ಸಿಬ್ಬಂದಿ.` · `ಸೂಕ್ತಾದ ಅಧಿಕಾರದಾರಿ ಕಚೇರಿಯವರ ಮೂಲಕ ಸಲ್ಲಿಸಲಾಗುತ್ತದೆ.`
- *textbook:* `ಕಾಗಳು ಜ್ಞಾನವೇದೀಶ ಬ್ರಹ್ಮಶ್ರೀ ಮುದ್ದನಾಥ ಮಹಾಶ್ರೀ.` · `ಮೇಲಿನವರೇ ಹೊರತು ಮೊದಲ, ತೂರಾ ನರೇರಾ ಹೇರೆಯ ಮಹಾತ್ಮ` · `ನೀವು ಉತ್ತರಿಸಲಾಗಿದೆ.` · and the wrong print year `೨೦೨೪` (the image says `೨೦೨೬`)
- *handwriting:* no line fell below the 0.45 line-match threshold against ground truth (Groq returned only 7 lines there)

**Optional Latin-junk cleanup — measured 22 Oct 2026, local, Tesseract 5.5.3:** `LATIN_CLEANUP=true` vs the default-off baseline (the Tesseract columns above). Gate: no sample may worsen by more than **1.00 pp** — result **PASS**, every row improved. The cleanup was tuned and tested on the same 4 samples.

| Image | psm 4 baseline → with cleanup | psm 6 baseline → with cleanup |
|---|---|---|
| `sample_circular.png` | 15.92% → **12.79%** (−3.13 pp) | 15.80% → **12.42%** (−3.38 pp) |
| `sample_handwriting.png` | 15.44% → **11.76%** (−3.68 pp) | 17.65% → **13.97%** (−3.68 pp) |
| `sample_notice.png` | 18.65% → **17.57%** (−1.08 pp) | 17.84% → **15.95%** (−1.89 pp) |
| `sample_textbook.png` | 12.00% → **11.75%** (−0.25 pp) | 12.62% → **9.88%** (−2.74 pp) |

Worst change: **+0.00 pp**. Protected strings survived verbatim in the after-texts: `PDO`, `AUTHORITY`, `ED-2026-KN-0492/SAMPLE`, `GP-SRP-2026-NOTICE/SAMPLE`, `KTBS`. The Latin tokens that disappeared: `ritdosh`, `vara}`, `cea?`, `sid` (notice), `Paden`, `Sota:`, `Tow.`, `Hawes`, `sic` (textbook), `Beis` (handwriting) — replaced by Kannada tokens such as `ನ್ಸರ್ಗ`, `ವರ್ಷ:`, `ಮಲೆನಾಡ್ನ`, `ಜೆಳ್ಗಗೆ`. The flag ships **off**: with `LATIN_CLEANUP` unset, all three printed samples re-ran **byte-identical** to the baseline above. Enabling it added **~51% OCR time locally** (40.8s → 61.5s over 10 runs); **not enabled on the free Render server**.

**Browser end-to-end checks — measured 22 Oct 2026, local, Tesseract 5.5.3:**

- **Multi-page PDF:** a 2-page PDF OCR'd in **12 s** in the UI (**11 s** at the API), `page_count: 2`, page markers `—— ಪುಟ / Page 1 ——` and `—— ಪುಟ / Page 2 ——` present
- **English-only image:** clean English text (379 chars) plus the banner *"Script Validation Warning: Almost no Kannada script detected (0.0%)"*
- **Forced 500** (Playwright route interception): error banner shown, empty editor → all **7** action buttons disabled; text present → all **7** enabled; sample pills unlocked again — **PASS, no FAILs** (gating in `frontend/main.js:611-622`)
- **Engine label with and without a key:** identical — badge `TESSERACT: READY`, meta `TESSERACT (tesseract-kan (psm 6 (print)))`; decided by `OCR_ENGINE` (`UnifiedOCRManager.get_configured_engine_name()`, `main.py:84`)
- **TXT export:** `kannada_document_transcription.txt` — 104 bytes = UTF-8 BOM (`EF BB BF`) + content, valid UTF-8, zero-width joiners and Latin digits intact, exact match with the editor text
- **Read Aloud data path:** the headless Chromium test had **0 Kannada voices** (5 voices total) — real browsers vary → `POST /api/tts` returned 200 `audio/mpeg` → the text reached **Google** (`main.py:359` `gTTS(lang="kn")`, `main.js:876`, `main.js:909`)
- **Privacy default:** images are processed in memory and are not stored unless `ENABLE_ARCHIVE=true`

**About the numbers above:** OCR now runs Tesseract with `lang="kan+eng"` (bug fix — `kan` alone mangled Latin codes like `ED-2026-KN-0492/SAMPLE`). Tesseract latencies are higher than in single-pipeline runs because print mode runs **both** preprocessing variants and keeps the higher-confidence result (confidence is not accuracy — see §6).

**Reading these numbers honestly:** best Tesseract CER on this set is **12.00%** (textbook, psm 4) and worst is **18.65%** (notice, psm 4) — i.e. roughly **12–19 characters wrong per 100**. Versus the previous `lang="kan"` run: the three printed samples **improved** (circular 20.75%→15.80%, notice 22.16%→17.84%, textbook 17.62%→12.00%) but the handwriting sample got **worse** (11.03%→15.44%). Usable as a draft transcription aid with the editable pane, **not** as unattended digitization. We publish the bad numbers because hiding them would misrepresent readiness.

## 12. Limitations & Future Scope

**Limitations:** the built-in handwriting sample is **simulated handwriting generated by script, not a real pen-on-paper photo** — the handwriting mode is **experimental**: it was tested only on that one simulated sample (where Tesseract's confidence picker selected the print pipeline, producing the same output as print mode). Tesseract `kan` is trained on printed text; no real-handwriting accuracy has been measured or claimed — one real phone photo of ruled handwriting was tested manually (readable with many errors, no CER measured; see §11). gTTS needs internet; free-tier Groq quotas can throttle or fail heavy use (the UI surfaces this clearly — benchmark runs on 22 Oct 2026 hit repeated `429` backoffs and one 25 s timeout — and OCR keeps working offline). Translation is LLM-generated and can smooth over OCR errors or guess missing words; English and Hindi output can differ for the same text; verify against the original. `kan+eng` fixes Latin codes and digits but occasionally replaces a Kannada word with short English junk (e.g. 'asta', 'Assit'; measured 22 Oct 2026: `ritdosh`, `Paden`, `sic`); review the text in the editable pane, or enable the opt-in `LATIN_CLEANUP` (default `false`), which measured −0.25 to −3.68 pp CER on all four samples with no sample worsening (§11).

**Future scope:** batch PDF ingestion with page-wise OCR, multi-dialect phrase bank for PS-04 crossover, screen-reader-optimized accessibility mode, evaluation of on-device models for real handwriting (beyond today's simulated sample), and measuring the two preprocessing variants against real photos/scans (today they are picked by Tesseract confidence only, which is not accuracy).

---

**Certificate & contact:** submitted via Unstop for the Kannada Digital Innovation Hackathon 2026 · PS-05 · Individual participation.
*All API keys are loaded from environment variables — no secrets are stored in this repository.*
