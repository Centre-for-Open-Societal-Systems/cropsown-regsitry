# Immutable central chart consumer

Install the deploy-agent dependency with `python3 -m pip install -r ci/deploy/requirements.txt`.
The registry-owned Jenkins job and agent/credential IDs are unchanged.

`oan-chart.json` records the COSS oan-helm commit, chart version, SHA-256, native
platform version, public-values checksum, release and environment. CI downloads
and validates the archive before Helm uses it. There is no local Helm source,
dependency update, moving branch URL or chart-version stamping.

Read-only verification: `python3 ci/deploy/oan_chart.py fetch registry <directory>`
and `python3 ci/deploy/oan_chart.py values registry <public-values.yaml>`.
Unit checks: `python3 -m unittest discover -s test -p test_oan_chart.py` and
`python3 -m unittest discover -s test -p test_deployment_guard.py`.

All deployment entry points call require-deployable first. The current profile
is deliberately promotionReady=false. Accept domain/source/Kafka/AWE/MDM and
preservation behavior before reviewing an immutable accepted release/profile.
Staging requires its own environment profile and restored-data rehearsal; it
must not use the dev public-values overlay as a fallback.

Live metadata is read only by ci/refactor/new_dev_metadata.py with an explicit
authorized --credentials path. It never captures registry records or submits
approval actions. Credentials/cookies remain in memory, and metadata snapshots
remove credential values. Rehearse/compare scripts run serially using disposable
test databases; they do not bypass the real seed promotion preflight.

Crop's build agent runs `prefetch registry` and `prefetch dashboard` before
stashing `.central-charts/**`. Archives and public values are cached by SHA-256;
the VPN deploy node rechecks the exact package and values without GitHub access.
A corrupt cached archive fails closed and does not trigger a network fallback.
Manual runs can prefetch on a connected machine and carry that directory with
the same immutable profile. Cached archives are not editable Helm sources.

## cropsown-connector release (New Dev)

`ci/deploy/connector-chart` is the `openg2p-connector` 0.1.0 chart that the standalone
`cropsown-connector` release (namespace `crop`) runs. It is the chart this repository once
carried at `openg2p-connector-service/deploy/charts/openg2p-connector`, with two additions
(`extraEnv`/`extraEnvFrom`, and an optional `image.digest` per component), identical to the
copy in livestock-registry `ci/connector/chart`.

Jenkins `NEW_DEV_DELIVERY_ACTION` on develop:

| Action | What it does |
| --- | --- |
| `connector-plan` | Changes nothing. Prints the image digest it would set, the release values, the rendered manifest diff against the running release, a server-side dry run, and whether the optional Keycloak client secret copy exists (informational). |
| `connector-upgrade` | Builds no image. Archives the connector database to the New Dev box, then `helm upgrade` of `cropsown-connector` with the same checks printed first, and verifies the pinned image on api, worker and beat. Upgrade only, safe to rerun. |

The image is `gen2/cropsown-registry/registry-connector` (built by this pipeline from
`docker/registry-connector`), taken from the tag `CONNECTOR_IMAGE_TAG` (default `develop`, or
a build tag such as `develop-186`) and pinned by digest, so the Helm release owns the image
instead of a hand-run `kubectl set image`.

Values are not copied into git. `ci/deploy/upgrade-crop-connector.sh` reads the running
release's values with `helm get values`, writes a small override file (the image on api,
worker and beat, `postgres-init` off) and upgrades with
`--reset-values -f <current> -f <override>`; both files are printed. Never `--reuse-values`.

Plan output, before anyone upgrades: release status and history, the image
(`...@sha256:<64 hex>`), the current values, the manifest diff, the live Deployment images and
`Server-side dry run passed.`. The expected diff touches only the api, worker and beat image
and removes nothing else; no Service, VirtualService, HPA, probe or Job changes. The upgrade
runs with `--atomic`, so a failed rollout rolls the release back to the previous revision.

The connector needs no Keycloak client secret: its admin access only validates incoming
tokens (issuer, JWKS, client id, role), and its WebSub hub calls use the connector
definition's own credentials. The script still reports whether `crop/registry-connector-client`
exists (PRESENT, MISSING or UNKNOWN), but never blocks on it.

### Renewing the WebSub hub subscription lease

The Farmer change notices reach crop through the connector's WebSub subscription on the
Commons hub. The subscription has a lease, and nothing renews it automatically: the connector
has no renewal task (its only periodic task, `connector.poll_all`, polls sources), so the
lease ends unless someone re-syncs the subscription before then.

- **Route:** `POST /connectors/{connector_id}/websub/sync-subscriptions` on the connector API
  (`https://connector-cropsown-registry.development.oanstaging.com`), with the Farmer
  reference connector's id (today `6de1cbac-…`; list ids with `GET /connectors`). The
  connector UI's "Sync subscriptions" action calls the same route.
- **Who:** a staff user whose token carries the `REGISTRY_CONNECTOR_ADMIN` client role of
  the `registry-connector` client (Keycloak user `admin` on New Dev), once the admin-only
  connector access is live. Until then the route answers without a token.
- **When:** before the current lease ends, 2026-11-08 17:02 UTC, and again before each
  following expiry. The sync response and the hub's subscriber list show the new lease end.
- **Check:** approve a Farmer change and see the crop UPDATE change request.

The sync re-subscribes with the connector definition's own hub credentials and webhook
secret; it needs no client secret in the connector pod.
