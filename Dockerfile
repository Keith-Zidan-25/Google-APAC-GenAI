# Builder
FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Runner
FROM python:3.11-slim

WORKDIR /app

COPY --from=builder /install /usr/local

COPY main.py .
COPY Verifact/ ./Verifact/

# Cloud Run injects PORT env var — default 8080
ENV PORT=8080
ENV MCP_PORT=8081

# Credentials: On Cloud Run the attached service account is used automatically
# via Application Default Credentials. No key file needed.
# Non-GCP API keys are injected via --set-env-vars or Secret Manager at deploy time.
ENV GOOGLE_GENAI_USE_VERTEXAI=FALSE
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 8080

CMD ["python", "main.py"]