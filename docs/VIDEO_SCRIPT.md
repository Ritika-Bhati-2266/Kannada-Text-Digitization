# Explanation Video Script — ಕನ್ನಡ ಲಿಪಿ ಮಿತ್ರ (Kannada Lipi Mitra)

**Total runtime: ~4:45 · Voice-over only, screen recording · PS-05: Kannada Text Digitization**

---

## 0:00 – 0:45 · Problem Statement & Requirements

> We're solving **Problem Statement 05 — Kannada Text Digitization**: build a solution that converts Kannada text from images, scanned documents, or handwritten material into **searchable digital text**, and makes that content **easier to understand and access**.
>
> In Karnataka, thousands of government circulars, school textbook pages, hospital notices and heritage documents exist only as **paper or scanned images**. You can look at them — but you can't search them, copy them, translate them, or have them read aloud. Students, researchers, citizens, and visually impaired users are locked out of their own language's written wealth.

**Screen:** show the Unstop problem-statement PDF, then 2–3 photos of real Kannada notices/posters.

## 0:45 – 1:30 · Existing Systems & Their Gaps

> How is this solved today?
>
> - **Traditional OCR** like Tesseract with Kannada training data — cheap, but accuracy collapses on modern scans and mixed Kannada-English notices, and it *silently* outputs garbage.
> - **General cloud OCR** — Google Vision, AWS Textract — weaker Indic script support, paid per call, no Kannada-specific validation.
> - **Manual transcription** — accurate but slow, costly, and impossible at the scale of real archives.
>
> The common gap: none of them **check whether the output is actually Kannada**, and none help you *understand* the text once extracted.

**Screen:** side-by-side — a Tesseract garbled output sample vs. the real document; a pricing/quota page.

## 1:30 – 3:30 · Our Solution — Live Demo & Approach

> This is **Kannada Lipi Mitra** — a Kannada Document AI with **engine-agnostic OCR**.
>
> **[Demo 1 — Instant demo, 25s]** One click on a built-in sample — a department circular. Watch: image loads on the left, extracted **clean Kannada Unicode** appears on the right. The header badge shows which engine ran — here, Groq.
>
> **[Demo 2 — Camera capture & in-text search, 25s]** Now a real-world test: I'll photograph a Kannada notice with the camera button — no file transfer, straight from phone to OCR. And notice the in-text search: type a word, every match highlights instantly with a counter. The transcription pane is fully **editable** — copy it, export a `.txt`, or print a formatted digital copy as PDF.
>
> **[Demo 3 — Multi-page PDF, 20s]** Most scanned archives are PDFs, so let me drop in a two-page circular. It renders each page and OCRs them in sequence, returning the full text with **per-page markers** — so you know exactly which page a line came from.
>
> **[Demo 4 — Handwriting, 20s]** PS-05 also names handwritten material. Here's a handwritten-style note — the engine extracts its Kannada text, making even hand-written content searchable.
>
> **[Demo 5 — Engine selector, 15s]** Watch the header dropdown: I can force Gemini, Groq, or fully-offline Tesseract. If an engine isn't configured or its quota runs out, the manager **auto-falls back** to a ready one — the user is never blocked.
>
> **[Demo 6 — Understand & hear, 25s]** Extraction isn't the finish line. One click translates the full text to **English** — or **Hindi**. Then **Read Aloud**: if the browser has no Kannada voice, our backend streams authentic Kannada speech via gTTS. This is what makes documents accessible to someone who *cannot read* Kannada script.
>
> **[Approach & tech stack, 45s]** Under the hood, a **UnifiedOCRManager** routes each image or PDF page to Gemini, Groq, or fully-offline Tesseract, then measures the **Unicode script distribution** — if the model slips into Devanagari or English, a targeted retry fires automatically. That validation loop is the reliability layer traditional OCR lacks.
>
> **Tech stack:** a lightweight vanilla-JS frontend served by a **Python FastAPI** backend, deployed as **one service** on Render straight from `render.yaml`. The same service hosts the API and the UI — one URL, zero CORS pain.

**Screen:** the live app throughout; briefly flash the `ocr_service.py` engine-classes and the script-validation function.

## 3:30 – 4:30 · Tech Stack & Architecture

> **Tech stack:** the frontend is lightweight vanilla JS with Vite, served by a **Python FastAPI** backend. OCR runs on **Gemini 2.0 Flash**, **Groq vision LLMs**, or **Tesseract + OpenCV** offline. Translation is LLM-based; speech uses the browser's native voice with a **gTTS** server fallback.
>
> **Architecture:** the browser's split-view UI talks to one REST API — `/api/ocr`, `/api/translate`, `/api/tts`. The FastAPI app hands images to the OCR manager, which selects an engine, validates the script, and returns structured JSON. The same service serves the built frontend — so the whole product is **one URL, zero CORS pain**, deployed on Render straight from `render.yaml`.

**Screen:** slide with the architecture diagram (boxes: Browser → FastAPI → OCR Manager → three engines), then the repo structure.

## 4:30 – 5:00 · Conclusion

> **Kannada Lipi Mitra** turns any Kannada document image into text you can **search, edit, understand, hear, translate and share** — addressing PS-05 end to end, with a validation layer that traditional OCR lacks and an engine-agnostic core that never locks you in.
>
> Future scope: batch PDF ingestion, offline handwriting fine-tuning, and transliteration.
>
> Code, live demo and this submission are built for the **Kannada Digital Innovation Hackathon 2026** — *Code. Create. Celebrate Kannada.* ಧನ್ಯವಾದಗಳು!

**Screen:** app hero screen with three sample results side by side → title card with repo + live URL.

---

### Recording checklist

- [ ] Screen resolution ≥ 1080p, browser zoom 100–110%, dark theme for contrast
- [ ] Pre-warm the backend and run each demo once before recording (LLM first-call latency)
- [ ] Keep a working sample ready in case an API quota hits 429 mid-take
- [ ] Audio: quiet room, -6 dB peaks, no background music (voice-over only)
- [ ] Export 3:00–5:00 minutes total; verify final length before upload
