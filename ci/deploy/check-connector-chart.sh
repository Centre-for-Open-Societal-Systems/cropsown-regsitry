#!/usr/bin/env bash
# Offline check of ci/deploy/connector-chart and the image override that
# ci/deploy/upgrade-crop-connector.sh applies: the digest wins over the tag on api,
# worker, beat and ui, postgres-init stays at the release's disabled value and renders no
# Job, and the ServiceAccount the release already owns is still rendered. Needs helm.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
dir=$(mktemp -d)
trap 'rm -rf "$dir"' EXIT
digest=sha256:$(printf 'a%.0s' $(seq 1 64))
repo=123456789012.dkr.ecr.ap-south-1.amazonaws.com/gen2/cropsown-registry/registry-connector
ui_digest=sha256:$(printf 'b%.0s' $(seq 1 64))
ui_repo=123456789012.dkr.ecr.ap-south-1.amazonaws.com/gen2/cropsown-registry/registry-connector-ui
cat > "$dir/current.json" <<JSON
{"fullnameOverride": "cropsown-connector",
 "global": {"connectorDB": "cropsown_connector"},
 "api": {"image": {"repository": "old/connector-service", "tag": "old"}},
 "ui": {"image": {"repository": "old/connector-ui", "tag": "ui-tag"}},
 "postgres-init": {"enabled": false},
 "extraEnv": {"CONNECTOR_VALIDATE_MAPPED_PAYLOAD": "true"}}
JSON
cat > "$dir/override.json" <<JSON
{"api": {"image": {"repository": "$repo", "tag": "", "digest": "$digest"}},
 "worker": {"image": {"repository": "$repo", "tag": "", "digest": "$digest"}},
 "beat": {"image": {"repository": "$repo", "tag": "", "digest": "$digest"}},
 "ui": {"image": {"repository": "$ui_repo", "tag": "", "digest": "$ui_digest"}}}
JSON
helm lint ../deploy/connector-chart -f "$dir/current.json" -f "$dir/override.json" > /dev/null
helm template cropsown-connector connector-chart -n crop -f "$dir/current.json" -f "$dir/override.json" > "$dir/out.yaml"
test "$(grep -c "image: \"$repo@$digest\"" "$dir/out.yaml")" -eq 3
test "$(grep -c "image: \"$ui_repo@$ui_digest\"" "$dir/out.yaml")" -eq 1
if grep -q 'old/connector' "$dir/out.yaml"; then echo "FAIL: an old image is still rendered" >&2; exit 1; fi
grep -q 'name: cropsown-connector-postgres-init$' "$dir/out.yaml"
test "$(grep -c 'name: CONNECTOR_VALIDATE_MAPPED_PAYLOAD$' "$dir/out.yaml")" -ge 3
if grep -q 'kind: Job' "$dir/out.yaml"; then echo "FAIL: the chart renders a Job" >&2; exit 1; fi
if grep -q 'CONNECTOR_ADMIN_AUTH_CLIENT_SECRET' "$dir/out.yaml"; then echo "FAIL: a client secret reference is rendered" >&2; exit 1; fi
echo "PASS: cropsown-connector chart renders the digest-pinned images on api, worker, beat and ui, and keeps the postgres-init ServiceAccount"
