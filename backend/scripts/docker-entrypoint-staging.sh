#!/bin/bash
# Docker entrypoint for staging database initialization
# This script initializes the staging database with anonymized production data

set -e

# Configuration
: "${PGHOST:=localhost}"
: "${PGPORT:=5432}"
: "${PGUSER:=perito}"
: "${PGDATABASE:=perito_staging}"
: "${ANONYMIZED_DUMP_FILE:=/tmp/perito_prod_anonymized.sql}"
: "${MAX_RETRIES:=30}"
: "${RETRY_DELAY:=1}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Wait for PostgreSQL to be ready
wait_for_postgres() {
    local attempt=0
    log_info "Waiting for PostgreSQL at $PGHOST:$PGPORT..."

    while [ $attempt -lt $MAX_RETRIES ]; do
        if pg_isready -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" 2>/dev/null; then
            log_info "PostgreSQL is ready!"
            return 0
        fi
        attempt=$((attempt + 1))
        log_warn "PostgreSQL not ready yet. Attempt $attempt/$MAX_RETRIES..."
        sleep "$RETRY_DELAY"
    done

    log_error "PostgreSQL failed to start after $MAX_RETRIES attempts"
    return 1
}

# Create database if it doesn't exist
create_database() {
    log_info "Checking database $PGDATABASE..."

    # Check if database exists
    if psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -lqt | cut -d \| -f 1 | grep -qw "$PGDATABASE"; then
        log_warn "Database $PGDATABASE already exists. Dropping it to start fresh..."
        dropdb -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" --if-exists "$PGDATABASE" || true
    fi

    log_info "Creating database $PGDATABASE..."
    createdb -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" "$PGDATABASE"
    log_info "Database created successfully"
}

# Load anonymized data
load_anonymized_data() {
    if [ ! -f "$ANONYMIZED_DUMP_FILE" ]; then
        log_error "Anonymized dump file not found: $ANONYMIZED_DUMP_FILE"
        return 1
    fi

    log_info "Loading anonymized data from $ANONYMIZED_DUMP_FILE..."
    log_info "Database size: $(du -h "$ANONYMIZED_DUMP_FILE" | cut -f1)"

    if psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -f "$ANONYMIZED_DUMP_FILE" > /dev/null 2>&1; then
        log_info "Data loaded successfully"
        return 0
    else
        log_error "Failed to load anonymized data"
        return 1
    fi
}

# Verify data load
verify_data_load() {
    log_info "Verifying data load..."

    # Count tables
    table_count=$(psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -t -c \
        "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';" 2>/dev/null || echo "0")

    log_info "Found $table_count tables in $PGDATABASE"

    if [ "$table_count" -eq 0 ]; then
        log_error "No tables found in database. Data load may have failed."
        return 1
    fi

    return 0
}

# Main execution
main() {
    log_info "=== Staging Database Initialization ==="
    log_info "Host: $PGHOST"
    log_info "Port: $PGPORT"
    log_info "Database: $PGDATABASE"
    log_info "User: $PGUSER"
    log_info ""

    # Wait for PostgreSQL
    if ! wait_for_postgres; then
        log_error "Failed to connect to PostgreSQL"
        exit 1
    fi

    # Create database
    if ! create_database; then
        log_error "Failed to create database"
        exit 1
    fi

    # Load data if dump file exists
    if [ -f "$ANONYMIZED_DUMP_FILE" ]; then
        if ! load_anonymized_data; then
            log_error "Failed to load anonymized data"
            exit 1
        fi

        # Verify
        if ! verify_data_load; then
            log_error "Data verification failed"
            exit 1
        fi
    else
        log_warn "No anonymized dump file found at $ANONYMIZED_DUMP_FILE"
        log_info "Database created but not populated"
    fi

    log_info "=== Staging Database Initialization Complete ==="
    log_info "Staging database is ready for testing"
    log_info ""

    # Execute any additional command passed as arguments
    if [ $# -gt 0 ]; then
        log_info "Executing additional command: $@"
        exec "$@"
    fi
}

# Run main function
main "$@"
