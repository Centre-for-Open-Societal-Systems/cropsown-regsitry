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
| `connector-plan` | Changes nothing. Prints the image digest it would set, the release values, the rendered manifest diff against the running release, a server-side dry run, and whether the client secret below is present. |
| `connector-upgrade` | Builds no image. Refuses to run without the client secret, archives the connector database to the New Dev box, then `helm upgrade` of `cropsown-connector` with the same checks printed first, and verifies the pinned image on api, worker and beat. Upgrade only, safe to rerun. |

The image is `gen2/cropsown-registry/registry-connector` (built by this pipeline from
`docker/registry-connector`), taken from the tag `CONNECTOR_IMAGE_TAG` (default `develop`, or
a build tag such as `develop-186`) and pinned by digest, so the Helm release owns the image
instead of a hand-run `kubectl set image`.

Values are not copied into git. `ci/deploy/upgrade-crop-connector.sh` reads the running
release's values with `helm get values`, writes a small override file (the image on api,
worker and beat, `postgres-init` off, the client secret reference) and upgrades with
`--reset-values -f <current> -f <override>`; both files are printed. Never `--reuse-values`.

### Keycloak client secret

The connector's admin calls use the staff-realm Keycloak client `registry-connector`.

- The client is created by the Commons `keycloak-init`. The Commons `client-secrets-sync`
  Job then writes its generated secret to a Secret named after the client,
  `registry-connector`, key `client_secret`, in the **commons** namespace (the Job writes to
  its own release namespace).
- A `secretKeyRef` cannot cross namespaces, so the connector reads a copy in `crop`: Secret
  `registry-connector-client`, key `client_secret`, exposed as the environment variable
  `CONNECTOR_ADMIN_AUTH_CLIENT_SECRET` through `extraEnvFrom` with `optional: false`. No value
  is in git or in values.
- The copy is a documented sync step done by whoever owns Commons: after the Commons upgrade
  that adds the client, copy `commons/registry-connector` to `crop/registry-connector-client`
  (same key). `connector-plan` reports whether the copy exists; `connector-upgrade` stops
  before changing anything when it is missing or empty.
- The #162 admin-auth extension only validates tokens: it reads `CONNECTOR_ADMIN_AUTH_ISSUER`,
  `_JWKS_URL`, `_CLIENT_ID`, `_ROLE` and `_UI_CLIENT_ID` (or the baked `admin-auth.json`) and no
  client secret yet. The variable above is where the secret is delivered for the connector's
  client-credentials calls once they exist.
