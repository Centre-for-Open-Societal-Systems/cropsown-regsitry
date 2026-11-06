# Chart delivery

A develop build packages `helm/openg2p-cropsown-registry` with its own images (stage `Package chart`,
`ci/deploy/package-chart.sh`), installs that archive on New Dev and publishes the same file to
`repository/develop/` of oan-helm (stage `Publish chart`). The version comes from git:
`0.0.0-develop.<commit count>`. Rollback is described in `docs/rollback.md` of oan-helm.

The rest of this page covers the pinned archive. A deploy by hand and staging use it.

## Immutable central chart consumer

Install the deploy-agent dependency with `python3 -m pip install -r ci/deploy/requirements.txt`.
The registry-owned Jenkins job and agent/credential IDs are unchanged.

`oan-chart.json` records the COSS oan-helm commit, chart version, SHA-256, native
platform version, public-values checksum, release and environment. CI downloads
and validates the archive before Helm uses it. There is no local Helm source,
dependency update, moving branch URL or chart-version stamping on that path.

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
| `connector-plan` | Changes nothing. Prints the image digests it would set, the release values, the rendered manifest diff against the running release, a server-side dry run, and whether the optional Keycloak client secret copy exists (informational). Fails when the diff removes a non-image line or the target renders a Job (set `ALLOW_NON_IMAGE_CHANGES=1` only for a deliberate chart change). |
| `connector-upgrade` | Builds no image. Archives the connector database to the New Dev box, then `helm upgrade` of `cropsown-connector` with the same checks printed first, and verifies the pinned image on api, worker, beat and ui. Upgrade only, safe to rerun. |

The service image (api, worker, beat) is `openg2p/cropsown-registry/registry-connector` (built by this
pipeline from `docker/registry-connector`) and the UI image is `openg2p/cropsown-registry/registry-connector-ui`
(from `docker/registry-connector-ui`). Both are taken from the tag `CONNECTOR_IMAGE_TAG` (default
`develop`, or a build tag such as `develop-195`), each resolved to its own digest in ECR and pinned by
digest, so the Helm release owns the images instead of a hand-run `kubectl set image`.

Values are not copied into git. `ci/deploy/upgrade-crop-connector.sh` reads the running
release's values with `helm get values`, writes a small override file (the image on api,
worker, beat and ui, nothing else) and upgrades with
`--reset-values -f <current> -f <override>`; both files are printed. Never `--reuse-values`.

`postgres-init` is not in the override. The release's own value (`postgres-init.enabled: false`) is
kept, so the postgres-init Jobs are not rendered. The release still owns the ServiceAccount
`cropsown-connector-postgres-init`, which an older revision of the chart rendered from
`templates/preserved-init-serviceaccount.yaml`; that template is part of the vendored chart again
(rendered only while `postgres-init.enabled` is false), so the upgrade does not delete the ServiceAccount.

Plan output, before anyone upgrades: release status and history, the image
(`...@sha256:<64 hex>`), the current values, the manifest diff, the live Deployment images and
`Server-side dry run passed.`. The expected diff touches only the four image lines (api, worker, beat, ui)
and removes nothing else; no Service, VirtualService, HPA, probe, ServiceAccount or Job changes.
The plan prints `Image lines changed (expected 4)`, `Removed lines other than image lines (expected 0)`
and `Jobs in target manifest (expected 0)`, and exits non-zero after the dry run when the last two are not 0. The upgrade
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

## Connector definitions are declared in git and applied by Helm

The rows of `connector_definitions` are declared in `definitions.newdev.yaml` (New Dev) and
`definitions.staging.yaml` (staging) under `connectorDefinitions`. The chart's post-install and post-upgrade
hook Job (`connector-chart/templates/definitions-job.yaml`, script `connector-chart/files/apply_definitions.py`)
calls the connector's own admin API on every deploy: it creates a missing definition, PATCHes an existing one
(matched by name, then `previous_names`, then slug) to the declared state, and for WebSub receivers calls
`POST /connectors/{id}/websub/sync-subscriptions`. The API does not subscribe on create and a row inserted with
SQL is never subscribed, so the apply performs the subscription. Checkpoints are not touched.

Secrets are never in values: `webhook_secret_from` / `auth_secret_from` name Kubernetes Secrets read through
`secretKeyRef` (`generate: true` creates the hub secret once if absent; an existing Secret is left alone). A
declared but empty secret never overwrites a stored one. The Keycloak client secret for the admin token is read
at run time from `commons/registry-connector` by the Job's ServiceAccount; apply `ci/k8s/connector-definitions-rbac.yaml`
once as cluster admin. `upgrade-crop-connector.sh` passes `definitions.newdev.yaml`. Tests:
`python -m unittest discover ci/deploy/tests`; `check-connector-chart.sh` renders the hook.

## Staging connector upgrade

`ci/pipelines/staging.groovy` runs `ci/deploy/upgrade-crop-connector-staging.sh` after the registry is promoted and deployed. It takes no
parameters: the connector images are the `registry-connector` and `registry-connector-ui` images of the develop build whose
`staff-api` digest the promoted chart pins (same ECR build tag), pinned by digest. The release is upgraded with the vendored
chart, `cropsown-connector.staging.values.yaml` and `definitions.staging.yaml` using `helm upgrade --atomic --reset-values`.
The hook ServiceAccount needs the Role binding in `ci/k8s/connector-definitions-rbac.yaml` (namespace `crop`) before the first run.
