#!/usr/bin/env bash

# ==============================================================================
# Script: init_db_schema.sh
# Description: Creates the database and generates all table schemas (DDL) 
#              without inserting sample data SQL files.
# ==============================================================================

set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# 1. Load environment variables
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

PGHOST="${POSTGRES_HOST:-localhost}"
PGPORT="${POSTGRES_PORT:-5446}"
PGUSER="${POSTGRES_SUPERUSER:-${POSTGRES_USER:-postgres}}"
export PGPASSWORD="${POSTGRES_PASSWORD:-postgres}"

DB_NAME="${REGISTRY_DB:-cropsown}"
PG_CONTAINER="${POSTGRES_CONTAINER:-cropsown-registry-postgres}"
API_CONTAINER="${STAFF_API_CONTAINER:-cropsown-registry-staff-api}"

echo "======================================================================"
echo "🛠️ OpenG2P Crop Sown Registry - Schema Creation Only (No Sample Data)"
echo "======================================================================"
echo "  Target Host:       ${PGHOST}"
echo "  Target Port:       ${PGPORT}"
echo "  Database User:     ${PGUSER}"
echo "  Target Database:   ${DB_NAME}"
echo "  API Container:     ${API_CONTAINER}"
echo "======================================================================"

# 2. Helper function to run psql
run_psql() {
    local db="$1"
    local query_or_file="$2"
    local is_file="${3:-false}"
    local stop_on_error="${4:-1}"

    if command -v psql &> /dev/null && psql -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -d postgres -c "SELECT 1;" &> /dev/null; then
        if [ "${is_file}" = "true" ]; then
            psql -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -d "${db}" -v ON_ERROR_STOP="${stop_on_error}" -q -f "${query_or_file}"
        else
            psql -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -d "${db}" -v ON_ERROR_STOP="${stop_on_error}" -c "${query_or_file}"
        fi
    elif docker ps --format '{{.Names}}' | grep -q "^${PG_CONTAINER}$"; then
        if [ "${is_file}" = "true" ]; then
            docker exec -i "${PG_CONTAINER}" psql -U "${PGUSER}" -d "${db}" -v ON_ERROR_STOP="${stop_on_error}" -q < "${query_or_file}"
        else
            docker exec -i "${PG_CONTAINER}" psql -U "${PGUSER}" -d "${db}" -v ON_ERROR_STOP="${stop_on_error}" -c "${query_or_file}"
        fi
    else
        echo "❌ Error: Could not connect via local 'psql' or Docker container '${PG_CONTAINER}'."
        exit 1
    fi
}

# 3. Check & Create Database
echo "🔍 Checking database status for '${DB_NAME}'..."
DB_EXISTS=$(run_psql "postgres" "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}';" false 1 | grep -c "1" || true)

if [ "${DB_EXISTS}" -eq "0" ]; then
    echo "✨ Database '${DB_NAME}' does not exist. Creating database..."
    run_psql "postgres" "CREATE DATABASE \"${DB_NAME}\";" false 1
    echo "✅ Database '${DB_NAME}' created successfully."
else
    echo "ℹ️ Database '${DB_NAME}' already exists."
fi

# 4. Create all table schemas (DDL) using ORM Initializer Migration
echo "🏗️ Generating table schemas for all core and extension tables..."

if docker ps --format '{{.Names}}' | grep -q "^${API_CONTAINER}$"; then
    docker exec -i "${API_CONTAINER}" python3 -m openg2p_fastapi_common.app migrate
    echo "✅ Table schemas created successfully via container migration."
else
    echo "❌ Error: Container '${API_CONTAINER}' is not running. Please start the stack via 'docker compose up -d' to generate table schemas."
    exit 1
fi

# 5. Apply system UI metadata and AWE policy configurations (No sample data)
META_DATA_DIR="${PROJECT_ROOT}/cropsown-extension/src/openg2p_registry_cropsown_extension/meta_data"

if [ -d "${META_DATA_DIR}" ]; then
    echo "📋 Applying UI layout definitions and metadata configurations..."
    
    find "${META_DATA_DIR}" -name "*.sql" | sort | while read -r sql_file; do
        filename=$(basename "${sql_file}")
        echo "  ➡️ Applying metadata: ${filename}..."
        run_psql "${DB_NAME}" "${sql_file}" true 0
    done
fi

echo "======================================================================"
echo "🎉 SUCCESS: Database '${DB_NAME}' and all table schemas created!"
echo "🚫 Skipped inserting sample data SQL files (10_crop_sowns.sql, 20_crop_lines.sql, 40_bulk_records.sql, etc.)."
echo "======================================================================"
