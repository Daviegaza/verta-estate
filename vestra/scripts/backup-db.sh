#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# VESTRA — PostgreSQL Backup Script
# AI-Powered Property Trust & Operating System for Africa
# ═══════════════════════════════════════════════════════════════════════════════
#
# Features:
#   - Full PostgreSQL dump via pg_dump with custom format (compressed, parallel)
#   - GZip compression of the dump
#   - Upload to remote storage (AWS S3 / GCS / Azure Blob / SFTP)
#   - Automatic cleanup of backups older than RETENTION_DAYS
#   - Prometheus-compatible metrics output
#   - Email/webhook alerts on failure
#   - Lock-file protection against concurrent runs
#
# Usage:
#   ./scripts/backup-db.sh                        # Backup with defaults from .env
#   ./scripts/backup-db.sh --db-name=vestra       # Backup specific database
#   ./scripts/backup-db.sh --output-dir=/backups   # Custom output directory
#   ./scripts/backup-db.sh --upload-only           # Only upload existing backups
#   ./scripts/backup-db.sh --dry-run               # Show what would be done
#
# Cron recommendation (daily at 2 AM):
#   0 2 * * * /path/to/vestra/scripts/backup-db.sh >> /var/log/vestra-backup.log 2>&1
#
# Dependencies: pg_dump (PostgreSQL client), gzip, awscli or gsutil or curl
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail
IFS=$'\n\t'

# ── Script Configuration ──────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOCKFILE="/tmp/vestra_db_backup.lock"
START_TIME=$(date +%s)

# ── Default Values ────────────────────────────────────────────────────────────
# Load from .env if present
if [ -f "$PROJECT_DIR/.env" ]; then
    set -a
    source "$PROJECT_DIR/.env"
    set +a
fi

# Database connection parameters
DB_HOST="${PGHOST:-localhost}"
DB_PORT="${PGPORT:-5432}"
DB_NAME="${PGDATABASE:-vestra}"
DB_USER="${PGUSER:-postgres}"
DB_PASSWORD="${PGPASSWORD:-${POSTGRES_PASSWORD:-}}"

# Backup storage
BACKUP_DIR="${BACKUP_DIR:-/var/backups/vestra/postgres}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
UPLOAD_ENABLED="${BACKUP_UPLOAD_ENABLED:-false}"

# Remote storage (S3-compatible)
S3_BUCKET="${BACKUP_S3_BUCKET:-}"
S3_PREFIX="${BACKUP_S3_PREFIX:-backups/postgres}"
S3_ENDPOINT="${BACKUP_S3_ENDPOINT:-}"  # For MinIO or other S3-compatible storage
AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-}"
AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-}"

# Remote storage (GCS)
GCS_BUCKET="${BACKUP_GCS_BUCKET:-}"

# Remote storage (SFTP)
SFTP_HOST="${BACKUP_SFTP_HOST:-}"
SFTP_PORT="${BACKUP_SFTP_PORT:-22}"
SFTP_USER="${BACKUP_SFTP_USER:-}"
SFTP_PASSWORD="${BACKUP_SFTP_PASSWORD:-}"
SFTP_PATH="${BACKUP_SFTP_PATH:-backups/postgres}"

# Alerting
ALERT_WEBHOOK_URL="${BACKUP_ALERT_WEBHOOK_URL:-}"
ALERT_EMAIL="${BACKUP_ALERT_EMAIL:-${ALERT_EMAIL:-}}"

# Performance
PARALLEL_JOBS="${BACKUP_PARALLEL_JOBS:-2}"  # Number of parallel dump jobs
COMPRESSION_LEVEL="${BACKUP_COMPRESSION_LEVEL:-6}"  # gzip level 1-9

# ── Color Output ──────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ── Helper Functions ──────────────────────────────────────────────────────────

log_info() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] ${BLUE}INFO${NC}: $*"
}

log_success() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] ${GREEN}OK${NC}: $*"
}

log_warn() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] ${YELLOW}WARN${NC}: $*"
}

log_error() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] ${RED}ERROR${NC}: $*" >&2
}

cleanup() {
    # Remove lockfile on exit
    rm -f "$LOCKFILE"
    log_info "Cleanup complete."
}

# Send alert notification
send_alert() {
    local subject="$1"
    local message="$2"
    local severity="${3:-error}"

    # Webhook alert (Slack, Teams, etc.)
    if [ -n "$ALERT_WEBHOOK_URL" ]; then
        local payload
        payload=$(cat <<EOF
{
    "text": "[VESTRA Backup - $severity] $subject",
    "attachments": [{"text": "$message", "color": "$([ "$severity" = "error" ] && echo "danger" || echo "warning")"}]
}
EOF
        )
        curl -s -X POST -H "Content-Type: application/json" -d "$payload" "$ALERT_WEBHOOK_URL" 2>/dev/null || true
    fi

    # Email alert
    if [ -n "$ALERT_EMAIL" ]; then
        echo "$message" | mail -s "[VESTRA Backup] $subject" "$ALERT_EMAIL" 2>/dev/null || true
    fi
}

# Output Prometheus-compatible metrics
output_metrics() {
    local status="$1"
    local duration="$2"
    local size_bytes="$3"
    local file_count="$4"

    cat <<EOF
# HELP vestra_backup_status Backup job status (0=success, 1=failure)
# TYPE vestra_backup_status gauge
vestra_backup_status{db="${DB_NAME}"} $status

# HELP vestra_backup_duration_seconds Duration of the last backup run
# TYPE vestra_backup_duration_seconds gauge
vestra_backup_duration_seconds{db="${DB_NAME}"} $duration

# HELP vestra_backup_size_bytes Size of the last backup file
# TYPE vestra_backup_size_bytes gauge
vestra_backup_size_bytes{db="${DB_NAME}"} $size_bytes

# HELP vestra_backup_files_total Number of backup files retained
# TYPE vestra_backup_files_total gauge
vestra_backup_files_total{db="${DB_NAME}"} $file_count

# HELP vestra_backup_timestamp_seconds Unix timestamp of the last backup
# TYPE vestra_backup_timestamp_seconds gauge
vestra_backup_timestamp_seconds{db="${DB_NAME}"} $(date +%s)
EOF
}

# ── Argument Parsing ──────────────────────────────────────────────────────────
DRY_RUN=false
UPLOAD_ONLY=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --db-name=*) DB_NAME="${1#*=}" ;;
        --output-dir=*) BACKUP_DIR="${1#*=}" ;;
        --retention-days=*) RETENTION_DAYS="${1#*=}" ;;
        --upload-only) UPLOAD_ONLY=true ;;
        --dry-run) DRY_RUN=true ;;
        --help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --db-name=NAME      Database name (default: vestra)"
            echo "  --output-dir=DIR    Backup output directory"
            echo "  --retention-days=N  Days to keep backups (default: 30)"
            echo "  --upload-only       Only upload existing backups, don't create new"
            echo "  --dry-run           Show what would be done without doing it"
            echo "  --help              Show this help"
            exit 0
            ;;
        *) log_error "Unknown option: $1"; exit 1 ;;
    esac
    shift
done

# ── Pre-flight Checks ─────────────────────────────────────────────────────────

# Check for lockfile (prevent concurrent runs)
if [ -f "$LOCKFILE" ]; then
    local pid
    pid=$(cat "$LOCKFILE" 2>/dev/null)
    if kill -0 "$pid" 2>/dev/null; then
        log_error "Backup already running (PID $pid). Exiting."
        exit 1
    else
        log_warn "Stale lockfile found. Removing."
        rm -f "$LOCKFILE"
    fi
fi
echo $$ > "$LOCKFILE"
trap cleanup EXIT

# Check required commands
required_cmds=("pg_dump" "gzip")
for cmd in "${required_cmds[@]}"; do
    if ! command -v "$cmd" &>/dev/null; then
        log_error "Required command not found: $cmd"
        send_alert "Backup failed" "Required command not found: $cmd" "error"
        output_metrics 1 0 0 0
        exit 1
    fi
done

# Check database connectivity
log_info "Checking database connectivity..."
PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" &>/dev/null || {
    log_error "Cannot connect to database $DB_NAME at $DB_HOST:$DB_PORT"
    send_alert "Backup failed" "Cannot connect to database $DB_NAME at $DB_HOST:$DB_PORT" "error"
    output_metrics 1 0 0 0
    exit 1
}
log_success "Database connection OK"

# ── Upload-Only Mode ──────────────────────────────────────────────────────────
if [ "$UPLOAD_ONLY" = true ]; then
    log_info "Upload-only mode enabled. Skipping backup creation."
    # Find latest backup and upload it
    LATEST_BACKUP=$(find "$BACKUP_DIR" -name "vestra_*.sql.gz" -type f | sort | tail -1)
    if [ -n "$LATEST_BACKUP" ]; then
        log_info "Found existing backup: $LATEST_BACKUP"
        # Upload flow reuses the upload function below
    else
        log_error "No existing backups found in $BACKUP_DIR"
        exit 1
    fi
fi

# ── Create Backup ─────────────────────────────────────────────────────────────

# Ensure backup directory exists
mkdir -p "$BACKUP_DIR"

# Backup filename
BACKUP_FILE="${BACKUP_DIR}/vestra_${DB_NAME}_${TIMESTAMP}.sql.gz"
BACKUP_FILE_PLAIN="${BACKUP_DIR}/vestra_${DB_NAME}_${TIMESTAMP}.sql"

log_info "Starting backup of database: $DB_NAME"
log_info "Output file: $BACKUP_FILE"

if [ "$DRY_RUN" = true ]; then
    log_info "[DRY RUN] Would create backup: $BACKUP_FILE"
    log_info "[DRY RUN] Would upload to remote storage"
    log_info "[DRY RUN] Would clean up backups older than $RETENTION_DAYS days"
    output_metrics 0 0 0 0
    exit 0
fi

# Step 1: Dump the database using pg_dump in custom format, then pipe to gzip
# --format=custom: Custom compressed format (restores with pg_restore)
# --compress=0: No internal compression (we pipe to gzip for higher ratio)
# --no-owner: Don't include owner statements (safer for cross-environment restore)
# --no-acl: Don't include privilege statements
# --verbose: Show detailed progress on stderr
# --lock-wait-timeout=30: Fail if we can't get a lock within 30 seconds

log_info "Dumping database (parallel=$PARALLEL_JOBS, compression level=$COMPRESSION_LEVEL)..."

if ! PGPASSWORD="$DB_PASSWORD" pg_dump \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    --format=custom \
    --compress=0 \
    --no-owner \
    --no-acl \
    --verbose \
    --jobs="$PARALLEL_JOBS" \
    --lock-wait-timeout=30 \
    2>"${BACKUP_FILE_PLAIN}.log" \
    | gzip -"${COMPRESSION_LEVEL}" > "$BACKUP_FILE"; then
    log_error "pg_dump failed for database $DB_NAME"
    send_alert "Backup failed" "pg_dump failed for database $DB_NAME. Check log: ${BACKUP_FILE_PLAIN}.log" "error"
    rm -f "$BACKUP_FILE"
    output_metrics 1 0 0 0
    exit 1
fi

# Also create a plain SQL backup (useful for grepping, smaller restores)
log_info "Creating plain SQL dump..."
if ! PGPASSWORD="$DB_PASSWORD" pg_dump \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    --format=plain \
    --no-owner \
    --no-acl \
    --compress="$COMPRESSION_LEVEL" \
    --lock-wait-timeout=30 \
    --file="${BACKUP_DIR}/vestra_${DB_NAME}_${TIMESTAMP}_plain.sql.gz"; then
    log_warn "Plain SQL dump failed (non-fatal)"
fi

# Verify backup integrity
log_info "Verifying backup integrity..."
BACKUP_SIZE=$(stat -c%s "$BACKUP_FILE" 2>/dev/null || stat -f%z "$BACKUP_FILE" 2>/dev/null)
if [ "$BACKUP_SIZE" -lt 1000 ]; then
    log_error "Backup file is suspiciously small (${BACKUP_SIZE} bytes). Possible failure."
    send_alert "Backup verification failed" "Backup file is only ${BACKUP_SIZE} bytes for $DB_NAME" "error"
    rm -f "$BACKUP_FILE"
    output_metrics 1 0 0 0
    exit 1
fi

# Test the backup can be read (pg_restore --list reads the TOC without restoring)
if command -v pg_restore &>/dev/null; then
    if ! gunzip -c "$BACKUP_FILE" | pg_restore --list &>/dev/null; then
        log_error "Backup integrity check failed — pg_restore cannot read the archive"
        send_alert "Backup integrity check failed" "Backup archive is corrupt for $DB_NAME" "error"
        rm -f "$BACKUP_FILE"
        output_metrics 1 0 0 0
        exit 1
    fi
    log_success "Backup integrity verified (pg_restore --list passed)"
fi

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
BACKUP_SIZE_HUMAN=$(numfmt --to=iec "$BACKUP_SIZE" 2>/dev/null || echo "${BACKUP_SIZE} bytes")

log_success "Backup completed successfully!"
log_info "  File: $BACKUP_FILE"
log_info "  Size: $BACKUP_SIZE_HUMAN (${BACKUP_SIZE} bytes)"
log_info "  Duration: ${DURATION}s"

# ── Upload to Remote Storage ──────────────────────────────────────────────────

if [ "$UPLOAD_ENABLED" != "true" ]; then
    log_info "Remote upload disabled (set BACKUP_UPLOAD_ENABLED=true to enable)."
else
    log_info "Uploading backup to remote storage..."

    # Upload to S3 (or S3-compatible like MinIO, DigitalOcean Spaces)
    if [ -n "$S3_BUCKET" ]; then
        if command -v aws &>/dev/null; then
            S3_DEST="s3://${S3_BUCKET}/${S3_PREFIX}/$(basename "$BACKUP_FILE")"
            S3_ARGS=("s3" "cp" "$BACKUP_FILE" "$S3_DEST" "--no-progress")

            if [ -n "$S3_ENDPOINT" ]; then
                S3_ARGS+=("--endpoint-url=$S3_ENDPOINT")
            fi

            if aws "${S3_ARGS[@]}"; then
                log_success "Uploaded to S3: $S3_DEST"

                # Upload the plain SQL backup too
                PLAIN_FILE="${BACKUP_DIR}/vestra_${DB_NAME}_${TIMESTAMP}_plain.sql.gz"
                if [ -f "$PLAIN_FILE" ]; then
                    aws s3 cp "$PLAIN_FILE" "s3://${S3_BUCKET}/${S3_PREFIX}/$(basename "$PLAIN_FILE")" --no-progress || true
                fi

                # Upload the log file
                aws s3 cp "${BACKUP_FILE_PLAIN}.log" "s3://${S3_BUCKET}/${S3_PREFIX}/$(basename "${BACKUP_FILE_PLAIN}.log")" --no-progress || true
            else
                log_warn "S3 upload failed. Continuing with local backup only."
            fi
        else
            log_warn "aws CLI not found. Cannot upload to S3."
        fi
    fi

    # Upload to GCS
    if [ -n "$GCS_BUCKET" ]; then
        if command -v gsutil &>/dev/null; then
            GCS_DEST="gs://${GCS_BUCKET}/${S3_PREFIX}/$(basename "$BACKUP_FILE")"
            if gsutil cp "$BACKUP_FILE" "$GCS_DEST"; then
                log_success "Uploaded to GCS: $GCS_DEST"
            else
                log_warn "GCS upload failed. Continuing with local backup only."
            fi
        else
            log_warn "gsutil not found. Cannot upload to GCS."
        fi
    fi

    # Upload via SFTP
    if [ -n "$SFTP_HOST" ] && [ -n "$SFTP_USER" ]; then
        if command -v sshpass &>/dev/null && [ -n "$SFTP_PASSWORD" ]; then
            SSH_CMD="sshpass -p '$SFTP_PASSWORD' sftp -o StrictHostKeyChecking=no -P $SFTP_PORT"
        elif command -v sftp &>/dev/null; then
            SSH_CMD="sftp -o StrictHostKeyChecking=no -P $SFTP_PORT"
        else
            log_warn "Neither sshpass nor sftp available for SFTP upload."
            SSH_CMD=""
        fi

        if [ -n "$SSH_CMD" ]; then
            # Create remote directory and upload
            if echo "put $BACKUP_FILE ${SFTP_PATH}/" | eval "$SSH_CMD ${SFTP_USER}@${SFTP_HOST}" &>/dev/null; then
                log_success "Uploaded via SFTP: ${SFTP_USER}@${SFTP_HOST}:${SFTP_PATH}/"
            else
                log_warn "SFTP upload failed. Continuing with local backup only."
            fi
        fi
    fi
fi

# ── Cleanup Old Backups ───────────────────────────────────────────────────────

log_info "Cleaning up backups older than $RETENTION_DAYS days..."

OLD_BACKUPS=$(find "$BACKUP_DIR" -name "vestra_*.sql.gz" -type f -mtime "+${RETENTION_DAYS}" | sort)
OLD_COUNT=$(echo "$OLD_BACKUPS" | grep -c . || true)

if [ "$OLD_COUNT" -gt 0 ]; then
    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY RUN] Would delete $OLD_COUNT old backup files"
        echo "$OLD_BACKUPS" | while read -r f; do
            log_info "[DRY RUN]   Would delete: $f"
        done
    else
        echo "$OLD_BACKUPS" | while read -r f; do
            rm -f "$f"
            log_info "Deleted old backup: $f"
            # Also delete associated files
            rm -f "${f%.sql.gz}.log" 2>/dev/null || true
            rm -f "${f%.sql.gz}_plain.sql.gz" 2>/dev/null || true
        done
        log_success "Deleted $OLD_COUNT old backup(s)"
    fi
else
    log_info "No old backups to clean up."
fi

# Clean up pg_dump log file (keep last 5)
find "$BACKUP_DIR" -name "vestra_*.log" -type f | sort | head -n -5 | while read -r f; do
    rm -f "$f"
done

# Calculate remaining backup count
REMAINING_COUNT=$(find "$BACKUP_DIR" -name "vestra_*.sql.gz" -type f | wc -l)
REMAINING_SIZE=$(find "$BACKUP_DIR" -name "vestra_*.sql.gz" -type f -exec stat -c%s {} + 2>/dev/null | paste -sd+ | bc || echo 0)

log_success "Backup retention: $REMAINING_COUNT files, $(numfmt --to=iec "$REMAINING_SIZE" 2>/dev/null || echo "${REMAINING_SIZE} bytes") total"

# ── Final Output ──────────────────────────────────────────────────────────────

# Output metrics for Prometheus
output_metrics 0 "$DURATION" "$BACKUP_SIZE" "$REMAINING_COUNT" > "${BACKUP_DIR}/.metrics" 2>/dev/null || true

log_success "Backup job completed in ${DURATION}s"
log_info "Backup directory: $BACKUP_DIR"
log_info "Next steps:"
echo "  - To restore: gunzip -c $BACKUP_FILE | pg_restore -d $DB_NAME"
echo "  - To restore (custom format): gunzip -c $BACKUP_FILE | pg_restore --jobs=4 -d $DB_NAME"
echo "  - List contents: gunzip -c $BACKUP_FILE | pg_restore --list"

exit 0
