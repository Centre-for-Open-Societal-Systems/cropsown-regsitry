#!/usr/bin/env bash
# Deploy a Crop Sown Registry build from ECR into the dev cluster.
#
# This is the body of the Jenkinsfile's 'Deploy to Dev' stage, pulled out so the
# same deploy can be run by hand — after a build held at the ECR push with
# DEV_DEPLOY=false, or to roll the namespace back to an earlier build. Jenkins
# supplies the tag and the credentials; everything else defaults to what the
# pipeline uses, so a manual run lands exactly where a pipeline run would.
#
# It deploys whatever cluster KUBECONFIG points at. In Jenkins that is the
# gen2-kubeconfig credential (the cluster behind rancher.openg2p.test); by hand
# it is yours, so the context is printed before anything is changed.
#
# The images must already be in ECR — this builds nothing.
#
# Usage:
#   ./ci/deploy-dev.sh <tag>
#   TAG=<tag> ./ci/deploy-dev.sh
#
#   AWS_ACCOUNT_ID=123456789012 ./ci/deploy-dev.sh develop-42
#
# Prefer a build-numbered tag (develop-42) over the moving branch tag (develop).
# A release already on `develop` renders the same manifests again, so helm has
# nothing to roll and the pods keep running whatever image they last pulled.
#
# Env:
#   AWS_ACCOUNT_ID  account that owns the ECR registry (or set ECR_REGISTRY)
#   ECR_REGISTRY    full registry host; overrides AWS_ACCOUNT_ID + AWS_REGION
#   AWS_REGION      default ap-south-1
#   ECR_BASE        default gen2/cropsown-registry
#   NAMESPACE       default crop
#   RELEASE_NAME    default cropsown-registry
#   CHART_DIR       default helm/openg2p-cropsown-registry
#   KUBECONFIG      the cluster to deploy to
#
# Requires: helm, kubectl.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

TAG="${1:-${TAG:-}}"
AWS_REGION="${AWS_REGION:-ap-south-1}"
ECR_BASE="${ECR_BASE:-gen2/cropsown-registry}"
NAMESPACE="${NAMESPACE:-crop}"
RELEASE_NAME="${RELEASE_NAME:-cropsown-registry}"
CHART_DIR="${CHART_DIR:-helm/openg2p-cropsown-registry}"

die()  { echo "ERROR: $*" >&2; exit 1; }
note() { echo "=== $* ==="; }

if [ -z "$TAG" ]; then
  echo "usage: $0 <tag>" >&2
  echo "   or: TAG=<tag> $0" >&2
  exit 2
fi

if [ -z "${ECR_REGISTRY:-}" ]; then
  [ -n "${AWS_ACCOUNT_ID:-}" ] \
    || die "set AWS_ACCOUNT_ID (aws sts get-caller-identity --query Account --output text) or ECR_REGISTRY"
  ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
fi

# Fail on a missing tool before touching the cluster, not halfway through.
command -v helm    >/dev/null || die "helm not found on PATH"
command -v kubectl >/dev/null || die "kubectl not found on PATH"
[ -f "$CHART_DIR/Chart.yaml" ] || die "no chart at $CHART_DIR"

note "Deploying ${RELEASE_NAME} to namespace ${NAMESPACE}"
echo "context:  $(kubectl config current-context 2>/dev/null || echo '(none)')"
echo "images:   ${ECR_REGISTRY}/${ECR_BASE}/*:${TAG}"

# The wrapper chart owns no templates; every manifest comes from the pinned
# openg2p-registry subchart, so the dependency must be present before install.
helm repo add openg2p https://openg2p.github.io/openg2p-helm || true
helm repo update openg2p || true
helm dependency build "./${CHART_DIR}"

# Point one chart component at an image built by this pipeline.
#
# NB every path is UNDER the subchart alias (registry.*), sanity included — see
# CHART_IMAGE_PATHS in .gitlab-ci.yml. A top-level `sanity.image.*` writes a key
# the chart never reads, so the sanity Job would silently keep the values.yaml
# default tag.
SETS=()
set_image() {
  SETS+=(--set "registry.$1.image.repository=${ECR_REGISTRY}/${ECR_BASE}/$2"
         --set "registry.$1.image.tag=${TAG}")
}
set_image staffApi     staff-api
set_image partnerApi   partner-api
set_image celeryWorker celery
set_image celeryBeat   celery
set_image dbSeed       db-seed
set_image sanity       sanity-tests

helm upgrade --install "${RELEASE_NAME}" "./${CHART_DIR}" \
  --namespace "${NAMESPACE}" \
  --create-namespace \
  --timeout 10m \
  "${SETS[@]}"

note "Waiting for rollout"
# staff-portal-api, not staff-api: the subchart sets
# staffApi.nameOverride=staff-portal-api, so that is the Deployment the chart
# actually creates. The old name matched nothing, and `|| true` swallowed the
# error — this step reported success without ever waiting for a rollout.
kubectl rollout status "deployment/${RELEASE_NAME}-staff-portal-api" \
  -n "${NAMESPACE}" --timeout=120s || true

note "Deployment status"
kubectl get pods -n "${NAMESPACE}" | grep "${RELEASE_NAME}" || true
