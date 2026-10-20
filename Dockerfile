# ==============================================================================
# Kannada Lipi Mitra — multi-stage production image
# Stage 1: build the Vite frontend (Node)
# Stage 2: Python 3.12 + Tesseract (kan) + FastAPI; serves API + frontend/dist
# No secrets are baked in — set GROQ_API_KEY / OCR_ENGINE at runtime.
# ==============================================================================

# ---- Stage 1: frontend build ------------------------------------------------
FROM node:20-alpine AS frontend-build
WORKDIR /build

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# ---- Stage 2: runtime -------------------------------------------------------
FROM python:3.12-slim-bookworm

# Tesseract OCR + Kannada language data (language code: kan)
RUN apt-get update -qq \
    && apt-get install -y -qq --no-install-recommends \
        tesseract-ocr \
        tesseract-ocr-kan \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ backend/
# backend/main.py resolves the UI at ../frontend/dist (same layout as the repo)
COPY --from=frontend-build /build/dist frontend/dist/

ENV PYTHONUNBUFFERED=1 \
    OCR_ENGINE=tesseract \
    PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PORT','8000')+'/api/health', timeout=4)"

WORKDIR /app/backend
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
