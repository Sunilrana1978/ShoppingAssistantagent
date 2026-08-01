#!/usr/bin/env bash
set -e

SERVICE_NAME="shopping-user-service"
PROJECT_ID="ecom-cx-agent"
REGION="us-central1"

echo "=========================================================="
echo "🚀 DEPLOYING FASTAPI USER SERVICE TO GOOGLE CLOUD RUN"
echo "=========================================================="
echo "📍 Service: ${SERVICE_NAME}"
echo "📍 Project: ${PROJECT_ID}"
echo "📍 Region:  ${REGION}"
echo "=========================================================="

cd "$(dirname "$0")"

gcloud run deploy "${SERVICE_NAME}" \
    --source . \
    --project "${PROJECT_ID}" \
    --region "${REGION}" \
    --allow-unauthenticated \
    --set-env-vars GCP_PROJECT_ID="${PROJECT_ID}" \
    --quiet

echo ""
echo "=========================================================="
echo "🎉 CLOUD RUN SERVICE DEPLOYED SUCCESSFULLY!"
SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" --project "${PROJECT_ID}" --region "${REGION}" --format='value(status.url)')
echo "🌐 Public URL: ${SERVICE_URL}"
echo "=========================================================="
