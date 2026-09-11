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
# ci/deploy-staging.sh runs this same deploy under the staging release name, so a
# change here reaches both environments.
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
#   HELM_VERSION    helm to fetch when none is on PATH (default v4.2.4)
#   KUBECTL_VERSION kubectl to fetch when none is on PATH (default v1.36.1)
#   TOOLS_DIR       where fetched tools are kept (default <repo>/.tools)
#
# Requires: helm and kubectl, or — on Linux — curl, tar and sha256sum to fetch
# them.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

TAG="${1:-${TAG:-}}"
AWS_REGION="${AWS_REGION:-ap-south-1}"
ECR_BASE="${ECR_BASE:-gen2/cropsown-registry}"
NAMESPACE="${NAMESPACE:-crop}"
RELEASE_NAME="${RELEASE_NAME:-cropsown-registry}"
CHART_DIR="${CHART_DIR:-helm/openg2p-cropsown-registry}"
HELM_VERSION="${HELM_VERSION:-v4.2.4}"
KUBECTL_VERSION="${KUBECTL_VERSION:-v1.36.1}"
TOOLS_DIR="${TOOLS_DIR:-$REPO_ROOT/.tools}"

die()  { echo "ERROR: $*" >&2; exit 1; }
note() { echo "=== $* ==="; }

# The Jenkins build agent carries docker and the aws CLI but neither helm nor
# kubectl, and the first deploy from it died on "helm not found on PATH" after
# the images had built and pushed. Nothing in this repo can install software on
# that node, so a missing tool is fetched instead: a pinned release, checked
# against its published sha256, into TOOLS_DIR. Each version gets its own
# directory, so the download happens once per workspace and a pin bump fetches
# afresh. A tool already on PATH always wins.
fetch_arch() {
  [ "$(uname -s)" = "Linux" ] || die "$1 not found on PATH; install it (fetching is Linux-only)"
  command -v curl >/dev/null || die "$1 not found on PATH, and no curl to fetch it"
  case "$(uname -m)" in
    x86_64|amd64)  echo amd64 ;;
    aarch64|arm64) echo arm64 ;;
    *) die "$1 not found on PATH, and no $1 build for $(uname -m)" ;;
  esac
}

ensure_helm() {
  command -v helm >/dev/null && return
  local dir="$TOOLS_DIR/helm-$HELM_VERSION"
  if [ ! -x "$dir/helm" ]; then
    local arch tgz tmp
    arch="$(fetch_arch helm)"
    tgz="helm-$HELM_VERSION-linux-$arch.tar.gz"
    note "helm not on PATH — fetching $HELM_VERSION"
    tmp="$(mktemp -d)"
    curl -fsSL --retry 3 -o "$tmp/$tgz" "https://get.helm.sh/$tgz"
    curl -fsSL --retry 3 -o "$tmp/$tgz.sha256sum" "https://get.helm.sh/$tgz.sha256sum"
    (cd "$tmp" && sha256sum -c --quiet "$tgz.sha256sum") || die "helm $HELM_VERSION failed its checksum"
    tar -xzf "$tmp/$tgz" -C "$tmp"
    mkdir -p "$dir"
    mv "$tmp/linux-$arch/helm" "$dir/helm"
    rm -rf "$tmp"
  fi
  PATH="$dir:$PATH"
}

ensure_kubectl() {
  command -v kubectl >/dev/null && return
  local dir="$TOOLS_DIR/kubectl-$KUBECTL_VERSION"
  if [ ! -x "$dir/kubectl" ]; then
    local arch url tmp
    arch="$(fetch_arch kubectl)"
    url="https://dl.k8s.io/release/$KUBECTL_VERSION/bin/linux/$arch/kubectl"
    note "kubectl not on PATH — fetching $KUBECTL_VERSION"
    tmp="$(mktemp -d)"
    curl -fsSL --retry 3 -o "$tmp/kubectl" "$url"
    curl -fsSL --retry 3 -o "$tmp/kubectl.sha256" "$url.sha256"
    # The published file is the bare hash, without the filename sha256sum wants.
    (cd "$tmp" && echo "$(cat kubectl.sha256)  kubectl" | sha256sum -c --quiet) \
      || die "kubectl $KUBECTL_VERSION failed its checksum"
    chmod +x "$tmp/kubectl"
    mkdir -p "$dir"
    mv "$tmp/kubectl" "$dir/kubectl"
    rm -rf "$tmp"
  fi
  PATH="$dir:$PATH"
}

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

# Settle the tools before touching the cluster, not halfway through.
ensure_helm
ensure_kubectl
[ -f "$CHART_DIR/Chart.yaml" ] || die "no chart at $CHART_DIR"

note "Deploying ${RELEASE_NAME} to namespace ${NAMESPACE}"
echo "helm:     $(helm version --short 2>/dev/null || echo '?') ($(command -v helm))"
echo "kubectl:  $(kubectl version --client 2>/dev/null | head -1 || echo '?') ($(command -v kubectl))"
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
