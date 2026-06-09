# ─── Stage 1: builder ─────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

RUN echo 'Acquire::Retries "5";' > /etc/apt/apt.conf.d/80-retries \
 && for i in 1 2 3 4 5; do \
      apt-get update -y && \
      apt-get install -y --no-install-recommends \
        build-essential libpq-dev libffi-dev ffmpeg && break; \
      echo "apt attempt $i failed, retrying in 30s..."; sleep 30; \
    done \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip \
 && pip install --prefix=/install --no-cache-dir -r requirements.txt

# ─── Stage 2: runtime ─────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

WORKDIR /app

RUN echo 'Acquire::Retries "5";' > /etc/apt/apt.conf.d/80-retries \
 && for i in 1 2 3 4 5; do \
      apt-get update -y && \
      apt-get install -y --no-install-recommends \
        libpq5 ffmpeg curl && break; \
      echo "apt attempt $i failed, retrying in 30s..."; sleep 30; \
    done \
 && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local

COPY . .

RUN useradd -m -u 1001 appuser \
 && mkdir -p /app/uploads /app/temp_generated_files /app/vector_db \
 && chown -R appuser:appuser /app

USER appuser

ENV ANONYMIZED_TELEMETRY=False \
    CHROMA_CLIENT_TELEMETRY=False \
    CHROMA_TELEMETRY=False \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

CMD ["uvicorn", "main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "2", \
     "--timeout-keep-alive", "120", \
     "--access-log"]
