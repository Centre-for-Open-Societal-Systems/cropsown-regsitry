#!/usr/bin/env bash
# Offline check of ci/deploy/connector-chart and the image override that
# ci/deploy/upgrade-crop-connector.sh applies: the digest wins over the tag on api,
# worker and beat, the UI image is left as the release has it, and postgres-init
# renders no Job. Needs helm.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
dir=$(mktemp -d)
trap 'rm -rf "$dir"' EXIT
digest=sha256:$(printf 'a%.0s' $(seq 1 64))
repo=123456789012.dkr.ecr.ap-south-1.amazonaws.com/gen2/cropsown-registry/registry-connector
cat > "$dir/current.json" <<JSON
{"fullnameOverride": "cropsown-connector",
 "global": {"connectorDB": "cropsown_connector"},
 "api": {"image": {"repository": "old/connector-service", "tag": "old"}},
 "ui": {"image": {"repository": "old/connector-ui", "tag": "ui-tag"}},
 "extraEnv": {"CONNECTOR_VALIDATE_MAPPED_PAYLOAD": "true"}}
JSON
cat > "$dir/override.json" <<JSON
{"api": {"image": {"repository": "$repo", "tag": "", "digest": "$digest"}},
 "worker": {"image": {"repository": "$repo", "tag": "", "digest": "$digest"}},
 "beat": {"image": {"repository": "$repo", "tag": "", "digest": "$digest"}},
 "postgres-init": {"enabled": false}}
JSON
helm lint ../deploy/connector-chart -f "$dir/current.json" -f "$dir/override.json" > /dev/null
helm template cropsown-connector connector-chart -n crop -f "$dir/current.json" -f "$dir/override.json" > "$dir/out.yaml"
test "$(grep -c "image: \"$repo@$digest\"" "$dir/out.yaml")" -eq 3
grep -q 'image: "old/connector-ui:ui-tag"' "$dir/out.yaml"
test "$(grep -c 'name: CONNECTOR_VALIDATE_MAPPED_PAYLOAD$' "$dir/out.yaml")" -ge 3
if grep -q 'kind: Job' "$dir/out.yaml"; then echo "FAIL: the chart renders a Job" >&2; exit 1; fi
if grep -q 'CONNECTOR_ADMIN_AUTH_CLIENT_SECRET' "$dir/out.yaml"; then echo "FAIL: a client secret reference is rendered" >&2; exit 1; fi
echo "PASS: cropsown-connector chart renders the digest-pinned image on api, worker and beat"
