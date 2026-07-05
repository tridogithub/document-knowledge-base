# --- Stage 1: build the web UI ---
FROM node:22-alpine AS ui
WORKDIR /ui
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# --- Stage 2: backend runtime ---
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# opencv-python (pulled in transitively by docling's table-structure model)
# needs these native libs even headless; missing libxcb.so.1 etc crashes
# ingestion of any PDF/DOCX/PPTX/XLSX at the "table_model" init step.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 libsm6 libxext6 libxrender1 libxcb1 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv/backend
COPY backend/pyproject.toml backend/uv.lock ./
ENV UV_PROJECT_ENVIRONMENT=/srv/venv
RUN uv sync --frozen --no-dev --no-install-project

COPY backend/app ./app
COPY --from=ui /ui/dist ./app/static

ENV PATH="/srv/venv/bin:$PATH" \
    DATA_DIR=/data \
    HF_HOME=/data/hf-cache

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
