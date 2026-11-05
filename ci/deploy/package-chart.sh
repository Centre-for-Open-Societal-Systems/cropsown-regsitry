#!/usr/bin/env bash
# Package helm/openg2p-cropsown-registry with this build's images into built-chart/, with
# scripts/ci/package_chart.py of oan-helm. The deploy installs that archive and publish-chart.sh
# publishes the same file. chart-images.tsv comes from the Build & Push stage.
set -euo pipefail
: "${BRANCH_NAME:?Jenkins sets the branch}"
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
git clone --quiet --depth 1 --filter=blob:none --sparse \
  https://github.com/Centre-for-Open-Societal-Systems/oan-helm.git "$WORK/oan-helm"
git -C "$WORK/oan-helm" sparse-checkout set scripts/ci
python3 "$WORK/oan-helm/scripts/ci/package_chart.py" \
  --chart helm/openg2p-cropsown-registry --images chart-images.tsv --output built-chart \
  --source-repository Centre-for-Open-Societal-Systems/cropsown-regsitry \
  --source-commit "$(git rev-parse HEAD)" --subject "$(git log -1 --pretty=%s)" \
  --release cropsown-registry --namespace crop \
  --overlay environments/dev/values/cropsown.yaml --branch "$BRANCH_NAME"
