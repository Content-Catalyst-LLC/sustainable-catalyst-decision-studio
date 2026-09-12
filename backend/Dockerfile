FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8089 \
    SCDS_BUILD_FINGERPRINT=scds-v2.3.1-criteria-alternatives-tradeoff-matrix \
    SCDS_SOURCE_COMMIT=release-v2.3.1 \
    SCDS_MAX_REQUEST_BYTES=1048576 \
    SCDS_PUBLIC_RATE_LIMIT=60 \
    SCDS_RATE_WINDOW_SECONDS=60

WORKDIR /app

COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app

EXPOSE 8089

HEALTHCHECK --interval=20s --timeout=5s --start-period=10s --retries=6 \
  CMD python -c "import json,urllib.request; d=json.load(urllib.request.urlopen('http://127.0.0.1:8089/health', timeout=3)); raise SystemExit(0 if d.get('ok') and d.get('version') == '2.3.1' else 1)"

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
