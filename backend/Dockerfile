FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

ENV PORT=8089
ENV SCDS_BUILD_FINGERPRINT=scds-v2.1.0-unified-decision-object-platform-context-foundation
ENV SCDS_SOURCE_COMMIT=release-v2.1.0
ENV SCDS_MAX_REQUEST_BYTES=1048576
ENV SCDS_PUBLIC_RATE_LIMIT=60

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
