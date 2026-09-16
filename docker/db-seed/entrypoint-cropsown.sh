#!/bin/sh
# db-seed for the crop sown registry: the platform's seeding, then this
# variant's Ethiopia geo hierarchy.
#
# The base image's /seed/entrypoint.sh loads the registry metadata, and its
# load_geo_data.py loads the generic sample hierarchy that ships in
# /openg2p-data. This registry is Ethiopia-only and needs the real
# region/zone/woreda/kebele hierarchy instead, which lives in this repo as
# geo-seed/ethiopia_geo_seed_fixed.sql (21,057 INSERTs, every one with ON
# CONFLICT, wrapped in one transaction, so re-running it changes nothing).
#
# Until now that file reached only the docker-compose stack, applied by hand
# (docker/local-dev/geo-seed/import_ethiopia_geo.py documents how it was
# generated); nothing copied it into this image, so a deployed cluster kept the
# sample hierarchy. It is now part of the image and applied on every deploy.
#
# It goes into the MASTER DATA database (g2p_geo_levels, g2p_geo_level_values),
# which is where the geo-hierarchy widget reads from, using the MD_PG* variables
# the chart already passes to this Job.
#
# Env:
#   LOAD_ETHIOPIA_GEO  false skips this step, strict makes its failure fatal
#                      (default: run it, but never fail the Job over it)
#   GEO_SEED_FILE      override the SQL applied
#   MD_PGHOST/MD_PGPORT/MD_PGDATABASE/MD_PGUSER/MD_PGPASSWORD  master data DB
set -eu

GEO_SEED_FILE="${GEO_SEED_FILE:-/seed/geo-seed/ethiopia_geo_seed_fixed.sql}"

# Platform seeding first: its failure is this Job's failure, as before.
/seed/entrypoint.sh "$@"

if [ "${LOAD_ETHIOPIA_GEO:-true}" = "false" ]; then
  echo "[geo-seed] LOAD_ETHIOPIA_GEO=false - skipping the Ethiopia hierarchy"
  exit 0
fi

# This step is best-effort on purpose. db-seed is a post-upgrade HOOK: if this
# script exits non-zero the whole helm release fails, so the images that already
# pulled and rolled out do not go live either. A geo hierarchy that did not load
# is a data problem to read in this log and fix, not a reason to fail a deploy.
# LOAD_ETHIOPIA_GEO=strict makes it fatal again, for a run where you want that.
geo_problem() {
  echo "[geo-seed] WARNING: $1" >&2
  if [ "${LOAD_ETHIOPIA_GEO:-true}" = "strict" ]; then
    echo "[geo-seed] LOAD_ETHIOPIA_GEO=strict: failing the Job" >&2
    exit 1
  fi
  echo "[geo-seed] the platform seeding above succeeded; leaving the hierarchy as it is" >&2
  exit 0
}

[ -f "$GEO_SEED_FILE" ] || geo_problem "${GEO_SEED_FILE} is not in this image"
command -v psql >/dev/null 2>&1 || geo_problem "no psql in this image"
{ [ -n "${MD_PGDATABASE:-}" ] && [ -n "${MD_PGHOST:-}" ]; } \
  || geo_problem "MD_PGHOST/MD_PGDATABASE are not set; cannot reach the master data DB"

echo "[geo-seed] Applying the Ethiopia hierarchy to ${MD_PGDATABASE}@${MD_PGHOST}:${MD_PGPORT:-5432} ..."
PGPASSWORD="${MD_PGPASSWORD:-}" psql \
  --host "$MD_PGHOST" \
  --port "${MD_PGPORT:-5432}" \
  --username "${MD_PGUSER:-postgres}" \
  --dbname "$MD_PGDATABASE" \
  --set ON_ERROR_STOP=1 \
  --quiet \
  --file "$GEO_SEED_FILE" \
  || geo_problem "psql could not apply ${GEO_SEED_FILE} (see the error above)"

PGPASSWORD="${MD_PGPASSWORD:-}" psql \
  --host "$MD_PGHOST" --port "${MD_PGPORT:-5432}" \
  --username "${MD_PGUSER:-postgres}" --dbname "$MD_PGDATABASE" \
  --tuples-only --no-align \
  --command "SELECT '[geo-seed] ' || (SELECT count(*) FROM g2p_geo_levels) || ' geo levels, ' || (SELECT count(*) FROM g2p_geo_level_values) || ' values'" \
  || true
