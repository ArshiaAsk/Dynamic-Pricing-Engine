# One hardened image (DECISIONS D31): dependencies are installed in a builder
# stage, the runtime stage is non-root, and Docker can probe /v1/health.
FROM python:3.12-slim AS builder

WORKDIR /app

COPY requirements.txt .

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --default-timeout=120 --retries 10 --prefix=/install -r requirements.txt

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1

RUN useradd --create-home --uid 1000 appuser

COPY --from=builder /install /usr/local

WORKDIR /app

RUN chown appuser:appuser /app

COPY --chown=appuser:appuser . .

USER appuser

# Build the data and model inside the image (D30): models/*.pkl and
# data/features/ are excluded from the build context.
RUN python scripts/regenerate_data.py && python -m src.training.train

# The serving path writes structured logs and prediction JSONL here.
RUN mkdir -p logs/predictions

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/v1/health', timeout=4).status==200 else 1)"

CMD ["python", "-m", "src.api.server"]
