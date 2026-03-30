#!/bin/bash
# deploy.sh — Deploy VeriFact to Cloud Run
# Run from the root of your project (parent of Verifact/)
# Usage: bash deploy.sh

set -e  # exit on any error

# ── Config — edit these ──────────────────────────────────────────────────────
PROJECT_ID="codelabs-project-491110"
REGION="asia-south1"
SERVICE_NAME="verifact"
SERVICE_ACCOUNT="verifact-service-agent@${PROJECT_ID}.iam.gserviceaccount.com"

# ── Enable required APIs ─────────────────────────────────────────────────────
echo "Enabling required APIs..."
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  bigquery.googleapis.com \
  secretmanager.googleapis.com \
  --project=$PROJECT_ID

# ── Create service account (skip if already exists) ──────────────────────────
echo "Setting up service account..."
gcloud iam service-accounts create verifact-service-agent \
  --display-name="VeriFact Agent Service Account" \
  --project=$PROJECT_ID 2>/dev/null || echo "Service account already exists, skipping."

# Grant BigQuery access
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/bigquery.dataViewer"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/bigquery.jobUser"

# ── Store API keys in Secret Manager ────────────────────────────────────────
# Run these once manually before deploying:
#
#   echo -n "your-serper-key" | \
#     gcloud secrets create SERPER_API_KEY --data-file=- --project=$PROJECT_ID
#
#   echo -n "your-google-cse-key" | \
#     gcloud secrets create GOOGLE_CSE_API_KEY --data-file=- --project=$PROJECT_ID
#
#   echo -n "your-cse-id" | \
#     gcloud secrets create GOOGLE_CSE_ID --data-file=- --project=$PROJECT_ID
#
#   echo -n "your-gemini-key" | \
#     gcloud secrets create GOOGLE_API_KEY --data-file=- --project=$PROJECT_ID

# Grant secret access to service account
for SECRET in SERPER_API_KEY GOOGLE_CSE_API_KEY GOOGLE_CSE_ID GOOGLE_API_KEY; do
  gcloud secrets add-iam-policy-binding $SECRET \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/secretmanager.secretAccessor" \
    --project=$PROJECT_ID 2>/dev/null || echo "Secret $SECRET binding skipped."
done

# ── Deploy to Cloud Run ───────────────────────────────────────────────────────
echo "Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
  --source . \
  --region $REGION \
  --project $PROJECT_ID \
  --service-account $SERVICE_ACCOUNT \
  --port 8080 \
  --memory 1Gi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 10 \
  --timeout 300 \
  --set-env-vars "GOOGLE_GENAI_USE_VERTEXAI=FALSE,BIGQUERY_PROJECT_ID=${PROJECT_ID},BIGQUERY_DATASET_ID=verifact,MCP_PORT=8081" \
  --set-secrets "GOOGLE_API_KEY=GOOGLE_API_KEY:latest,SERPER_API_KEY=SERPER_API_KEY:latest,GOOGLE_CSE_API_KEY=GOOGLE_CSE_API_KEY:latest,GOOGLE_CSE_ID=GOOGLE_CSE_ID:latest" \
  --allow-unauthenticated

echo ""
echo "Deployment complete!"
echo "Service URL:"
gcloud run services describe $SERVICE_NAME \
  --region $REGION \
  --project $PROJECT_ID \
  --format "value(status.url)"