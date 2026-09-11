# Crop Sown Registry

An installable **Crop Sown Registry** built as a thin extension of the OpenG2P
[registry platform](https://github.com/OpenG2P/registry-platform), following the
same inverted build model as the
[Farmer Registry](https://github.com/OpenG2P/farmer-registry): the platform
publishes the runnable base images and the `openg2p-registry` Helm chart; this
repo adds **only** the crop sown domain on top.

The domain is ported from the Odoo module `g2p_crop_registry` (`g2p.crop.registry`
and its planning / cultivation / sowing / harvesting lines) onto the platform's
register model.

## What this repo owns

| Path | Purpose |
|---|---|
| `cropsown-extension/` | The crop sown domain package — models, schemas, services, seed metadata (registers, AWE policy, DCI templates) |
| `dashboard-ui/` | The Crop Sown Registry analytics dashboard (the view behind the portal's Dashboard button) |
| `docker/` | Thin Dockerfiles (`FROM openg2p/openg2p-registry-*` + `pip install cropsown-extension`) selected at runtime by `REGISTRY_EXTENSION_MODULE` (Option C). `docker/staff-ui/` also injects the Dashboard header button; `docker/dashboard-ui/` builds the analytics app. |
| `helm/openg2p-cropsown-registry/` | A thin wrapper chart: pins `openg2p-registry` as a dependency and supplies the crop sown values overlay (no templates) |
| `docker-compose.yml`, `local/` | Docker Compose stack for running the registry on a laptop (`local/` holds its env file and the service configs — Postgres bootstrap, Keycloak realm, IAM login provider and role catalog, id-generator pools) |
| `Jenkinsfile`, `local/jenkins/` | The self-hosted CI pipeline, and a local Jenkins controller that runs it against your own Docker daemon |
| `ci/` | Scripts the pipeline runs that are also run by hand — `ci/deploy-dev.sh` rolls an ECR build into the dev cluster |
| `test/sanity/` | The crop sown **field-specific** sanity tests (Set 2); the harness + generic tests are inherited from the platform sanity image |

## Registers

Modelled on the **CROP SOWN REGISTRY ERD UPDATED** diagram. The crop sown record
is the hub: every crop line links directly to it. Land is not a register of its
own — a crop sown record covers exactly one plot, whose attributes and geometry
sit flat on the record.

```
CropSown                     farmer identifiers, the plot (land_uuid/land_id, ownership, soil fertility,
                             area, geo), status, production year, lifecycle stage
├── Planning                 season, crop, planned area/seed/fertilizer, expected yield
├── Cultivation              land preparation, actual planted date/area/seed/fertilizer
├── Sowing                   sowing status, area sown, sowing date, seed type, machinery
├── Production               growth stage, area under production, actual yield, yield per ha
├── Harvest                  maturity, harvest date, area/quantity harvested, loss, stored, sold
├── Infestation              growth stage, pest/weed/disease, severity, damage, action taken
└── Cluster                  cluster name/status, agro-ecological zone, area, smallholders
```

Neither land nor farmers are registers here. The plot's `land_uuid` (generated)
stays the key every crop line references, but it now names the plot described by
its parent crop sown record rather than a row in a separate land register.

Farmers are **not** a register here: the crop sown record carries their
identifiers (`farmer_uuid`, `farmer_id`, `fayda_fan_id`, `farmer_name`) and
mirrors the Fayda FAN into `link_foundational_id`, because this system is not the
system of record for farmers.

Each register has a `G2PRegister*`, a `G2PRegisterHistory*` and a
`G2PIntakeForm*` model, a matching pydantic schema trio, and a domain service
that validates the domain attributes and builds `search_text` / `record_name`.
Every field, section and tab carries a human-readable label. Catalogs and lookup
tables from the ERD are seeded as attribute lookups — see
[cropsown-extension/README.md](cropsown-extension/README.md) for the full mapping.

## Documentation

- [The Record Photo Chain](docs/record-photo-chain.md) — how record photos
  reach the browser, and the five places that chain breaks. Registry-agnostic;
  useful to any OpenG2P registry wiring up images.

## Run it locally

```bash
docker compose --env-file local/.env up -d --build
```

Then open the **Staff Portal at http://portal.localtest.me:3020** and log in with
`admin` / `admin`. The header's **Dashboard** button opens the Crop Sown Registry
analytics view at http://dashboard.localtest.me:3021 (its Back button returns you
to the portal page you left). The dashboard reads this stack's registry database
directly, so it shows the records the portal holds and nothing else — a registry
with no crop sown records renders empty panels. See `dashboard-ui/README.md`.

The stack runs the whole login chain — Keycloak (realm `staff`), the IAM staff
API and master data — alongside the registry, so this is a real OIDC login and
the registry resolves the user's roles into permissions exactly as a deployment
does. Staff API on http://localhost:8001/docs, Partner API on
http://localhost:8002/docs, Master Data API on http://localhost:8010/docs.
See [local/README.md](local/README.md) for the full service list and how the
pieces fit together.

## Continuous integration

`Jenkinsfile` is the self-hosted pipeline. It builds six images from
`docker/*/Dockerfile` — `staff-api`, `partner-api`, `celery`, `db-seed`,
`sanity-tests` and `dashboard-ui` — publishes them to a private ECR under
branch-derived tags, and deploys both `develop` and `staging` to a `crop`
namespace.

The same namespace name, because the two land on different clusters. Dev goes to
the cluster behind `rancher.openg2p.test` via the `gen2-kubeconfig` credential;
staging is a separate EC2 instance running its own RKE2 cluster, reached with
`staging-rke2-kubeconfig`. The kubeconfig is what separates them, so nothing is
gained by calling one namespace `crop-staging` — and the staging instance does
not have a namespace by that name.

**Merging a pull request into `develop` or `staging` deploys it.** A green build
rolls the images it just pushed into `crop` on that branch's cluster — release
`cropsown-registry` on dev, which is the `crop` deployments view in Rancher, and
`cropsown-stg` on the staging instance. Both deploy stages run on the same agent
as the build. That agent has no `helm` or `kubectl`: `ci/deploy-dev.sh` fetches
pinned, checksum-verified copies into `.tools/` when they are missing, while the
staging stage still needs them on PATH. Neither asks for a
labelled deploy node: the old `vpn-deploy-agent` label is carried by no node, and
an unsatisfiable label does not fail a build — it queues until the 90-minute
timeout, which is how a successful build ended up red.

Nobody has to start that build. `develop` and `staging` poll the repository every
five minutes and build any new commit; a GitHub webhook to
`https://jenkins.oanstaging.com/github-webhook/` starts it at once, with polling
as the fallback. The trigger is registered by a build that reads the
Jenkinsfile, so the first build of each branch after the polling change is
started by hand.

The dev deploy is `ci/deploy-dev.sh`; the Jenkinsfile only hands it the
credentials and the image tag. To deploy by hand, run the same script against
any tag already in ECR, with your kubeconfig pointing at the dev cluster:

```sh
AWS_ACCOUNT_ID=<account> ./ci/deploy-dev.sh develop-42
```

Use a build-numbered tag rather than `develop`: a release already on `develop`
renders the same manifests again, so nothing rolls. The script prints the
kube context before it changes anything; `./ci/deploy-dev.sh` with no tag prints
its usage, and the header lists the defaults it shares with the pipeline.

| Gate | Effect |
|---|---|
| `DEV_DEPLOY=false` | holds a `develop` build at the ECR push; deploy with `ci/deploy-dev.sh` |
| `STAGING_DEPLOY=false` | holds a `staging` build at the ECR push; deploy to the staging instance by hand |

Both are set on the controller. The Staff Portal UI is
deliberately not built here: the chart consumes it as-is from the platform base
image, so a build of it would produce an image nothing deploys.

This is a different road from `.gitlab-ci.yml`, which delegates to
`openg2p/packaging@v1` and publishes to the shared OpenG2P registry and Helm
catalogue. Both build the same Dockerfiles; only the destination differs.

`dashboard-ui` is the one image with no chart value pointing at it — the
analytics dashboard is still Compose-only, so nothing pulls it yet. It is
published so it is ready ahead of the dashboard being deployed. Because Next.js
compiles the portal origin into the client bundle at build time, set `PORTAL_URL`
on the controller to the deployed portal origin; left unset the build warns and
falls back to the local portal, which is wrong for a published image.

### Running the pipeline locally

`local/jenkins/` stands up a controller on <http://localhost:8090> wired to your
own Docker daemon, with the `cropsown-registry` multibranch job already created:

```bash
docker compose -f local/jenkins/docker-compose.yml up -d --build
```

Two environment variables that only this controller sets opt the pipeline into
local behaviour. Absent — which is every run on the real controller — everything
keeps its production form.

| Variable | Local | Effect |
|---|---|---|
| `PUSH_TO_ECR` | `false` | skips the ECR push and both deploy stages |
| `DOCKER_NO_CACHE` | `false` | builds with cache rather than `--no-cache` |

Builds run **committed** code: Jenkins clones `file:///repo`, so uncommitted
edits — including edits to the `Jenkinsfile` itself — are invisible until you
commit. See `local/jenkins/README.md`.

## Deploy

```bash
helm repo add openg2p https://openg2p.github.io/openg2p-helm
helm dependency build ./helm/openg2p-cropsown-registry
helm install cropsown-registry ./helm/openg2p-cropsown-registry \
  --set global.registryHostname=cropsown-registry.example.org
```

Set `registry.sanity.runE2e=true` to run the end-to-end sanity suite after install.

## Version pinning

The `openg2p-registry` base image tag (`RP_VERSION` in each Dockerfile) and the
chart dependency version in `helm/openg2p-cropsown-registry/Chart.yaml` are
**hardcoded and pinned together**. The crop sown images and the wrapper chart are
versioned in lockstep by CI (one version per commit).

To see which version it would pick, run `./scripts/bump-rp-version.sh -n` (dry-run,
writes nothing); `-h` prints help. To apply, run `./scripts/bump-rp-version.sh`
(latest published version) or `./scripts/bump-rp-version.sh <version>` — it updates
the Dockerfiles and the chart dependency together, so they can never drift. A CI
check (`test/test_rp_pin_lockstep.py`) fails the build if they ever do.

See the deployment & extension docs at [docs.openg2p.org](https://docs.openg2p.org).
