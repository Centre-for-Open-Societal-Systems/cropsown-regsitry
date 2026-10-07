#!/usr/bin/env bash

# ==============================================================================
# Script: init_and_seed_db.sh
# Description: Creates the database (if missing) and populates tables using 
#              database parameters from docker-compose / .env and SQL seeds from 
#              docker/db-seed/sample-data.
# ==============================================================================

set -eo pipefail

# 1. Determine script & project root directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# 2. Load environment variables from local/.env or .env if present
if [ -f "${PROJECT_ROOT}/local/.env" ]; then
    echo "📄 Loading environment configuration from local/.env..."
    set -o allexport
    source "${PROJECT_ROOT}/local/.env"
    set +o allexport
elif [ -f "${PROJECT_ROOT}/.env" ]; then
    echo "📄 Loading environment configuration from .env..."
    set -o allexport
    source "${PROJECT_ROOT}/.env"
    set +o allexport
fi

# 3. Resolve database connection variables with fallback defaults
PGHOST="${POSTGRES_HOST:-localhost}"
PGPORT="${POSTGRES_PORT:-5446}"
PGUSER="${POSTGRES_SUPERUSER:-${POSTGRES_USER:-postgres}}"
export PGPASSWORD="${POSTGRES_PASSWORD:-postgres}"

# DB Name extracted from env (REGISTRY_DB) or fallback 'cropsown'
DB_NAME="${REGISTRY_DB:-cropsown}"
CONTAINER_NAME="${POSTGRES_CONTAINER:-cropsown-registry-postgres}"

SAMPLE_DATA_DIR="${PROJECT_ROOT}/docker/db-seed/sample-data"

echo "======================================================================"
echo "🚀 OpenG2P Crop Sown Registry - Database Creation & Seeding Tool"
echo "======================================================================"
echo "  Target Host:       ${PGHOST}"
echo "  Target Port:       ${PGPORT}"
echo "  Database User:     ${PGUSER}"
echo "  Target Database:   ${DB_NAME}"
echo "  Sample Data Dir:   ${SAMPLE_DATA_DIR}"
echo "======================================================================"

# 4. Helper function to run psql commands (via docker exec or native psql)
run_psql() {
    local db="$1"
    local query_or_file="$2"
    local is_file="${3:-false}"

    if command -v psql &> /dev/null && psql -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -d postgres -c "SELECT 1;" &> /dev/null; then
        if [ "${is_file}" = "true" ]; then
            psql -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -d "${db}" -v ON_ERROR_STOP=1 -q -f "${query_or_file}"
        else
            psql -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -d "${db}" -v ON_ERROR_STOP=1 -c "${query_or_file}"
        fi
    elif docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        if [ "${is_file}" = "true" ]; then
            docker exec -i "${CONTAINER_NAME}" psql -U "${PGUSER}" -d "${db}" -v ON_ERROR_STOP=1 -q < "${query_or_file}"
        else
            docker exec -i "${CONTAINER_NAME}" psql -U "${PGUSER}" -d "${db}" -v ON_ERROR_STOP=1 -c "${query_or_file}"
        fi
    else
        echo "❌ Error: Could not connect via local 'psql' or Docker container '${CONTAINER_NAME}'."
        exit 1
    fi
}

# 5. Check if Target Database exists, create if missing
echo "🔍 Checking database status for '${DB_NAME}'..."
DB_EXISTS=$(run_psql "postgres" "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}';" false | grep -c "1" || true)

if [ "${DB_EXISTS}" -eq "0" ]; then
    echo "✨ Database '${DB_NAME}' does not exist. Creating database..."
    run_psql "postgres" "CREATE DATABASE \"${DB_NAME}\";" false
    echo "✅ Database '${DB_NAME}' created successfully."
else
    echo "ℹ️ Database '${DB_NAME}' already exists."
fi

# 6. Apply sample data SQL seed files in order
if [ ! -d "${SAMPLE_DATA_DIR}" ]; then
    echo "❌ Error: Sample data directory '${SAMPLE_DATA_DIR}' not found!"
    exit 1
fi

echo "📦 Seeding tables from '${SAMPLE_DATA_DIR}' into '${DB_NAME}'..."

shopt -s nullglob
SQL_FILES=("${SAMPLE_DATA_DIR}"/*.sql)
shopt -u nullglob

if [ ${#SQL_FILES[@]} -eq 0 ]; then
    echo "⚠️ No .sql files found in '${SAMPLE_DATA_DIR}'."
    exit 0
fi

for sql_file in "${SQL_FILES[@]}"; do
    filename=$(basename "${sql_file}")
    echo "  ➡️ Applying ${filename}..."
    if ! run_psql "${DB_NAME}" "${sql_file}" true; then
        echo "⚠️ Note: If table schema columns are missing, ensure 'staff-portal-api' has run migrations first."
        exit 1
    fi
done

echo "======================================================================"
echo "🎉 DB creation & seeding completed successfully!"
echo "======================================================================"
