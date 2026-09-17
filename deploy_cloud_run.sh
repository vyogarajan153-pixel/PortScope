#!/usr/bin/env bash
# Deploy PortScope to Google Cloud Run.
# Prereqs: gcloud CLI installed and authenticated (gcloud auth login),
# a GCP project selected (gcloud config set project YOUR_PROJECT_ID),
# and billing + Cloud Run + Cloud Build APIs enabled on that project.
set -euo pipefail

SERVICE_NAME="portscope"
REGION="us-central1"   # change to a region near you

# Builds the container with Cloud Build and deploys it to Cloud Run
# straight from source -- no need to build/push the image yourself.
gcloud run deploy "$SERVICE_NAME" \
  --source . \
  --region "$REGION" \
  --allow-unauthenticated \
  --port 8080

echo "Done. Cloud Run will print the live *.run.app URL above."
