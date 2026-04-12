# ==============================================================================
# Dockerfile — Hugging Face Spaces Deployment (Backend)
# ==============================================================================
# This Dockerfile is optimized for HF Spaces free tier (2GB RAM, 16GB disk).
# It pre-downloads the sentence-transformers model during build so the
# container starts faster and doesn't OOM downloading at runtime.
#
# USAGE:
#   Local test: docker build -t support-agent . && docker run -p 7860:7860 support-agent
#   HF Spaces:  Push to HF repo → auto-builds and deploys
# ==============================================================================

FROM python:3.11-slim

# ── System dependencies ──────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# ── Create non-root user (required by HF Spaces) ────────────────────────────
RUN useradd -m -u 1000 user
ENV HOME=/home/user \
    PATH="/home/user/.local/bin:$PATH"

WORKDIR $HOME/app

# ── Install Python dependencies ─────────────────────────────────────────────
COPY --chown=user requirements.txt .
USER user
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ── Pre-download the embedding model at build time ───────────────────────────
# This avoids downloading ~80MB at runtime (slow + might OOM).
# The model gets cached in the Docker image layer.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# ── Copy application code ───────────────────────────────────────────────────
COPY --chown=user . .

# ── HF Spaces uses port 7860 by default ─────────────────────────────────────
EXPOSE 7860

# ── Start the FastAPI server ─────────────────────────────────────────────────
# HF Spaces expects the app on port 7860
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "7860"]
