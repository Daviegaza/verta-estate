#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# VESTRA — Comprehensive Health Check Script
# AI-Powered Property Trust & Operating System for Africa
# ═══════════════════════════════════════════════════════════════════════════════
#
# Features:
#   - Checks ALL services: API, Frontend, PostgreSQL, Redis, Worker, Monitoring
#   - Prometheus-compatible metrics output (also writes to file for node_exporter)
#   - Configurable thresholds (timeout, retries)
#   - Support for authenticated health endpoints (HEALTH_CHECK_TOKEN)
#   - Color-coded terminal output for human readability
#   - JSON output for machine parsing (--json flag)
#   - Exit code: 0 = all healthy, 1 = warnings, 2 = critical failures
#
# Usage:
#   ./scripts/health-check.sh                          # Standard check (all services)
#   ./scripts/health-check.sh --service=api             # Check only API
#   ./scripts/health-check.sh --json                   # JSON output
#   ./scripts/health-check.sh --prometheus-file=/path   # Write Prometheus metrics
#   ./scripts/health-check.sh --timeout=10              # Custom timeout per check
#   ./scripts/health-check.sh --slack-webhook=URL       # Alert on failure
#
# Cron recommendation (every 5 minutes):
#   */5 * * * * /path/to/vestra/scripts/health-check.sh --prometheus-file=/var/lib/node_exporter/textfile/vestra_health.prom
#
# Dependencies: curl, nc (netcat), psql (optional), redis-cli (optional)
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail
IFS=$'\n\t'

# ── Script Configuration ──────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
START_TIME=$(date +%s)

# ── Default Values ────────────────────────────────────────────────────────────
# Load from .env if present
if [ -f "$PROJECT_DIR/.env" ]; then
    set -a
    source "$PROJECT_DIR/.env"
    set +a
fi

# Service endpoints (override via environment variables or --endpoint flags)
API_URL="${HEALTH_API_URL:-http://localhost:8000}"
FRONTEND_URL="${HEALTH_FRONTEND_URL:-http://localhost:3000}"
NGINX_URL="${HEALTH_NGINX_URL:-http://localhost:80}"
PROMETHEUS_URL="${HEALTH_PROMETHEUS_URL:-http://localhost:9090}"
GRAFANA_URL="${HEALTH_GRAFANA_URL:-http://localhost:3001}"
ALERTMANAGER_URL="${HEALTH_ALERTMANAGER_URL:-http://localhost:9093}"
FLOWER_URL="${HEALTH_FLOWER_URL:-http://localhost:5555}"

# Database
DB_HOST="${PGHOST:-localhost}"
DB_PORT="${PGPORT:-5432}"
DB_NAME="${PGDATABASE:-vestra}"
DB_USER="${PGUSER:-postgres}"
DB_PASSWORD="${PGPASSWORD:-${POSTGRES_PASSWORD:-}}"

# Redis
REDIS_HOST="${REDIS_HOST:-localhost}"
REDIS_PORT="${REDIS_PORT:-6379}"
REDIS_PASSWORD="${REDIS_PASSWORD:-}"

# Authentication
HEALTH_CHECK_TOKEN="${HEALTH_CHECK_TOKEN:-}"

# Thresholds
TIMEOUT="${HEALTH_CHECK_TIMEOUT:-5}"        # Seconds per check
CRITICAL_THRESHOLD="${HEALTH_CRITICAL_THRESHOLD:-3}"  # Number of failed checks before critical

# Output
PROMETHEUS_FILE="${HEALTH_PROMETHEUS_FILE:-}"
SLACK_WEBHOOK_URL="${HEALTH_SLACK_WEBHOOK_URL:-}"

# ── Color & Formatting ────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# ── State ─────────────────────────────────────────────────────────────────────
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0
WARN_CHECKS=0
declare -A CHECK_RESULTS
declare -A CHECK_DURATIONS
declare -A CHECK_MESSAGES
EXIT_CODE=0

# ── Helper Functions ──────────────────────────────────────────────────────────

log_info() {
    echo -e "[$(date '+%H:%M:%S')] ${BLUE}INFO${NC}: $*"
}

log_success() {
    echo -e "[$(date '+%H:%M:%S')] ${GREEN}OK${NC}: $*"
}

log_warn() {
    echo -e "[$(date '+%H:%M:%S')] ${YELLOW}WARN${NC}: $*"
    WARN_CHECKS=$((WARN_CHECKS + 1))
}

log_fail() {
    echo -e "[$(date '+%H:%M:%S')] ${RED}FAIL${NC}: $*"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
    EXIT_CODE=2
}

record_result() {
    local service="$1"
    local status="$2"
    local duration="$3"
    local message="$4"
    CHECK_RESULTS["$service"]="$status"
    CHECK_DURATIONS["$service"]="$duration"
    CHECK_MESSAGES["$service"]="$message"
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    if [ "$status" = "pass" ]; then
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    fi
}

# Perform an HTTP health check
check_http() {
    local name="$1"
    local url="$2"
    local expected_status="${3:-200}"
    local timeout="${4:-$TIMEOUT}"

    local start
    start=$(date +%s%N)

    local curl_args=(
        "--max-time" "$timeout"
        "--connect-timeout" "$((timeout / 2))"
        "--silent"
        "--output" "/dev/null"
        "--write-out" "%{http_code}"
        "--insecure"  # Allow self-signed certs in internal checks
    )

    # Add health check token if configured
    if [ -n "$HEALTH_CHECK_TOKEN" ]; then
        curl_args+=("--header" "X-Health-Check-Token: $HEALTH_CHECK_TOKEN")
    fi

    local http_code
    http_code=$(curl "${curl_args[@]}" "$url" 2>/dev/null || echo "000")

    local end
    end=$(date +%s%N)
    local duration_ms=$(( (end - start) / 1000000 ))

    if [ "$http_code" = "$expected_status" ]; then
        log_success "$name — HTTP $http_code (${duration_ms}ms)"
        record_result "$name" "pass" "$duration_ms" "HTTP ${http_code}"
        return 0
    elif [ "$http_code" = "000" ]; then
        log_fail "$name — Connection failed (${duration_ms}ms)"
        record_result "$name" "fail" "$duration_ms" "Connection failed"
        return 1
    else
        log_fail "$name — Expected $expected_status, got $http_code (${duration_ms}ms)"
        record_result "$name" "fail" "$duration_ms" "Expected ${expected_status}, got ${http_code}"
        return 1
    fi
}

# Perform a TCP port check
check_tcp() {
    local name="$1"
    local host="$2"
    local port="$3"
    local timeout="${4:-$TIMEOUT}"

    local start
    start=$(date +%s%N)

    if command -v nc &>/dev/null; then
        if nc -z -w "$timeout" "$host" "$port" &>/dev/null; then
            local end
            end=$(date +%s%N)
            local duration_ms=$(( (end - start) / 1000000 ))
            log_success "$name — TCP $host:$port OPEN (${duration_ms}ms)"
            record_result "$name" "pass" "$duration_ms" "TCP port open"
            return 0
        fi
    elif command -v curl &>/dev/null; then
        # Fallback: use curl's telnet support
        if curl --max-time "$timeout" "telnet://${host}:${port}" &>/dev/null; then
            local end
            end=$(date +%s%N)
            local duration_ms=$(( (end - start) / 1000000 ))
            log_success "$name — TCP $host:$port OPEN (${duration_ms}ms)"
            record_result "$name" "pass" "$duration_ms" "TCP port open"
            return 0
        fi
    else
        log_warn "$name — Cannot check TCP (neither nc nor curl with telnet available)"
        record_result "$name" "warn" 0 "No TCP check tool available"
        return 2
    fi

    local end
    end=$(date +%s%N)
    local duration_ms=$(( (end - start) / 1000000 ))
    log_fail "$name — TCP $host:$port CLOSED (${duration_ms}ms)"
    record_result "$name" "fail" "$duration_ms" "TCP port closed"
    return 1
}

# Check PostgreSQL
check_postgres() {
    local name="PostgreSQL"
    local start
    start=$(date +%s%N)

    if PGPASSWORD="$DB_PASSWORD" psql \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        -c "SELECT 1;" \
        -t \
        -q \
        --no-psqlrc \
        -P footer=off \
        -o /dev/null \
        2>/dev/null; then
        local end
        end=$(date +%s%N)
        local duration_ms=$(( (end - start) / 1000000 ))
        log_success "$name — Connected (${duration_ms}ms)"
        record_result "$name" "pass" "$duration_ms" "Connected"
        return 0
    else
        local end
        end=$(date +%s%N)
        local duration_ms=$(( (end - start) / 1000000 ))
        if command -v psql &>/dev/null; then
            log_fail "$name — Connection failed (${duration_ms}ms)"
            record_result "$name" "fail" "$duration_ms" "Connection failed"
        else
            log_warn "$name — psql not installed, falling back to TCP check"
            check_tcp "$name" "$DB_HOST" "$DB_PORT"
        fi
        return 1
    fi
}

# Check Redis
check_redis() {
    local name="Redis"
    local start
    start=$(date +%s%N)

    if command -v redis-cli &>/dev/null; then
        local auth_arg=""
        [ -n "$REDIS_PASSWORD" ] && auth_arg="-a '$REDIS_PASSWORD' --no-auth-warning"
        if eval redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" "$auth_arg" ping 2>/dev/null | grep -q "PONG"; then
            local end
            end=$(date +%s%N)
            local duration_ms=$(( (end - start) / 1000000 ))
            log_success "$name — PONG (${duration_ms}ms)"
            record_result "$name" "pass" "$duration_ms" "PONG"
            return 0
        else
            local end
            end=$(date +%s%N)
            local duration_ms=$(( (end - start) / 1000000 ))
            log_fail "$name — Connection failed (${duration_ms}ms)"
            record_result "$name" "fail" "$duration_ms" "Connection failed"
            return 1
        fi
    else
        log_warn "$name — redis-cli not installed, falling back to TCP check"
        check_tcp "$name" "$REDIS_HOST" "$REDIS_PORT"
    fi
}

# ── Argument Parsing ──────────────────────────────────────────────────────────
OUTPUT_MODE="terminal"  # terminal | json
SINGLE_SERVICE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --service=*) SINGLE_SERVICE="${1#*=}" ;;
        --json) OUTPUT_MODE="json" ;;
        --prometheus-file=*) PROMETHEUS_FILE="${1#*=}" ;;
        --slack-webhook=*) SLACK_WEBHOOK_URL="${1#*=}" ;;
        --timeout=*) TIMEOUT="${1#*=}" ;;
        --help)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --service=NAME       Check only a specific service"
            echo "                       Names: api, frontend, nginx, postgres, redis,"
            echo "                              worker, prometheus, grafana, alertmanager,"
            echo "                              flower, all"
            echo "  --json               Output in JSON format"
            echo "  --prometheus-file=PATH  Write Prometheus metrics to file"
            echo "  --slack-webhook=URL  Send alert to Slack webhook on failure"
            echo "  --timeout=N          Timeout in seconds per check (default: 5)"
            echo "  --help               Show this help"
            exit 0
            ;;
        *) log_warn "Unknown option: $1"; exit 1 ;;
    esac
    shift
done

# ── Header ────────────────────────────────────────────────────────────────────

if [ "$OUTPUT_MODE" = "terminal" ]; then
    echo ""
    echo -e "${BOLD}╔══════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}║          VESTRA — Comprehensive Health Check                        ║${NC}"
    echo -e "${BOLD}║          $(date '+%Y-%m-%d %H:%M:%S %Z')                               ║${NC}"
    echo -e "${BOLD}╚══════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
fi

# ── Run Checks ────────────────────────────────────────────────────────────────

# Helper to check if a service should be tested
should_check() {
    local service="$1"
    if [ -z "$SINGLE_SERVICE" ] || [ "$SINGLE_SERVICE" = "all" ] || [ "$SINGLE_SERVICE" = "$service" ]; then
        return 0
    fi
    return 1
}

# ── 1. API Health Endpoint ────────────────────────────────────────────────────
# The primary health endpoint confirms the API server is running and responsive.
if should_check "api"; then
    log_info "Checking API server..."
    check_http "API" "${API_URL}/health" 200
    check_http "API (Ready)" "${API_URL}/health/ready" 200
fi

# ── 2. Frontend ───────────────────────────────────────────────────────────────
if should_check "frontend"; then
    log_info "Checking Frontend..."
    check_http "Frontend" "${FRONTEND_URL}/" 200
fi

# ── 3. Nginx Reverse Proxy ────────────────────────────────────────────────────
if should_check "nginx"; then
    log_info "Checking Nginx..."
    check_http "Nginx" "${NGINX_URL}/health" 200 2
fi

# ── 4. PostgreSQL ─────────────────────────────────────────────────────────────
if should_check "postgres"; then
    log_info "Checking PostgreSQL..."
    check_postgres

    # Additional: check for long-running queries
    if command -v psql &>/dev/null; then
        LONG_QUERIES=$(PGPASSWORD="$DB_PASSWORD" psql \
            -h "$DB_HOST" \
            -p "$DB_PORT" \
            -U "$DB_USER" \
            -d "$DB_NAME" \
            --no-psqlrc \
            -t \
            -A \
            -c "SELECT count(*) FROM pg_stat_activity WHERE state = 'active' AND now() - pg_stat_activity.query_start > interval '5 minutes' AND query NOT LIKE '%pg_stat%' AND query NOT LIKE '%SELECT 1%';" \
            2>/dev/null || echo "0")

        if [ "$LONG_QUERIES" -gt 5 ]; then
            log_warn "PostgreSQL — $LONG_QUERIES long-running queries detected"
            CHECK_MESSAGES["PostgreSQL"]="${CHECK_MESSAGES[PostgreSQL]}; ${LONG_QUERIES} long queries"
        fi
    fi

    # Check replication status
    if command -v psql &>/dev/null; then
        REPLICATION_LAG=$(PGPASSWORD="$DB_PASSWORD" psql \
            -h "$DB_HOST" \
            -p "$DB_PORT" \
            -U "$DB_USER" \
            -d "$DB_NAME" \
            --no-psqlrc \
            -t \
            -A \
            -c "SELECT CASE WHEN pg_is_in_recovery() THEN COALESCE(EXTRACT(EPOCH FROM (now() - pg_last_xact_replay_timestamp()))::text, '0') ELSE '0' END;" \
            2>/dev/null || echo "0")

        if [ "$REPLICATION_LAG" != "0" ] && [ "${REPLICATION_LAG%.*}" -gt 300 ]; then
            log_warn "PostgreSQL — Replication lag: ${REPLICATION_LAG}s"
            CHECK_MESSAGES["PostgreSQL"]="${CHECK_MESSAGES[PostgreSQL]}; Replication lag ${REPLICATION_LAG}s"
        fi
    fi
fi

# ── 5. Redis ──────────────────────────────────────────────────────────────────
if should_check "redis"; then
    log_info "Checking Redis..."
    check_redis

    # Check Redis memory usage
    if command -v redis-cli &>/dev/null && [ -n "$REDIS_PASSWORD" ]; then
        REDIS_INFO=$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" -a "$REDIS_PASSWORD" --no-auth-warning INFO memory 2>/dev/null || echo "")
        if [ -n "$REDIS_INFO" ]; then
            USED_MEMORY=$(echo "$REDIS_INFO" | grep "used_memory_peak_human" | cut -d: -f2 | tr -d '\r')
            MAX_MEMORY=$(echo "$REDIS_INFO" | grep "maxmemory_human" | cut -d: -f2 | tr -d '\r')
            # Check fragmentation
            FRAG_RATIO=$(echo "$REDIS_INFO" | grep "mem_fragmentation_ratio" | cut -d: -f2 | tr -d '\r')
            if [ -n "$FRAG_RATIO" ] && [ "$(echo "$FRAG_RATIO > 1.5" | bc -l 2>/dev/null || echo 0)" -eq 1 ]; then
                log_warn "Redis — High memory fragmentation ratio: $FRAG_RATIO"
                CHECK_MESSAGES["Redis"]="${CHECK_MESSAGES[Redis]}; Fragmentation: ${FRAG_RATIO}"
            fi
        fi
    fi
fi

# ── 6. Background Worker ──────────────────────────────────────────────────────
if should_check "worker"; then
    log_info "Checking Worker..."
    # Workers don't have an HTTP endpoint, so we check Redis connectivity
    # which is the worker's primary dependency
    check_redis

    # Check Celery worker stats via Flower API if available
    if [ -n "$FLOWER_URL" ]; then
        # Just check if Flower is responding
        check_http "Flower" "${FLOWER_URL}/flower" 200 3
    fi
fi

# ── 7. Prometheus ─────────────────────────────────────────────────────────────
if should_check "prometheus"; then
    log_info "Checking Prometheus..."
    check_http "Prometheus" "${PROMETHEUS_URL}/-/ready" 200
fi

# ── 8. Grafana ────────────────────────────────────────────────────────────────
if should_check "grafana"; then
    log_info "Checking Grafana..."
    check_http "Grafana" "${GRAFANA_URL}/api/health" 200
fi

# ── 9. Alertmanager ───────────────────────────────────────────────────────────
if should_check "alertmanager"; then
    log_info "Checking Alertmanager..."
    check_http "Alertmanager" "${ALERTMANAGER_URL}/-/healthy" 200
fi

# ── Summary ───────────────────────────────────────────────────────────────────

END_TIME=$(date +%s)
TOTAL_DURATION=$((END_TIME - START_TIME))

if [ "$OUTPUT_MODE" = "json" ]; then
    # JSON output
    echo "{"
    echo "  \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\","
    echo "  \"duration_seconds\": $TOTAL_DURATION,"
    echo "  \"summary\": {"
    echo "    \"total\": $TOTAL_CHECKS,"
    echo "    \"passed\": $PASSED_CHECKS,"
    echo "    \"failed\": $FAILED_CHECKS,"
    echo "    \"warnings\": $WARN_CHECKS"
    echo "  },"
    echo "  \"overall_status\": \"$([ $EXIT_CODE -eq 0 ] && echo 'healthy' || ([ $EXIT_CODE -eq 1 ] && echo 'degraded' || echo 'critical'))\","
    echo "  \"checks\": ["
    local first=true
    for service in "${!CHECK_RESULTS[@]}"; do
        $first || echo ","
        first=false
        echo "    {"
        echo "      \"service\": \"$service\","
        echo "      \"status\": \"${CHECK_RESULTS[$service]}\","
        echo "      \"duration_ms\": ${CHECK_DURATIONS[$service]:-0},"
        echo "      \"message\": \"${CHECK_MESSAGES[$service]:-}\""
        echo -n "    }"
    done
    echo ""
    echo "  ]"
    echo "}"
else
    # Terminal output
    echo ""
    echo -e "${BOLD}╔══════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}║                           Summary                                    ║${NC}"
    echo -e "${BOLD}╚══════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    printf "  ${BOLD}%-25s${NC} %s\n" "Total checks:" "$TOTAL_CHECKS"
    printf "  ${GREEN}%-25s${NC} %s\n" "Passed:" "$PASSED_CHECKS"
    if [ "$FAILED_CHECKS" -gt 0 ]; then
        printf "  ${RED}%-25s${NC} %s\n" "Failed:" "$FAILED_CHECKS"
    else
        printf "  %-25s %s\n" "Failed:" "$FAILED_CHECKS"
    fi
    if [ "$WARN_CHECKS" -gt 0 ]; then
        printf "  ${YELLOW}%-25s${NC} %s\n" "Warnings:" "$WARN_CHECKS"
    else
        printf "  %-25s %s\n" "Warnings:" "$WARN_CHECKS"
    fi
    printf "  %-25s %ds\n" "Duration:" "$TOTAL_DURATION"

    echo ""
    if [ "$FAILED_CHECKS" -gt 0 ]; then
        echo -e "  ${RED}Status: CRITICAL — Some services are down${NC}"
    elif [ "$WARN_CHECKS" -gt 0 ]; then
        echo -e "  ${YELLOW}Status: DEGRADED — All services responding but with warnings${NC}"
    else
        echo -e "  ${GREEN}Status: HEALTHY — All services operational${NC}"
    fi
    echo ""
fi

# ── Write Prometheus Metrics ──────────────────────────────────────────────────

if [ -n "$PROMETHEUS_FILE" ]; then
    METRICS_DIR="$(dirname "$PROMETHEUS_FILE")"
    mkdir -p "$METRICS_DIR"

    cat > "$PROMETHEUS_FILE" << EOF
# HELP vestra_health_overall Overall health status (0=healthy, 1=degraded, 2=critical)
# TYPE vestra_health_overall gauge
vestra_health_overall $EXIT_CODE

# HELP vestra_health_checks_total Total number of health checks performed
# TYPE vestra_health_checks_total gauge
vestra_health_checks_total $TOTAL_CHECKS

# HELP vestra_health_checks_passed Number of passed health checks
# TYPE vestra_health_checks_passed gauge
vestra_health_checks_passed $PASSED_CHECKS

# HELP vestra_health_checks_failed Number of failed health checks
# TYPE vestra_health_checks_failed gauge
vestra_health_checks_failed $FAILED_CHECKS

# HELP vestra_health_checks_warnings Number of health checks with warnings
# TYPE vestra_health_checks_warnings gauge
vestra_health_checks_warnings $WARN_CHECKS

# HELP vestra_health_duration_seconds Duration of the health check run
# TYPE vestra_health_duration_seconds gauge
vestra_health_duration_seconds $TOTAL_DURATION

# HELP vestra_health_timestamp_seconds Unix timestamp of last health check
# TYPE vestra_health_timestamp_seconds gauge
vestra_health_timestamp_seconds $(date +%s)
EOF

    # Write per-service health metrics
    for service in "${!CHECK_RESULTS[@]}"; do
        local status_code=0
        case "${CHECK_RESULTS[$service]}" in
            pass) status_code=0 ;;
            warn) status_code=1 ;;
            fail) status_code=2 ;;
        esac
        local duration="${CHECK_DURATIONS[$service]:-0}"
        # Sanitize service name for Prometheus label
        local sanitized_name
        sanitized_name=$(echo "$service" | tr '[:upper:]' '[:lower:]' | tr ' ()' '_')
        cat >> "$PROMETHEUS_FILE" << EOF

# HELP vestra_health_service_status Service health status (0=pass, 1=warn, 2=fail)
# TYPE vestra_health_service_status gauge
vestra_health_service_status{service="${sanitized_name}"} $status_code

# HELP vestra_health_service_duration_ms Service check duration in milliseconds
# TYPE vestra_health_service_duration_ms gauge
vestra_health_service_duration_ms{service="${sanitized_name}"} $duration
EOF
    done

    log_info "Prometheus metrics written to $PROMETHEUS_FILE"
fi

# ── Slack Alert on Failure ────────────────────────────────────────────────────

if [ -n "$SLACK_WEBHOOK_URL" ] && [ "$FAILED_CHECKS" -gt 0 ]; then
    local slack_color
    if [ "$EXIT_CODE" -eq 2 ]; then
        slack_color="danger"
    else
        slack_color="warning"
    fi

    local slack_message
    slack_message=$(cat <<EOF
{
    "text": "*VESTRA Health Check — FAILED*",
    "attachments": [
        {
            "color": "${slack_color}",
            "fields": [
                {"title": "Status", "value": "$([ $EXIT_CODE -eq 0 ] && echo 'Healthy' || ([ $EXIT_CODE -eq 1 ] && echo 'Degraded' || echo 'Critical'))", "short": true},
                {"title": "Failed", "value": "${FAILED_CHECKS}/${TOTAL_CHECKS}", "short": true},
                {"title": "Duration", "value": "${TOTAL_DURATION}s", "short": true}
            ],
            "footer": "VESTRA Health Check",
            "ts": $(date +%s)
        }
    ]
}
EOF
    )
    curl -s -X POST -H "Content-Type: application/json" -d "$slack_message" "$SLACK_WEBHOOK_URL" 2>/dev/null || true
    log_info "Slack alert sent."
fi

exit $EXIT_CODE
