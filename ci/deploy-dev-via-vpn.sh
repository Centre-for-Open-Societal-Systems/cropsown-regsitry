#!/usr/bin/env bash
# Deploy dev from an agent that is NOT on the openg2p-Gen2 VPN.
#
# The dev cluster's API server (10.15.0.1:6443, what rancher.openg2p.test
# resolves to) answers only on the openg2p-Gen2 WireGuard VPN, and the Jenkins
# build agent is not on it: every develop build pushed its images and then ended
# UNSTABLE on "context deadline exceeded". Putting the agent itself on the VPN
# (ci/setup-agent-vpn.sh) needs root on that box, and a deploy agent inside the
# cluster needs a new Jenkins node — neither is available.
#
# So the Deploy to Dev stage joins the VPN for the length of the deploy only,
# inside a throwaway container on the agent's Docker daemon — the one the Build
# stage already uses. The tunnel lives in the container's network namespace:
# the agent's own routes never change, nothing needs root on the host, and the
# tunnel is gone when the container is. The container runs ci/deploy-dev.sh
# unchanged, so the deploy is the same one a person on the VPN runs by hand.
#
# The files go in with `docker cp`, not bind mounts, so this also works when the
# agent is itself a container talking to the host's Docker daemon (a bind mount
# would name a path on the host, not in the agent).
#
# Usage:
#   WG_CONF=<peer.conf> KUBECONFIG=<kubeconfig> AWS_ACCOUNT_ID=<id> \
#     ./ci/deploy-dev-via-vpn.sh <tag>
#
# Env:
#   WG_CONF         WireGuard peer config for the openg2p-Gen2 VPN (Jenkins
#                   credential gen2-wireguard-conf). Issue one for CI rather than
#                   reusing a person's: two machines on one key keep taking the
#                   peer's endpoint from each other and both tunnels drop.
#   KUBECONFIG      the dev cluster (Jenkins credential gen2-kubeconfig)
#   AWS_ACCOUNT_ID  and every other variable ci/deploy-dev.sh reads, passed on
#   WG_ALLOWED_IPS  routed through the tunnel (default 10.15.0.1/32)
#   API_CHECK       HOST:PORT that must answer once the tunnel is up
#                   (default 10.15.0.1:6443)
#   DEPLOY_IMAGE    container image (default alpine:3.20)
#
# Exit status: that of ci/deploy-dev.sh, and 3 — "cannot reach the API server",
# which the Jenkinsfile turns into an UNSTABLE build — when the tunnel does not
# come up or the API server does not answer through it.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

TAG="${1:-${TAG:-}}"
WG_ALLOWED_IPS="${WG_ALLOWED_IPS:-10.15.0.1/32}"
API_CHECK="${API_CHECK:-10.15.0.1:6443}"
DEPLOY_IMAGE="${DEPLOY_IMAGE:-alpine:3.20}"

die()  { echo "ERROR: $*" >&2; exit 1; }
note() { echo "=== $* ==="; }

[ -n "$TAG" ] || { echo "usage: $0 <tag>" >&2; exit 2; }
[ -r "${WG_CONF:-}" ]    || die "WG_CONF must name a readable WireGuard peer config"
[ -r "${KUBECONFIG:-}" ] || die "KUBECONFIG must name a readable kubeconfig"
command -v docker >/dev/null || die "docker not found on PATH"

# A config missing any of these comes up as an interface that routes nowhere,
# and the only symptom would be the same timeout this is here to fix.
for want in '\[Interface\]' PrivateKey Address '\[Peer\]' PublicKey Endpoint AllowedIPs; do
  grep -Eq "^[[:space:]]*${want}" "$WG_CONF" \
    || die "WG_CONF has no ${want//\\/} line — is it a WireGuard peer config?"
done

tmp="$(mktemp -d)"
cid=""
cleanup() {
  [ -z "$cid" ] || docker rm -f "$cid" >/dev/null 2>&1 || true
  rm -rf "$tmp"
}
trap cleanup EXIT

# The deploy needs only the scripts and the chart; copying them keeps the
# helm dependency build and fetched tools out of the Jenkins workspace.
mkdir -p "$tmp/work"
cp -R ci helm "$tmp/work/"
cp "$KUBECONFIG" "$tmp/work/kubeconfig"

# Rewritten rather than copied, as ci/setup-agent-vpn.sh does:
#   - CRLF stripped: a config saved on Windows breaks wg-quick's parser
#   - DNS dropped: wg-quick hands it to resolvconf, which the image lacks
#   - AllowedIPs narrowed to the API server, so the ECR login and the helm and
#     kubectl downloads keep leaving through the agent's own network
#   - PersistentKeepalive added when absent, for a NAT in front of the agent
( umask 077
  tr -d '\r' < "$WG_CONF" \
    | sed -E '/^[[:space:]]*DNS[[:space:]]*=/d' \
    | sed -E "s|^[[:space:]]*AllowedIPs[[:space:]]*=.*|AllowedIPs = ${WG_ALLOWED_IPS}|" \
    | awk -v ka="$(grep -Eq '^[[:space:]]*PersistentKeepalive' "$WG_CONF" && echo yes)" '
        { print }
        /^\[Peer\]/ && ka != "yes" { print "PersistentKeepalive = 25" }' \
    > "$tmp/work/wg0.conf" )

cat > "$tmp/work/run.sh" <<'EOF'
set -eu
apk add --no-cache -q bash curl coreutils tar iproute2 wireguard-tools wireguard-go >/dev/null
install -d -m 700 /etc/wireguard
install -m 600 /work/wg0.conf /etc/wireguard/wg0.conf
rm -f /work/wg0.conf

# wg-quick uses the kernel's WireGuard when the host has it and falls back to
# wireguard-go (needs /dev/net/tun) when it does not.
if ! wg-quick up wg0; then
  echo "ERROR: the WireGuard tunnel did not come up inside the deploy container" >&2
  exit 3
fi

host="${API_CHECK%:*}"; port="${API_CHECK##*:}"
n=0
until timeout 5 bash -c "exec 3<>/dev/tcp/${host}/${port}" 2>/dev/null; do
  n=$((n + 1))
  if [ "$n" -ge 10 ]; then
    wg show wg0 || true
    echo "ERROR: ${API_CHECK} did not answer through the tunnel. No 'latest handshake'" >&2
    echo "  above means the VPN server never accepted this peer: check its Endpoint is" >&2
    echo "  reachable over UDP from the agent and the server holds this peer's key." >&2
    exit 3
  fi
  sleep 3
done
echo "tunnel up: ${API_CHECK} answers"

export KUBECONFIG=/work/kubeconfig
cd /work
exec bash ./ci/deploy-dev.sh "$1"
EOF

note "Deploying ${TAG} to dev through the openg2p-Gen2 VPN (container ${DEPLOY_IMAGE})"

tun=()
[ ! -c /dev/net/tun ] || tun=(--device /dev/net/tun)

# rancher.openg2p.test is named in kubeconfigs downloaded from Rancher and does
# not resolve off the VPN; pin it to the API server's address.
cid="$(docker create \
  --cap-add NET_ADMIN ${tun[@]+"${tun[@]}"} \
  --add-host rancher.openg2p.test:10.15.0.1 \
  -e API_CHECK="$API_CHECK" \
  -e AWS_ACCOUNT_ID -e ECR_REGISTRY -e AWS_REGION -e ECR_BASE \
  -e NAMESPACE -e RELEASE_NAME -e CHART_DIR \
  -e HELM_VERSION -e KUBECTL_VERSION \
  "$DEPLOY_IMAGE" sh /work/run.sh "$TAG")"
docker cp "$tmp/work/." "$cid:/work"

set +e
docker start -a "$cid"
rc=$?
set -e
exit "$rc"
