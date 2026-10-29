#!/usr/bin/env bash
# Upgrade the New Dev cropsown-connector release (namespace crop) to the connector
# image that this registry's pipeline builds, pinned by digest.
#
# A Helm upgrade of the existing release, with the vendored chart ci/deploy/connector-chart
# (openg2p-connector 0.1.0). It replaces the image that a hand-run `kubectl set image`
# once put on the Deployments with an image owned by Helm.
#
# Values: nothing is hidden in a flag. The running release's user values are read with
# `helm get values` into a file, the image override is written to a second file, and the
# upgrade runs with --reset-values -f <current> -f <override> (never --reuse-values).
# Both files are printed. The override sets only the api, worker and beat image
# (repository@digest) and keeps postgres-init off, as the release has run since its
# first install, and adds the client secret reference below. Everything else is exactly what the release already has.
#
# Upgrade only. The connector database is archived to the New Dev box first (same host
# and directory tree as fresh-install), then a server-side dry run and the rendered
# manifest diff against the running release are printed, and only then is the release
# upgraded. Connector definitions, checkpoints and webhook secrets live in that database
# and are not touched.
#
# PLAN_ONLY=1 (Jenkins connector-plan) stops after printing the image it would set, the
# values, the manifest diff and the dry run. It changes nothing and needs no backup key.
#
# Keycloak client secret: the connector reads the generated secret of the staff-realm client
# `registry-connector` from the Secret $CLIENT_SECRET_NAME (key client_secret) in the crop
# namespace, through a secretKeyRef on CONNECTOR_ADMIN_AUTH_CLIENT_SECRET (never a literal).
# connector-upgrade refuses to run when it is missing or empty; connector-plan reports it.
# See the README in this directory.
#
# Env: KUBECONFIG (crop-dev-kubeconfig); CONNECTOR_IMAGE_REPOSITORY and
# CONNECTOR_IMAGE_DIGEST (set by the pipeline from ECR); BACKUP_SSH_KEY
# (farmer-new-dev-backup-ssh, not needed with PLAN_ONLY=1); optional CONNECTOR_DB
# (default: global.connectorDB of the running release).
set -euo pipefail
set +x
umask 077

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"
: "${KUBECONFIG:?Jenkins must bind crop-dev-kubeconfig}"
: "${CONNECTOR_IMAGE_REPOSITORY:?The pipeline must resolve the connector image repository}"
: "${CONNECTOR_IMAGE_DIGEST:?The pipeline must resolve the connector image digest}"
[[ "$CONNECTOR_IMAGE_DIGEST" =~ ^sha256:[0-9a-f]{64}$ ]] || { echo "Not a sha256 digest: $CONNECTOR_IMAGE_DIGEST" >&2; exit 1; }
: "${PLAN_ONLY:=0}"
[[ "$PLAN_ONLY" == 1 ]] || : "${BACKUP_SSH_KEY:?Bind farmer-new-dev-backup-ssh}"
NAMESPACE=crop
RELEASE=cropsown-connector
CHART=ci/deploy/connector-chart
CLIENT_SECRET_NAME=registry-connector-client
CLIENT_SECRET_KEY=client_secret
BACKUP_HOST=ubuntu@13.201.58.55
BACKUP_DIR=/var/backups/oan/crop
KNOWN_HOSTS=ci/deploy/new-dev-known-hosts
STAMP=$(date -u +%Y%m%d-%H%M%S)
JOB="cropsown-connector-backup-$STAMP"
STATE=$(mktemp -d)
cleanup() {
  kubectl delete job -n "$NAMESPACE" "$JOB" --ignore-not-found --wait=false > /dev/null 2>&1 || true
  rm -rf "$STATE"
}
trap cleanup EXIT
remote() {
  ssh -i "$BACKUP_SSH_KEY" -o BatchMode=yes -o StrictHostKeyChecking=yes \
    -o UserKnownHostsFile="$KNOWN_HOSTS" -o ConnectTimeout=15 "$BACKUP_HOST" "$@"
}

# 1. The release must exist, be deployed, and come from the same chart.
# helm list, not helm status: the deploy node's helm prints no chart in status JSON.
status=$(helm list -n "$NAMESPACE" --filter "^${RELEASE}\$" -o json | python3 -c 'import json,sys; r=json.load(sys.stdin); print(" ".join((r[0]["status"], r[0]["chart"])) if r else "missing")')
echo "Current release: $RELEASE ($status)"
test "$status" = "deployed openg2p-connector-0.1.0"
helm history "$RELEASE" -n "$NAMESPACE" --max 5
kubectl get secret -n "$NAMESPACE" commons-postgresql -o name > /dev/null

# Keycloak client secret for the registry-connector client (copied into this namespace from
# the Commons Secret `registry-connector` by the documented sync step).
secret_present() {
  local value
  value=$(kubectl get secret -n "$NAMESPACE" "$CLIENT_SECRET_NAME" -o "jsonpath={.data.${CLIENT_SECRET_KEY}}" 2> /dev/null || true)
  [[ -n "$value" ]]
}
if secret_present; then
  echo "Keycloak client secret: PRESENT (Secret $NAMESPACE/$CLIENT_SECRET_NAME, key $CLIENT_SECRET_KEY)"
elif [[ "$PLAN_ONLY" == 1 ]]; then
  echo "Keycloak client secret: MISSING (Secret $NAMESPACE/$CLIENT_SECRET_NAME, key $CLIENT_SECRET_KEY). connector-upgrade would refuse to run."
else
  echo "Refusing to upgrade: Secret $NAMESPACE/$CLIENT_SECRET_NAME with key $CLIENT_SECRET_KEY is missing or empty." >&2
  echo "The staff-realm client registry-connector is created by the Commons keycloak-init and its secret is written by the Commons client-secrets-sync Job to Secret registry-connector in the commons namespace; copy it into $NAMESPACE first (ci/deploy/README.md). Nothing was changed." >&2
  exit 1
fi

# 2. The values: current user values of the release, plus the image override.
helm get values "$RELEASE" -n "$NAMESPACE" -o json > "$STATE/current.values.json"
CONNECTOR_DB="${CONNECTOR_DB:-$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("global", {}).get("connectorDB", ""))' "$STATE/current.values.json")}"
PGHOST_VALUE=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("global", {}).get("postgresqlHost") or "commons-postgresql.commons.svc.cluster.local")' "$STATE/current.values.json")
[[ -n "$CONNECTOR_DB" ]] || { echo "global.connectorDB is not in the release values; set CONNECTOR_DB" >&2; exit 1; }
IMAGE="$CONNECTOR_IMAGE_REPOSITORY@$CONNECTOR_IMAGE_DIGEST"
python3 - "$STATE/override.values.json" "$CONNECTOR_IMAGE_REPOSITORY" "$CONNECTOR_IMAGE_DIGEST" <<'PY'
import json, sys
path, repository, digest = sys.argv[1:4]
image = {"repository": repository, "tag": "", "digest": digest}
override = {name: {"image": dict(image)} for name in ("api", "worker", "beat")}
override["postgres-init"] = {"enabled": False}
override["extraEnvFrom"] = {"CONNECTOR_ADMIN_AUTH_CLIENT_SECRET": {"secretKeyRef": {
    "name": "registry-connector-client", "key": "client_secret", "optional": False}}}
json.dump(override, open(path, "w"), indent=2)
PY
echo "=== image this run sets on api, worker and beat ==="
echo "$IMAGE"
echo "=== current user values of $RELEASE (helm get values) ==="
cat "$STATE/current.values.json"; echo
echo "=== override applied on top ==="
cat "$STATE/override.values.json"; echo
echo "=== end of values ==="

plan() {
  helm lint "$CHART" -f "$STATE/current.values.json" -f "$STATE/override.values.json"
  helm get manifest "$RELEASE" -n "$NAMESPACE" > "$STATE/current.yaml"
  helm template "$RELEASE" "$CHART" -n "$NAMESPACE" -f "$STATE/current.values.json" -f "$STATE/override.values.json" > "$STATE/target.yaml"
  echo "=== manifest diff (running release -> git chart + image $IMAGE) ==="
  diff -u "$STATE/current.yaml" "$STATE/target.yaml" || true
  echo "=== end of diff ==="
  helm upgrade "$RELEASE" "$CHART" -n "$NAMESPACE" --reset-values \
    -f "$STATE/current.values.json" -f "$STATE/override.values.json" --dry-run=server > /dev/null
  echo "Server-side dry run passed."
}
if [[ "$PLAN_ONLY" == 1 ]]; then
  plan
  echo "PLAN_ONLY: nothing was changed."
  exit 0
fi
remote true

# 3. Archive the connector database (definitions, checkpoints, secrets live here).
kubectl apply -f - <<YAML
apiVersion: batch/v1
kind: Job
metadata:
  name: $JOB
  namespace: $NAMESPACE
  labels:
    app.kubernetes.io/name: cropsown-connector-backup
spec:
  backoffLimit: 0
  ttlSecondsAfterFinished: 3600
  template:
    metadata:
      labels:
        app.kubernetes.io/name: cropsown-connector-backup
    spec:
      restartPolicy: Never
      containers:
        - name: postgres
          image: docker.io/openg2p/postgresql:16.4.0-debian-12-r14
          env:
            - name: PGHOST
              value: "$PGHOST_VALUE"
            - name: PGUSER
              value: postgres
            - name: PGPASSWORD
              valueFrom:
                secretKeyRef:
                  name: commons-postgresql
                  key: postgres-password
            - name: CONNECTOR_DB
              value: "$CONNECTOR_DB"
          command: ["bash", "-c"]
          args:
            - |
              set -euo pipefail
              cd /tmp
              pg_dump -Fc -d "\$CONNECTOR_DB" -f "\$CONNECTOR_DB.dump"
              pg_restore --list "\$CONNECTOR_DB.dump" > /dev/null
              sha256sum ./*.dump > SHA256SUMS
              touch READY
              while [ ! -f DONE ]; do sleep 5; done
YAML
kubectl wait -n "$NAMESPACE" --for=condition=Ready pod -l "job-name=$JOB" --timeout=300s > /dev/null
POD=$(kubectl get pod -n "$NAMESPACE" -l "job-name=$JOB" -o name | head -n 1)
POD=${POD#pod/}
test -n "$POD"
for _ in $(seq 1 120); do
  if kubectl exec -n "$NAMESPACE" "$POD" -- test -f /tmp/READY 2> /dev/null; then break; fi
  if [[ "$(kubectl get pod -n "$NAMESPACE" "$POD" -o jsonpath='{.status.phase}')" == Failed ]]; then
    echo 'Connector database archive failed; nothing was changed.' >&2
    exit 1
  fi
  sleep 5
done
kubectl exec -n "$NAMESPACE" "$POD" -- test -f /tmp/READY
mkdir -p "$STATE/backup"
for name in "$CONNECTOR_DB.dump" SHA256SUMS; do
  kubectl cp -n "$NAMESPACE" "$POD:/tmp/$name" "$STATE/backup/$name" > /dev/null
done
(cd "$STATE/backup" && sha256sum -c SHA256SUMS > /dev/null)
kubectl exec -n "$NAMESPACE" "$POD" -- touch /tmp/DONE
remote "sudo -n install -d -m 700 -o root -g root $BACKUP_DIR"
for name in "$CONNECTOR_DB.dump" SHA256SUMS; do
  expected=$(sha256sum "$STATE/backup/$name" | cut -d ' ' -f 1)
  written=$(remote "sudo -n tee $BACKUP_DIR/$STAMP-connector-$name | sha256sum" < "$STATE/backup/$name" | cut -d ' ' -f 1)
  if [[ "$written" != "$expected" ]]; then
    echo "Archive $name did not arrive intact on the New Dev box; nothing was changed." >&2
    exit 1
  fi
done
echo "Archived $CONNECTOR_DB to $BACKUP_HOST:$BACKUP_DIR/$STAMP-connector-*"

# 4. Show what changes: rendered manifest diff and a server-side dry run.
plan

# 5. Upgrade.
helm upgrade "$RELEASE" "$CHART" -n "$NAMESPACE" --reset-values \
  -f "$STATE/current.values.json" -f "$STATE/override.values.json" --wait --timeout 10m
for d in api worker beat ui; do
  kubectl rollout status -n "$NAMESPACE" "deployment/$RELEASE-$d" --timeout=300s
done

# 6. Verify the running pods carry the pinned image and the API answers.
for d in api worker beat; do
  got=$(kubectl get deployment -n "$NAMESPACE" "$RELEASE-$d" -o jsonpath='{.spec.template.spec.containers[0].image}')
  test "$got" = "$IMAGE" || { echo "$RELEASE-$d runs $got, expected $IMAGE" >&2; exit 1; }
done
API_POD=$(kubectl get pod -n "$NAMESPACE" -l "app.kubernetes.io/instance=$RELEASE,app.kubernetes.io/component=api" -o name | head -n 1)
kubectl exec -n "$NAMESPACE" "${API_POD#pod/}" -- python -c 'import urllib.request; print(urllib.request.urlopen("http://127.0.0.1:8050/health", timeout=10).status)'
helm history "$RELEASE" -n "$NAMESPACE" --max 3
echo "Upgraded $RELEASE in $NAMESPACE to $IMAGE (archive: $BACKUP_HOST:$BACKUP_DIR/$STAMP-connector-*)"
