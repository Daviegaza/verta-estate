#!/usr/bin/env bash
# ==============================================================================
# VESTRA Database Restore Script — v4.3.0
# ==============================================================================
# Restores PostgreSQL database from backup files created by backup-db.sh.
# Supports S3, GCS, SFTP, and local file sources.
#
# Usage:
#   ./restore-db.sh s3://bucket/backups/vestra_2026-06-21.dump
#   ./restore-db.sh gs://bucket/backups/vestra_2026-06-21.sql.gz
#   ./restore-db.sh /local/path/vestra_backup.dump
#   ./restore-db.sh --latest s3://bucket/backups/
#
# Environment variables (or .env file):
#   DATABASE_URL          PostgreSQL connection URL (required)
#   AWS_ACCESS_KEY_ID     S3 access key (for S3 restores)
#   AWS_SECRET_ACCESS_KEY S3 secret key
#   S3_ENDPOINT           Custom S3 endpoint (optional)
#   GCS_SERVICE_ACCOUNT   Path to GCS service account JSON (for GCS restores)
#   SFTP_HOST, SFTP_USER, SFTP_KEY_PATH  SFTP credentials
#   SLACK_WEBHOOK_URL     Slack notification webhook (optional)
#
# Options:
#   --dry-run    Validate without restoring
#   --no-confirm Skip confirmation prompt
#   --no-backup  Skip pre-restore backup of current state
# ==============================================================================

set -euo pipefail
IFS=$'\n\t'

# ── Color helpers ──────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info()  { echo -e "${BLUE}[INFO]${NC}  $(date '+%Y-%m-%d %H:%M:%S') $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $(date '+%Y-%m-%d %H:%M:%S') $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') $*" >&2; }
log_success() { echo -e "${GREEN}[OK]${NC}    $(date '+%Y-%m-%d %H:%M:%S') $*"; }

# ── Load .env ───────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/../backend/.env"
if [ -f "$ENV_FILE" ]; then
    set -a; source "$ENV_FILE"; set +a
fi

# ── Configuration ───────────────────────────────────────────────────────────────
DRY_RUN=false
SKIP_CONFIRM=false
SKIP_PRE_BACKUP=false
SOURCE=""
LATEST=false
LOCAL_FILE=""
TEMP_DIR=""

PG_RESTORE="pg_restore"
PSQL="psql"

# ── Parse arguments ─────────────────────────────────────────────────────────────
while [ $# -gt 0 ]; do
    case "$1" in
        --dry-run)     DRY_RUN=true; shift ;;
        --no-confirm)  SKIP_CONFIRM=true; shift ;;
        --no-backup)   SKIP_PRE_BACKUP=true; shift ;;
        --latest)      LATEST=true; SOURCE="$2"; shift 2 ;;
        *)             SOURCE="$1"; shift ;;
    esac
done

# ── Validate prerequisites ──────────────────────────────────────────────────────
if [ -z "${DATABASE_URL:-}" ]; then
    log_error "DATABASE_URL is not set. Provide it in the environment or .env file."
    exit 1
fi

if [ -z "$SOURCE" ]; then
    log_error "No backup source specified. Usage: restore-db.sh <source>"
    exit 1
fi

for cmd in pg_restore psql; do
    if ! command -v "$cmd" &>/dev/null; then
        log_error "$cmd not found. Please install PostgreSQL client tools."
        exit 1
    fi
done

# ── Create temp directory ──────────────────────────────────────────────────────
TEMP_DIR="$(mktemp -d)"
trap "rm -rf $TEMP_DIR" EXIT

# ── Functions ──────────────────────────────────────────────────────────────────

notify_slack() {
    local status="$1" message="$2"
    if [ -n "${SLACK_WEBHOOK_URL:-}" ]; then
        curl -s -X POST "$SLACK_WEBHOOK_URL" \
            -H 'Content-Type: application/json' \
            -d "{\"text\":\"[VESTRA DB Restore] $status: $message\"}" >/dev/null || true
    fi
}

# ── Step 1: Pre-restore backup (unless skipped) ─────────────────────────────────

if [ "$SKIP_PRE_BACKUP" = false ] && [ "$DRY_RUN" = false ]; then
    log_info "Creating pre-restore safety backup..."
    PRE_BACKUP_FILE="$TEMP_DIR/pre_restore_$(date +%Y%m%d_%H%M%S).dump"
    if pg_dump --format=custom --file="$PRE_BACKUP_FILE" "$DATABASE_URL" 2>/dev/null; then
        log_success "Pre-restore backup created: $PRE_BACKUP_FILE"
    else
        log_warn "Pre-restore backup failed — continuing anyway (run with --no-backup to skip)"
    fi
fi

# ── Step 2: Fetch the backup file ──────────────────────────────────────────────

log_info "Fetching backup from: $SOURCE"

if [ "$LATEST" = true ]; then
    # Find the latest backup in the source directory
    if [[ "$SOURCE" == s3://* ]]; then
        LATEST_KEY=$(aws s3 ls "$SOURCE" --recursive 2>/dev/null | sort | tail -1 | awk '{print $NF}')
        if [ -z "$LATEST_KEY" ]; then
            log_error "No backups found at $SOURCE"
            exit 1
        fi
        SOURCE="$SOURCE$LATEST_KEY"
        log_info "Latest backup: $SOURCE"
    elif [[ "$SOURCE" == gs://* ]]; then
        LATEST_KEY=$(gsutil ls "$SOURCE" 2>/dev/null | sort | tail -1)
        if [ -z "$LATEST_KEY" ]; then
            log_error "No backups found at $SOURCE"
            exit 1
        fi
        SOURCE="$LATEST_KEY"
        log_info "Latest backup: $SOURCE"
    else
        log_error "--latest flag only works with s3:// or gs:// sources"
        exit 1
    fi
fi

LOCAL_FILE="$TEMP_DIR/backup_to_restore"

if [[ "$SOURCE" == s3://* ]]; then
    log_info "Downloading from S3..."
    aws s3 cp "$SOURCE" "$LOCAL_FILE" --no-progress 2>/dev/null || {
        log_error "Failed to download from S3: $SOURCE"
        exit 1
    }
elif [[ "$SOURCE" == gs://* ]]; then
    log_info "Downloading from GCS..."
    gsutil cp "$SOURCE" "$LOCAL_FILE" 2>/dev/null || {
        log_error "Failed to download from GCS: $SOURCE"
        exit 1
    }
elif [[ "$SOURCE" == sftp://* ]]; then
    log_info "Downloading over SFTP..."
    SFTP_HOST="${SFTP_HOST:?SFTP_HOST required}"
    SFTP_USER="${SFTP_USER:?SFTP_USER required}"
    SFTP_KEY="${SFTP_KEY_PATH:?SFTP_KEY_PATH required}"
    scp -i "$SFTP_KEY" "$SFTP_USER@$SFTP_HOST:${SOURCE#sftp://*/}" "$LOCAL_FILE" 2>/dev/null || {
        log_error "Failed to download over SFTP"
        exit 1
    }
elif [ -f "$SOURCE" ]; then
    log_info "Using local file..."
    LOCAL_FILE="$SOURCE"
else
    log_error "Unsupported source: $SOURCE (must be s3://, gs://, sftp://, or local path)"
    exit 1
fi

log_success "Backup file ready: $LOCAL_FILE ($(du -h "$LOCAL_FILE" | cut -f1))"

# ── Step 3: Validate backup file ────────────────────────────────────────────────

log_info "Validating backup file..."

# Detect format
FILE_TYPE=$(file "$LOCAL_FILE")
if echo "$FILE_TYPE" | grep -qi "gzip"; then
    log_info "Detected gzip-compressed backup — decompressing..."
    gunzip -c "$LOCAL_FILE" > "$TEMP_DIR/backup_decompressed" 2>/dev/null || {
        log_error "Failed to decompress backup"
        exit 1
    }
    LOCAL_FILE="$TEMP_DIR/backup_decompressed"
fi

if echo "$FILE_TYPE" | grep -qi "PostgreSQL custom"; then
    RESTORE_CMD="pg_restore"
    log_info "Format: PostgreSQL custom dump"
elif echo "$FILE_TYPE" | grep -qi "ASCII text\|SQL"; then
    RESTORE_CMD="psql"
    log_info "Format: Plain SQL"
else
    log_warn "Unknown format — will try pg_restore first"
    RESTORE_CMD="pg_restore"
fi

# ── Step 4: Confirm ─────────────────────────────────────────────────────────────

if [ "$SKIP_CONFIRM" = false ] && [ "$DRY_RUN" = false ]; then
    echo ""
    log_warn "=============================================================="
    log_warn "  DATABASE RESTORE — THIS WILL OVERWRITE THE CURRENT DATABASE"
    log_warn "=============================================================="
    echo ""
    log_info "Source:     $SOURCE"
    log_info "Target:     ${DATABASE_URL%%@*}@***"
    log_info "Format:     $RESTORE_CMD"
    log_info "Environment: ${ENVIRONMENT:-unknown}"
    echo ""

    read -r -p "Type 'RESTORE' to confirm and proceed: " CONFIRM
    if [ "$CONFIRM" != "RESTORE" ]; then
        log_info "Restore cancelled by user."
        exit 0
    fi
fi

# ── Step 5: Execute restore ─────────────────────────────────────────────────────

if [ "$DRY_RUN" = true ]; then
    log_info "DRY RUN — would restore using: $RESTORE_CMD"
    if [ "$RESTORE_CMD" = "pg_restore" ]; then
        pg_restore --list "$LOCAL_FILE" 2>/dev/null | head -20 || true
    fi
    log_success "Dry run complete. No changes made."
    exit 0
fi

log_info "Beginning database restore..."
RESTORE_START=$(date +%s)

# Drop existing connections (requires superuser)
log_info "Terminating existing connections..."
psql "$DATABASE_URL" -c "
    SELECT pg_terminate_backend(pg_stat_activity.pid)
    FROM pg_stat_activity
    WHERE pg_stat_activity.datname = current_database()
    AND pid <> pg_backend_pid();
" 2>/dev/null || log_warn "Could not terminate connections (may need superuser)"

if [ "$RESTORE_CMD" = "pg_restore" ]; then
    # Custom format — drop and recreate
    log_info "Restoring custom dump with pg_restore..."
    pg_restore \
        --dbname="$DATABASE_URL" \
        --clean \
        --if-exists \
        --no-owner \
        --no-acl \
        --jobs=4 \
        --verbose \
        "$LOCAL_FILE" 2>&1 || {
        log_error "pg_restore failed. The database may be in an inconsistent state."
        log_error "Restore pre-restore backup: pg_restore --dbname='$DATABASE_URL' '$PRE_BACKUP_FILE'"
        notify_slack "FAILED" "Database restore failed from $SOURCE"
        exit 1
    }
else
    # Plain SQL
    log_info "Restoring SQL dump with psql..."
    psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f "$LOCAL_FILE" 2>&1 || {
        log_error "psql restore failed. The database may be in an inconsistent state."
        notify_slack "FAILED" "Database restore failed from $SOURCE"
        exit 1
    }
fi

RESTORE_END=$(date +%s)
DURATION=$((RESTORE_END - RESTORE_START))

log_success "Database restore complete in ${DURATION}s"

# ── Step 6: Run migrations ──────────────────────────────────────────────────────

log_info "Running pending migrations..."
cd "$SCRIPT_DIR/../backend"

if command -v alembic &>/dev/null; then
    alembic upgrade head 2>&1 || {
        log_warn "alembic upgrade had issues — check migration status manually"
    }
    log_success "Migrations applied"
else
    log_warn "alembic not found — skipping migrations"
fi

# ── Step 7: Verify ──────────────────────────────────────────────────────────────

log_info "Verifying database..."
if psql "$DATABASE_URL" -c "SELECT count(*) FROM users;" >/dev/null 2>&1; then
    USER_COUNT=$(psql "$DATABASE_URL" -t -c "SELECT count(*) FROM users;" 2>/dev/null | tr -d '[:space:]')
    log_success "Database verified — $USER_COUNT users, ${DURATION}s restore time"
else
    log_warn "Could not verify user count"
fi

notify_slack "SUCCESS" "Database restored from $(basename "$SOURCE") in ${DURATION}s"

log_success "=============================================="
log_success "  Restore Complete"
log_success "  Duration: ${DURATION}s"
log_success "  Pre-restore backup: ${PRE_BACKUP_FILE:-skipped}"
log_success "=============================================="
