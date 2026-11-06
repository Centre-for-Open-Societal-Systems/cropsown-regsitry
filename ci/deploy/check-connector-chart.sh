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
repo=123456789012.dkr.ecr.ap-south-1.amazonaws.com/openg2p/cropsown-registry/registry-connector
ui_digest=sha256:$(printf 'b%.0s' $(seq 1 64))
ui_repo=123456789012.dkr.ecr.ap-south-1.amazonaws.com/openg2p/cropsown-registry/registry-connector-ui
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
if grep -q 'kind: Job' "$dir/out.yaml"; then echo "FAIL: the chart renders a Job without definitions" >&2; exit 1; fi
# With the definitions file the chart adds exactly the post-upgrade definitions hook.
helm lint connector-chart -f "$dir/current.json" -f "$dir/override.json" -f definitions.newdev.yaml > /dev/null
helm template cropsown-connector connector-chart -n crop -f "$dir/current.json" -f "$dir/override.json" -f definitions.newdev.yaml > "$dir/defs.yaml"
test "$(grep -c 'kind: Job' "$dir/defs.yaml")" -eq 1
grep -q 'helm.sh/hook: post-install,post-upgrade' "$dir/defs.yaml"
grep -q 'name: cropsown-connector-definitions$' "$dir/defs.yaml"
grep -q 'farmer-registry.farmer-profile.changed.v1' "$dir/defs.yaml"
test "$(grep -c 'name: CD_[0-9]*_AUTH_EMAIL$' "$dir/defs.yaml")" -eq 4
helm lint connector-chart -f "$dir/current.json" -f definitions.staging.yaml > /dev/null
if grep -q 'CONNECTOR_ADMIN_AUTH_CLIENT_SECRET' "$dir/out.yaml"; then echo "FAIL: a client secret reference is rendered" >&2; exit 1; fi
# Staging: the release values plus the digests the staging pipeline writes (any digests here).
staging=$(mktemp)
trap 'rm -rf "$dir" "$staging"' EXIT
sd=sha256:$(printf 'a%.0s' $(seq 1 64))
sui=sha256:$(printf 'b%.0s' $(seq 1 64))
repo=379220350808.dkr.ecr.ap-south-1.amazonaws.com/openg2p/cropsown-registry
override='{"api":{"image":{"repository":"'$repo'/registry-connector","tag":"t","digest":"'$sd'"}},"worker":{"image":{"repository":"'$repo'/registry-connector","tag":"t","digest":"'$sd'"}},"beat":{"image":{"repository":"'$repo'/registry-connector","tag":"t","digest":"'$sd'"}},"ui":{"image":{"repository":"'$repo'/registry-connector-ui","tag":"t","digest":"'$sui'"}}}'
echo "$override" > "$staging.json"
helm lint connector-chart -f cropsown-connector.staging.values.yaml -f "$staging.json" -f definitions.staging.yaml > /dev/null
helm template cropsown-connector connector-chart -n crop -f cropsown-connector.staging.values.yaml -f "$staging.json" -f definitions.staging.yaml > "$staging"
rm -f "$staging.json"
test "$(grep -c "image: \"$repo/registry-connector@$sd\"" "$staging")" -eq 4  # api, worker, beat and the definitions Job
grep -q "image: \"$repo/registry-connector-ui@$sui\"" "$staging"
if grep -q 'connector-service\|postgres-init:develop' "$staging"; then echo "FAIL: staging renders a retired image or the database init Job" >&2; exit 1; fi
test "$(grep -c 'kind: Job' "$staging")" -eq 1
grep -q 'name: cropsown-connector-postgres-init$' "$staging"  # kept by preserved-init-serviceaccount.yaml
grep -q 'connector-cropsown-registry.crop.staging.openg2p.test' "$staging"
grep -q 'cropsown_connector_crop' "$staging"
echo "PASS: cropsown-connector chart renders the digest-pinned images on api, worker, beat and ui, and keeps the postgres-init ServiceAccount"
