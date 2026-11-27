# Deployment

How the Crop Sown Registry reaches each environment, and where the detailed procedures are. Each change goes through
Jenkins. Never run `helm` or `psql` against an environment by hand.

## What is deployed

| Release | Namespace | What it is |
| --- | --- | --- |
| `cropsown-registry` | `crop` | The chart `helm/openg2p-cropsown-registry`, which wraps the OpenG2P `openg2p-registry` chart at the platform version in its `appVersion`. It runs the six platform images built here: staff-api, staff-ui, partner-api, celery (worker and beat), db-seed and sanity-tests. |
| `cropsown-connector` | `crop` | The connector API and UI images, with the chart in [`ci/deploy/connector-chart`](../ci/deploy/connector-chart). See [chart delivery](../ci/deploy/README.md#cropsown-connector-release-new-dev). |
| dashboard API and UI | `crop` | See [dashboard delivery](dashboard-delivery.md). |

Image names follow [`ci/image_names.py`](../ci/image_names.py). Farmer, Livestock and the shared Commons services
(Keycloak, AWE, ODK Central, MinIO, PostgreSQL) are separate releases with their own delivery.

On install and on every upgrade, the post-install hooks replay the seed (`meta_data/`, `awe_meta_data/`) and run the
sanity smoke tests (`test/sanity`). The seed is written to be replayed: every INSERT has ON CONFLICT.

## Environments

| | Dev (New Dev) | Staging | Production |
| --- | --- | --- | --- |
| Source branch | `develop` | `staging` | not defined yet |
| Pipeline | [`ci/pipelines/dev.groovy`](../ci/pipelines/dev.groovy) | [`ci/pipelines/staging.groovy`](../ci/pipelines/staging.groovy) | not defined yet |
| Namespace, release | `crop`, `cropsown-registry` | `crop`, `cropsown-registry` | not defined yet |
| Registry UI | `https://crop-registry.development.oanstaging.com` | `https://crop-registry.qa.oanstaging.com` | not defined yet |
| Values | oan-helm `environments/dev/values/cropsown.yaml` | oan-helm `environments/staging/values/cropsown.yaml` | not defined yet |
| Chart installed | the chart the build packaged; [`oan-chart.json`](../ci/deploy/oan-chart.json) for a deploy run by hand | the rc of the chart develop built from the same tree | not defined yet |

### Dev

A develop build validates, builds and pushes the images, packages the chart with them
([`ci/deploy/package-chart.sh`](../ci/deploy/package-chart.sh)) and upgrades the release with that chart
([`ci/deploy-crop-dev.sh`](../ci/deploy-crop-dev.sh)). It then deploys the dashboard UI and publishes the chart to
oan-helm `repository/develop/`. The build has no parameters, so there is no separate deploy button.

Other actions run from the operator job ([`Jenkinsfile.operator`](../Jenkinsfile.operator)), on `develop` only. A
person starts it, and the Jenkins `admin` user approves each run:

| `OPERATOR_ACTION` | Effect |
| --- | --- |
| `publish-only` | Builds and publishes the images, and deploys nothing. |
| `fresh-install` | Archives both databases to the New Dev box, uninstalls, drops them and installs again on empty databases ([`ci/deploy/fresh-install-crop-dev.sh`](../ci/deploy/fresh-install-crop-dev.sh)). |
| `connector-plan`, `connector-upgrade` | The connector release only. See [chart delivery](../ci/deploy/README.md#cropsown-connector-release-new-dev). |

### Staging

A merge into `staging` from `develop` builds nothing. It promotes the chart develop built from the same tree: the same
image digests under an rc version, deployed with oan-helm `scripts/ci/deliver_staging.sh` and the staging values. If
develop never built the tree, the build fails, so staging only runs what New Dev ran first. The connector release and
the dashboard UI follow in the same build. `LOAD_SAMPLE_DATA` (off by default) loads the sample records.

### Production

Not defined yet. Open questions, to be decided before this section is written:

- the cluster, namespace and the Commons endpoints production uses;
- the backup method and when it runs;
- the rollback policy (see [release](release.md#rollback)).

## Gates before a deploy

- Every GitHub check of the commit is green ([`ci/deploy/require-green-checks.sh`](../ci/deploy/require-green-checks.sh)).
  This includes `ci/validate.sh`, the native extension tests and the chart lint and render; what each check runs is
  in [ci/README.md](../ci/README.md).
- The rendered release passes the route and deployment guards (`ci/check-new-dev-routes.py`,
  `ci/refactor/deployment_guard.py`) before Helm runs.
- A deploy by hand installs only the chart archive and values pinned in `oan-chart.json`, checked by SHA-256
  (`ci/deploy/oan_chart.py`).

## Rollback and recovery

- Dev `deploy` is not `--atomic`. If the upgrade or a hook fails, the build prints the hook logs, pod logs and release
  history and fails, and the release stays `failed`. The next good build upgrades over it. A release left `pending-*`
  by an interrupted run blocks every upgrade, and the build prints the `helm rollback` that clears it.
- Staging: if the upgrade fails on a release that had a deployed revision, `deliver_staging.sh` rolls Helm back to
  it, and nothing is published. The connector and dashboard upgrades are `--atomic`.
- A Helm rollback restores the chart and values, not data that hooks or users wrote. Data is restored from a backup.
  On dev, that is the archive `fresh-install` writes before it drops the databases. Staging has no backup step in its
  pipeline yet.
