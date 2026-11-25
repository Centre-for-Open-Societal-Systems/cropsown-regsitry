# Release

How a Crop Sown Registry version is numbered, built and promoted. Where each version goes is in
[deployment](deployment.md).

## Versions

| What | Where it is set | Example |
| --- | --- | --- |
| Repository version | `version` in [`init.yaml`](../init.yaml) | `1.0.0` |
| Build version: image tag and chart version | `<version>-<branch>.<BUILD_NUMBER>` ([`ci/image_names.py`](../ci/image_names.py)) | `1.0.0-develop.310` |
| Staging version | the rc of a develop build, added by the staging promotion | |
| OpenG2P platform (`rpVersion`) | `appVersion` and the `openg2p-registry` dependency in `helm/openg2p-cropsown-registry/Chart.yaml`, and `ARG RP_VERSION` in the platform Dockerfiles | `1.2.2-rc.614` |
| Crop sown extension package | `__version__` in `cropsown-extension/src/openg2p_registry_cropsown_extension/__init__.py` | `1.0.0` |

The six platform images carry `-<rpVersion>` in their repository name, so a platform bump starts new ECR repositories:
`eoan/cropsown-registry/staff-api-1.2.2-rc.614:1.0.0-develop.310`. The connector and dashboard images do not. ECR tags
are immutable. The naming follows oan-helm `docs/release/naming-standard.md`, section 6.

`helm/openg2p-cropsown-registry/Chart.yaml` keeps `version: 0.0.0`. The build writes the real version into the archive
it packages.

## Release flow

1. **Merge to `develop`.** The build validates, publishes the images and deploys them to New Dev. It then publishes
   the packaged chart to oan-helm `repository/develop/`, where oan-helm's workflow updates the index, changelog and
   rollback history.
2. **Merge `develop` into `staging`.** The staging build promotes the chart develop built from the same tree. It adds
   the rc tag to the same image digests, deploys to staging and publishes the rc chart to `repository/staging/`.
   Nothing is rebuilt.
3. **Production.** Not defined yet ([deployment](deployment.md#production)).

Before step 2, add the changes to [CHANGELOG.md](../CHANGELOG.md) under a heading for the version being promoted.

## Changing the platform version

The platform version is owned centrally: update the chart and the pinned profile ([`ci/deploy/oan-chart.json`](../ci/deploy/oan-chart.json))
first. Then run `scripts/bump-rp-version.sh`. It writes that version into every `ARG RP_VERSION`, and into an
`RP_VERSION` override in the `Jenkinsfile` if there is one, and refuses any other version. These tests fail when the
copies disagree:

- `test/test_rp_pin_lockstep.py`: the Dockerfiles and Jenkins against `oan-chart.json`;
- `test/test_image_names.py`: the Dockerfiles against the chart's `appVersion`;
- `test/test_metadata_consistency.py`, which checks the platform's base model columns against the pin.

The script does not move the other copies of the version, so move them by hand with the pin:

- the test image, `ci/refactor/profile-tests.Dockerfile`;
- the platform images `ci/pipelines/dev.groovy` runs directly (the port check and the chart prefetch);
- the refactor checks and probes in `ci/refactor/` (`check_port.py`, `metadata_probe.py`,
  `notification_pipeline_probe.py`, `rehearse_metadata.py`, `verify_onboarding.py`).

`grep -rn 'rc\.[0-9]' Jenkinsfile ci/pipelines ci/refactor docker` lists them. No test checks these copies yet.

## Rollback

What the pipelines do today:

- New Dev: the deploy is not `--atomic`, so a failed upgrade leaves the release `failed` until the next good build.
- Staging: a failed upgrade is rolled back to the last deployed Helm revision.
- A Helm rollback restores the chart and values, not data that hooks or users wrote.
- Data is restored only from a backup. See [rollback and recovery](deployment.md#rollback-and-recovery).

The rollback policy is still to be agreed: when a release is rolled back instead of fixed forward, who decides, and
how a database change is undone.
