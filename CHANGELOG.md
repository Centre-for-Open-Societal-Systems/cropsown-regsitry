# Changelog

Notable changes to the Crop Sown Registry, newest first, in the format of [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versions are the repository version in `init.yaml` (see [release](docs/release.md)). Before this file, the history is
the git log and the pull requests.

## [Unreleased]

### Added

- `ci/validate.sh` runs every test in `test/`, and GitHub runs the staff UI widget tests on Node 22 (#318).
- Guard tests for contracts between files that nothing checks at runtime (#319):
  - base model columns match the platform pin, and the models match the register definitions;
  - every seed INSERT has ON CONFLICT;
  - consent scope ids are releasable by the DCI search response;
  - `search_text` is built from real columns;
  - AWE policy keys join across the registry and AWE seeds.
- Coverage reports of `cropsown-extension/src`, with no minimum yet, and a lint over every Python file with the
  rules in `ruff.toml`. `ci/README.md`: where each check runs (#320).
- `docs/deployment.md`, `docs/release.md` and this changelog.

### Changed

- Land ID and Land ID (cluster) are plain text with no enforced format; only a value of spaces alone is refused
  (#317).
- Sowing date and Date of observation may be future dates (#317).
- ODK forms 2026.11.20.2: land area row checks, Crop Year required in all four forms, and text answers that keep
  a new line, quote or backslash from breaking ingestion (#317).

### Known issues

- 13 search fields of the Harvest, Infestation, Planning, Production and Sowing registers are not columns, so they
  never reach `search_text` and a record cannot be found by them. They are listed in `test/test_search_text.py`.
- `scripts/bump-rp-version.sh` moves only the Dockerfiles and the `Jenkinsfile`. The platform version in
  `ci/pipelines/dev.groovy`, the test image and `ci/refactor/` is moved by hand ([release](docs/release.md)).
