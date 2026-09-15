#!/usr/bin/env bash
# Deploy cropsown-registry to the dev cluster's `crop` namespace with helm.
#
# The Jenkinsfile's Deploy to Dev stage runs this on the vpn-agent2 node with the
# crop-dev-kubeconfig credential (the crop-ci service account of the RKE2 cluster
# at https://10.0.1.166:6443). It is a script, not inline Groovy, so a deploy by
# hand is the same command:
#
#   KUBECONFIG=<kubeconfig> AWS_ACCOUNT_ID=<id> ./ci/deploy-crop-dev.sh develop-42
#
# What it does, in order:
#   1. Preflight: print the API server and identity; stop at once if the server
#      cannot be reached or the account cannot deploy the namespace.
#   2. helm dependency build.
#   3. Write the values this build owns: image tags, and every public host on
#      <namespace>.openg2p.test (the subchart defaults them to .openg2p.org
#      placeholders, which broke Keycloak, MinIO and IAM).
#   4. helm upgrade --install, layering those values over the live release's own
#      values, so settings made on the release are kept.
#   5. While helm waits on the post-upgrade hooks, print the release's Jobs every
#      minute and save hook pod logs (hook pods are deleted when they fail).
#   6. On failure print those logs, the API pod logs, release history and warning
#      events. On success wait for every Deployment to roll out.
#
# Env:
#   TAG              image tag to deploy (or first argument)       required
#   AWS_ACCOUNT_ID   owner of the ECR registry                      required
#   KUBECONFIG       kubeconfig for the dev cluster                 required
#   AWS_REGION       default ap-south-1
#   ECR_BASE         default gen2/cropsown-registry
#   HELM_RELEASE     default cropsown-registry
#   HELM_NAMESPACE   default crop
#   HELM_CHART_DIR   default helm/openg2p-cropsown-registry
#   BASE_DOMAIN      default <namespace>.openg2p.test (as a helm template)
#   RUN_DB_SEED      true|false, default true   run the db-seed hook Job
#   RUN_SANITY       true|false, default false  run the sanity seed + e2e hook Jobs
#   HELM_TIMEOUT     default 40m
set -euo pipefail

TAG="${1:-${TAG:-}}"
[ -n "$TAG" ] || { echo "usage: $0 <image-tag>" >&2; exit 2; }
: "${AWS_ACCOUNT_ID:?set AWS_ACCOUNT_ID}"
: "${KUBECONFIG:?set KUBECONFIG}"
AWS_REGION="${AWS_REGION:-ap-south-1}"
ECR_BASE="${ECR_BASE:-gen2/cropsown-registry}"
HELM_RELEASE="${HELM_RELEASE:-cropsown-registry}"
HELM_NAMESPACE="${HELM_NAMESPACE:-crop}"
HELM_CHART_DIR="${HELM_CHART_DIR:-helm/openg2p-cropsown-registry}"
[ -n "${BASE_DOMAIN:-}" ] || BASE_DOMAIN='{{ .Release.Namespace }}.openg2p.test'
RUN_DB_SEED="${RUN_DB_SEED:-true}"
RUN_SANITY="${RUN_SANITY:-false}"
HELM_TIMEOUT="${HELM_TIMEOUT:-40m}"
ECR="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_BASE}"

NS=(-n "$HELM_NAMESPACE")
WORK="$(mktemp -d)"
BG_PIDS=()
cleanup() {
  [ "${#BG_PIDS[@]}" -eq 0 ] || kill "${BG_PIDS[@]}" 2>/dev/null || true
  rm -rf "$WORK"
}
trap cleanup EXIT

say() { echo "=== $* ==="; }

# ── 1. Preflight ───────────────────────────────────────────────────────────────
say "Deploy target"
echo "server:    $(kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}')"
echo "namespace: ${HELM_NAMESPACE}"
echo "release:   ${HELM_RELEASE}"
echo "images:    ${ECR}/*:${TAG}"

if ! CONN="$(kubectl get --raw /version --request-timeout=15s 2>&1)"; then
  echo "ERROR: cannot connect to the API server:" >&2
  echo "$CONN" | tail -3 >&2
  echo "  timeout = no route on TCP 6443; x509 = wrong CA/address; Unauthorized = bad token." >&2
  exit 1
fi
kubectl auth whoami 2>/dev/null || true

MISSING=""
for CHECK in "list secrets" "create secrets" "create deployments" "create jobs"; do
  # can-i exits 1 on "no"; compare the printed answer instead.
  ANSWER="$(kubectl auth can-i ${CHECK} "${NS[@]}" 2>/dev/null || true)"
  echo "can-i ${CHECK}: ${ANSWER:-error}"
  [ "$ANSWER" = "yes" ] || MISSING="${MISSING} '${CHECK}'"
done
if [ -n "$MISSING" ]; then
  echo "ERROR: this account may not${MISSING} in namespace ${HELM_NAMESPACE}." >&2
  echo "  Bind it to the admin ClusterRole in that namespace (see ci/k8s/crop-deploy-rbac.yaml)." >&2
  exit 1
fi

# ── 2. Chart dependencies ──────────────────────────────────────────────────────
say "helm dependency build"
helm repo add openg2p https://openg2p.github.io/openg2p-helm >/dev/null 2>&1 || true
helm repo update openg2p >/dev/null
helm dependency build "$HELM_CHART_DIR"

# ── 3. Values this build owns ──────────────────────────────────────────────────
cat > "$WORK/ci-values.yaml" <<EOF
global:
  registryHostname: '{{ .Release.Name }}.${BASE_DOMAIN}'
  keycloakBaseUrl: 'https://keycloak.${BASE_DOMAIN}'
  minioHost: 'minio-api.${BASE_DOMAIN}'
  idGeneratorHostname: 'idgenerator-{{ .Release.Name }}.${BASE_DOMAIN}'
  aweHostname: 'awe.${BASE_DOMAIN}'
registry:
  staffApi:
    image: {repository: '${ECR}/staff-api', tag: '${TAG}'}
  staffUi:
    iamPublicUrl: 'https://staff-iam.${BASE_DOMAIN}'
    envVars:
      COOKIE_DOMAIN: '.${BASE_DOMAIN}'
    image: {repository: '${ECR}/staff-ui', tag: '${TAG}'}
  partnerApi:
    image: {repository: '${ECR}/partner-api', tag: '${TAG}'}
  celeryWorker:
    image: {repository: '${ECR}/celery', tag: '${TAG}'}
  celeryBeat:
    image: {repository: '${ECR}/celery', tag: '${TAG}'}
  dbSeed:
    enabled: ${RUN_DB_SEED}
    image: {repository: '${ECR}/db-seed', tag: '${TAG}'}
  sanity:
    enabled: ${RUN_SANITY}
    image: {repository: '${ECR}/sanity-tests', tag: '${TAG}'}
EOF
echo "db-seed hook: ${RUN_DB_SEED}   sanity hooks: ${RUN_SANITY}"

# The live release's values (hostnames, Keycloak/IAM wiring set on the release).
# Only a missing release — a first install — may go ahead without them.
if ! helm get values "$HELM_RELEASE" "${NS[@]}" -o yaml > "$WORK/current-values.yaml" 2> "$WORK/current.err"; then
  grep -q 'release: not found' "$WORK/current.err" || { cat "$WORK/current.err" >&2; exit 1; }
  echo "No ${HELM_RELEASE} release yet: installing with chart defaults."
  : > "$WORK/current-values.yaml"
fi

# A release left pending by an interrupted run blocks every upgrade with
# "another operation is in progress"; say so plainly instead.
STATUS="$(helm status "$HELM_RELEASE" "${NS[@]}" -o json 2>/dev/null | sed -n 's/.*"status":"\([a-z-]*\)".*/\1/p' | head -1 || true)"
case "$STATUS" in
  pending-*)
    echo "ERROR: release ${HELM_RELEASE} is '${STATUS}' from an interrupted deploy." >&2
    echo "  Roll back to the last good revision: helm -n ${HELM_NAMESPACE} history ${HELM_RELEASE}; helm -n ${HELM_NAMESPACE} rollback ${HELM_RELEASE} <rev>" >&2
    exit 1 ;;
esac

# ── 5. Watchers while helm runs ────────────────────────────────────────────────
# Hook pods are deleted as soon as their Job fails, so save their logs as we go.
# Only this release's own hook pods: <release>-<job>-<5 chars>.
HOOK_POD_RE="^pod/${HELM_RELEASE}-(db-seed|keycloak-init-[0-9]+|sanity(-[a-z]+)*|iam-register)-[a-z0-9]{5}$"
mkdir -p "$WORK/logs"
(
  set +x
  while :; do
    for P in $(kubectl get pods "${NS[@]}" -o name 2>/dev/null | grep -E "$HOOK_POD_RE" || true); do
      N="${P#pod/}"
      kubectl logs "$N" "${NS[@]}" --all-containers --prefix --tail=200 > "$WORK/logs/$N.tmp" 2>/dev/null \
        && mv "$WORK/logs/$N.tmp" "$WORK/logs/$N.log" || rm -f "$WORK/logs/$N.tmp"
      kubectl logs "$N" "${NS[@]}" --all-containers --prefix --tail=200 --previous > "$WORK/logs/$N.prev" 2>/dev/null \
        && mv "$WORK/logs/$N.prev" "$WORK/logs/$N.previous.log" || rm -f "$WORK/logs/$N.prev"
    done
    sleep 10
  done
) &
BG_PIDS+=("$!")

# helm prints nothing while it waits on hooks; show which Job it is waiting on.
(
  set +x
  while :; do
    sleep 60
    echo "--- $(date -u +%H:%M:%S) UTC: ${HELM_RELEASE} jobs (hooks run: db-seed, sanity seeds, iam-register, sanity e2e) ---"
    kubectl get jobs "${NS[@]}" --no-headers 2>/dev/null | grep -E "^${HELM_RELEASE}-" || true
  done
) &
BG_PIDS+=("$!")

# ── 4. Upgrade ─────────────────────────────────────────────────────────────────
say "helm upgrade started $(date -u +%H:%M:%S) UTC (timeout ${HELM_TIMEOUT})"
if ! helm upgrade --install "$HELM_RELEASE" "$HELM_CHART_DIR" "${NS[@]}" \
      -f "$WORK/current-values.yaml" -f "$WORK/ci-values.yaml" --timeout "$HELM_TIMEOUT"; then
  kill "${BG_PIDS[@]}" 2>/dev/null || true
  BG_PIDS=()
  for F in "$WORK"/logs/*.log; do
    [ -f "$F" ] || continue
    say "hook pod log: $(basename "$F" .log)" >&2
    cat "$F" >&2
  done
  for D in staff-portal-api partner-api; do
    say "${HELM_RELEASE}-${D} pod log" >&2
    kubectl logs "deploy/${HELM_RELEASE}-${D}" "${NS[@]}" --all-containers --prefix --tail=60 >&2 || true
  done
  say "release history" >&2
  helm history "$HELM_RELEASE" "${NS[@]}" --max 5 >&2 || true
  say "recent warning events" >&2
  kubectl get events "${NS[@]}" --field-selector type=Warning --sort-by=.lastTimestamp 2>/dev/null | tail -20 >&2 || true
  exit 1
fi
kill "${BG_PIDS[@]}" 2>/dev/null || true
BG_PIDS=()
say "helm upgrade finished $(date -u +%H:%M:%S) UTC"

# ── 6. Rollout ─────────────────────────────────────────────────────────────────
for D in staff-portal-api staff-portal-ui partner-api celery-worker celery-beat-producer; do
  kubectl rollout status "deployment/${HELM_RELEASE}-${D}" "${NS[@]}" --timeout=180s
done
say "Deployed ${TAG} to ${HELM_NAMESPACE}"
kubectl get deploy "${NS[@]}" -o custom-columns=NAME:.metadata.name,READY:.status.readyReplicas,IMAGE:.spec.template.spec.containers[0].image \
  | grep -E "^NAME|^${HELM_RELEASE}-" || true
