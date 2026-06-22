#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# VESTRA DEEP RESEARCH — Startup Script
# =====================================
# Starts the full VESTRA platform with Deep Research capabilities.
#
# Usage:
#   ./start.sh              # Interactive setup + start
#   ./start.sh --dev        # Development mode (hot reload)
#   ./start.sh --prod       # Production mode (gunicorn + optimized)
#   ./start.sh --install    # Install all dependencies
#   ./start.sh --check      # Verify system compatibility
#   ./start.sh --deep-research  # Start only deep research API
#   ./start.sh --help       # Show this help
#
# Prerequisites:
#   - Python 3.11+
#   - Node.js 20+
#   - PostgreSQL 16+ (or Docker)
#   - Redis 7+ (or Docker)
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail
IFS=$'\n\t'

# ── Colors ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; MAGENTA='\033[0;35m'; CYAN='\033[0;36m'
BOLD='\033[1m'; NC='\033[0m' # No Color

# ── Paths ────────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/vestra/backend"
FRONTEND_DIR="$SCRIPT_DIR/vestra/frontend-build"
VENV_DIR="$BACKEND_DIR/.venv"
REPORTS_DIR="$SCRIPT_DIR/reports"
DATA_DIR="$SCRIPT_DIR/data/vectors"
LOG_DIR="$SCRIPT_DIR/logs"

# ── Banner ────────────────────────────────────────────────────────────────────
banner() {
    echo -e "${MAGENTA}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║  ██╗   ██╗███████╗███████╗████████╗██████╗  █████╗         ║"
    echo "║  ██║   ██║██╔════╝██╔════╝╚══██╔══╝██╔══██╗██╔══██╗        ║"
    echo "║  ██║   ██║█████╗  ███████╗   ██║   ██████╔╝███████║        ║"
    echo "║  ╚██╗ ██╔╝██╔══╝  ╚════██║   ██║   ██╔══██╗██╔══██║        ║"
    echo "║   ╚████╔╝ ███████╗███████║   ██║   ██║  ██║██║  ██║        ║"
    echo "║    ╚═══╝  ╚══════╝╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝        ║"
    echo "║                                                              ║"
    echo "║           DEEP RESEARCH — Property Intelligence             ║"
    echo "║                  v4.1.0 — World Class                        ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# ── Help ──────────────────────────────────────────────────────────────────────
show_help() {
    banner
    echo -e "${BOLD}USAGE:${NC}"
    echo "  ./start.sh [OPTION]"
    echo ""
    echo -e "${BOLD}OPTIONS:${NC}"
    echo "  (no flag)       Interactive setup + start all services"
    echo "  --dev           Development mode (hot reload, debug logging)"
    echo "  --prod          Production mode (gunicorn + optimized)"
    echo "  --install       Install all dependencies (Python + Node)"
    echo "  --check         Verify system compatibility and report issues"
    echo "  --deep-research Start only the Deep Research API server"
    echo "  --docker        Start everything via Docker Compose"
    echo "  --stop          Stop all running services"
    echo "  --help          Show this help message"
    echo ""
    echo -e "${BOLD}EXAMPLES:${NC}"
    echo "  ./start.sh                    # Full interactive setup"
    echo "  ./start.sh --dev              # Dev mode with hot reload"
    echo "  ./start.sh --deep-research    # Just the deep research API"
    echo "  ./start.sh --docker           # Run via Docker Compose"
    echo ""
    echo -e "${BOLD}ENVIRONMENT:${NC}"
    echo "  Copy vestra/backend/.env.example to vestra/backend/.env"
    echo "  Required: DATABASE_URL, REDIS_URL, SECRET_KEY"
    echo "  For Deep Research: DEEP_RESEARCH_LLM_API_KEY (Anthropic/OpenAI)"
    echo ""
}

# ── System Check ──────────────────────────────────────────────────────────────
check_system() {
    echo -e "${BLUE}🔍 Checking system compatibility...${NC}\n"

    local all_ok=true

    check_cmd() {
        local cmd="$1" name="$2" version_flag="${3:---version}"
        if command -v "$cmd" &>/dev/null; then
            local version
            version=$("$cmd" $version_flag 2>&1 | head -1 || echo "unknown")
            echo -e "  ${GREEN}✅${NC} $name — $version"
            return 0
        else
            echo -e "  ${RED}❌${NC} $name — NOT FOUND"
            all_ok=false
            return 1
        fi
    }

    check_cmd python3 "Python 3" "--version"
    check_cmd node "Node.js" "--version"
    check_cmd npm "npm" "--version"
    check_cmd psql "PostgreSQL client" "--version"
    check_cmd redis-cli "Redis CLI" "--version"

    # Check Python version >= 3.11
    if python3 -c "import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)" 2>/dev/null; then
        echo -e "  ${GREEN}✅${NC} Python >= 3.11"
    else
        echo -e "  ${RED}❌${NC} Python 3.11+ required"
        all_ok=false
    fi

    # Check for Anthropic API key (optional)
    if [ -f "$BACKEND_DIR/.env" ]; then
        if grep -q "DEEP_RESEARCH_LLM_API_KEY=sk-ant" "$BACKEND_DIR/.env" 2>/dev/null; then
            echo -e "  ${GREEN}✅${NC} Anthropic API key found (Deep Research ready)"
        elif grep -q "DEEP_RESEARCH_LLM_API_KEY=sk-" "$BACKEND_DIR/.env" 2>/dev/null; then
            echo -e "  ${GREEN}✅${NC} OpenAI API key found (Deep Research ready)"
        else
            echo -e "  ${YELLOW}⚠️ ${NC} No LLM API key found — Deep Research runs in rule-based mode"
        fi
    else
        echo -e "  ${YELLOW}⚠️ ${NC} No .env file found — copy .env.example to .env"
    fi

    echo ""
    if $all_ok; then
        echo -e "${GREEN}✅ All system checks passed!${NC}\n"
    else
        echo -e "${RED}❌ Some checks failed. Install missing dependencies.${NC}\n"
    fi
    return 0
}

# ── Install Dependencies ──────────────────────────────────────────────────────
install_deps() {
    echo -e "${BLUE}📦 Installing dependencies...${NC}\n"

    # ── Backend Python deps ──────────────────────────────────────────────────
    echo -e "${YELLOW}Python backend dependencies...${NC}"
    cd "$BACKEND_DIR"

    if [ ! -d "$VENV_DIR" ]; then
        python3 -m venv "$VENV_DIR"
        echo -e "  ${GREEN}✅${NC} Virtual environment created at $VENV_DIR"
    fi

    # shellcheck disable=SC1090
    source "$VENV_DIR/bin/activate"
    pip install --upgrade pip -q

    # Install base requirements
    pip install -r requirements.txt -q
    echo -e "  ${GREEN}✅${NC} Core Python packages installed"

    # Install deep research extras
    echo -e "  Installing Deep Research extras..."
    pip install "anthropic>=0.39.0" "sentence-transformers>=3.0.0" "faiss-cpu>=1.8.0" "ddgs>=5.0.0" -q 2>/dev/null || {
        echo -e "  ${YELLOW}⚠️ ${NC} Some deep research packages failed — semantic search/web research may use fallbacks"
    }
    echo -e "  ${GREEN}✅${NC} Deep Research packages installed (or fallbacks available)"

    # ── Frontend Node deps ────────────────────────────────────────────────────
    echo -e "${YELLOW}Frontend dependencies...${NC}"
    cd "$FRONTEND_DIR"
    if [ -f package.json ]; then
        npm install --silent 2>/dev/null || npm install
        echo -e "  ${GREEN}✅${NC} Frontend packages installed"
    else
        echo -e "  ${YELLOW}⚠️ ${NC} No package.json found — skipping frontend"
    fi

    # ── Create directories ────────────────────────────────────────────────────
    mkdir -p "$REPORTS_DIR" "$DATA_DIR" "$LOG_DIR"
    echo -e "  ${GREEN}✅${NC} Created reports/, data/vectors/, logs/ directories"

    cd "$SCRIPT_DIR"
    echo -e "\n${GREEN}✅ All dependencies installed!${NC}\n"
}

# ── Environment Setup ─────────────────────────────────────────────────────────
setup_env() {
    echo -e "${BLUE}🔧 Setting up environment...${NC}\n"

    if [ ! -f "$BACKEND_DIR/.env" ]; then
        if [ -f "$BACKEND_DIR/.env.example" ]; then
            cp "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
            echo -e "  ${GREEN}✅${NC} Created .env from .env.example"
            echo -e "  ${YELLOW}⚠️ ${NC} Please edit $BACKEND_DIR/.env with your actual values!"
            echo ""
            echo -e "${BOLD}For Deep Research, add:${NC}"
            echo "  DEEP_RESEARCH_LLM_PROVIDER=anthropic"
            echo "  DEEP_RESEARCH_LLM_API_KEY=sk-ant-api03-your-key-here"
            echo "  DEEP_RESEARCH_LLM_MODEL=claude-sonnet-4-6"
            echo ""
        else
            echo -e "  ${RED}❌${NC} No .env.example found"
        fi
    else
        echo -e "  ${GREEN}✅${NC} .env file exists"
    fi

    mkdir -p "$REPORTS_DIR" "$DATA_DIR" "$LOG_DIR"
}

# ── Database Setup ────────────────────────────────────────────────────────────
setup_db() {
    echo -e "${BLUE}🗄️  Database setup...${NC}\n"

    cd "$BACKEND_DIR"

    # Source env vars
    if [ -f .env ]; then
        set -a; source .env; set +a
    fi

    # Check if we can connect to PostgreSQL
    local db_host db_port db_user db_pass db_name
    db_host=$(echo "$DATABASE_URL" | sed -n 's|.*@\([^:/]*\).*|\1|p')
    db_port=$(echo "$DATABASE_URL" | sed -n 's|.*:\([0-9]*\)/.*|\1|p')
    db_user=$(echo "$DATABASE_URL" | sed -n 's|.*://\([^:]*\).*|\1|p')
    db_pass=$(echo "$DATABASE_URL" | sed -n 's|.*://[^:]*:\([^@]*\).*|\1|p')
    db_name=$(echo "$DATABASE_URL" | sed -n 's|.*/\([^?]*\).*|\1|p')

    db_host="${db_host:-localhost}"
    db_port="${db_port:-5432}"
    db_user="${db_user:-postgres}"
    db_name="${db_name:-vestra}"

    if PGPASSWORD="$db_pass" psql -h "$db_host" -U "$db_user" -d "$db_name" -c "SELECT 1" >/dev/null 2>&1; then
        echo -e "  ${GREEN}✅${NC} Database connection OK"
    else
        echo -e "  ${YELLOW}⚠️  Cannot connect to PostgreSQL — DB-dependent routes will fail${NC}"
        echo ""
        echo -e "  ${BOLD}Run these commands to set up the database:${NC}"
        echo ""
        echo -e "  ${CYAN}sudo -u postgres psql${NC}"
        echo "  CREATE ROLE vestra WITH LOGIN PASSWORD 'vestra';"
        echo "  CREATE DATABASE vestra OWNER vestra;"
        echo "  ALTER USER vestra CREATEDB;"
        echo "  \\q"
        echo ""
        echo -e "  ${CYAN}sudo -u postgres psql -d vestra${NC}"
        echo "  GRANT ALL ON SCHEMA public TO vestra;"
        echo "  \\q"
        echo ""
        read -rp "  Run these commands now and press Enter to continue... " _
    fi

    # Check Redis
    if redis-cli ping >/dev/null 2>&1; then
        echo -e "  ${GREEN}✅${NC} Redis connection OK"
    else
        echo -e "  ${YELLOW}⚠️  Redis not reachable — caching and rate limiting use in-memory fallback${NC}"
    fi

    # Run migrations
    if [ -f "$VENV_DIR/bin/activate" ]; then
        source "$VENV_DIR/bin/activate"
    fi

    if command -v alembic &>/dev/null; then
        echo -e "  Running database migrations..."
        alembic upgrade head 2>&1 | tail -3
        echo -e "  ${GREEN}✅${NC} Migrations applied"
    else
        echo -e "  ${YELLOW}⚠️ ${NC} Alembic not found — skipping migrations"
    fi

    cd "$SCRIPT_DIR"
}

# ── Check Python Deps ────────────────────────────────────────────────────────
check_python_deps() {
    # Quick check if core packages are installed (in venv or globally)
    local python_cmd="$1"
    $python_cmd -c "import fastapi, sqlalchemy, redis, uvicorn" 2>/dev/null
}

# ── Start Backend ─────────────────────────────────────────────────────────────
start_backend() {
    local mode="${1:-dev}"

    cd "$BACKEND_DIR"

    if [ -f .env ]; then
        set -a; source .env; set +a
    fi

    # Determine Python to use
    local PYTHON_BIN="python3"
    if [ -f "$VENV_DIR/bin/activate" ]; then
        # shellcheck disable=SC1090
        source "$VENV_DIR/bin/activate"
        PYTHON_BIN="$VENV_DIR/bin/python"
        echo -e "  Using venv: $VENV_DIR"
    fi

    # Check if core deps are installed
    if ! check_python_deps "$PYTHON_BIN"; then
        echo -e "  ${YELLOW}⚠️  Python dependencies not installed${NC}"
        echo -e "  ${BLUE}📦 Installing now...${NC}"

        if [ ! -d "$VENV_DIR" ]; then
            python3 -m venv "$VENV_DIR"
            source "$VENV_DIR/bin/activate"
            PYTHON_BIN="$VENV_DIR/bin/python"
        fi

        pip install --upgrade pip -q 2>/dev/null
        pip install -r requirements.txt -q 2>&1 | tail -3

        if check_python_deps "$PYTHON_BIN"; then
            echo -e "  ${GREEN}✅ Dependencies installed${NC}"
        else
            echo -e "  ${RED}❌ Dependency install failed — run: ./start.sh --install${NC}"
            cd "$SCRIPT_DIR"
            return 1
        fi
    fi

    # Auto-configure deep research from env vars (if set)
    if [ -n "${DEEP_RESEARCH_LLM_API_KEY:-}" ]; then
        echo -e "  ${GREEN}✅${NC} Deep Research LLM auto-configured (${DEEP_RESEARCH_LLM_PROVIDER:-anthropic})"
    fi

    if [ "$mode" == "prod" ]; then
        echo -e "${GREEN}🚀 Starting backend (production — gunicorn)...${NC}"
        gunicorn app.main:app \
            -c app/core/gunicorn_conf.py \
            --bind 0.0.0.0:8000 \
            --access-logfile "$LOG_DIR/access.log" \
            --error-logfile "$LOG_DIR/error.log" &
    else
        echo -e "${GREEN}🚀 Starting backend (development — uvicorn hot reload)...${NC}"
        uvicorn app.main:app \
            --host 0.0.0.0 \
            --port 8000 \
            --reload \
            --log-level info &
    fi

    BACKEND_PID=$!
    echo -e "  Backend PID: $BACKEND_PID"
    echo -e "  API Docs:   ${CYAN}http://localhost:8000/docs${NC}"
    echo -e "  Deep Research: ${CYAN}http://localhost:8000/api/v1/deep-research/${NC}"
    cd "$SCRIPT_DIR"
}

# ── Start Frontend ────────────────────────────────────────────────────────────
start_frontend() {
    echo -e "${GREEN}🎨 Starting frontend (Next.js)...${NC}"

    cd "$FRONTEND_DIR"

    if [ ! -f package.json ]; then
        echo -e "  ${YELLOW}⚠️ ${NC} No frontend found — API only mode"
        cd "$SCRIPT_DIR"
        return 0
    fi

    # Check node_modules
    if [ ! -d "node_modules" ] || [ ! -f "node_modules/.package-lock.json" ]; then
        echo -e "  ${YELLOW}⚠️  node_modules missing — installing...${NC}"
        npm install 2>&1 | tail -3
        if [ ! -d "node_modules/next" ]; then
            echo -e "  ${RED}❌ Frontend install failed — run: cd vestra/frontend-build && npm install${NC}"
            cd "$SCRIPT_DIR"
            return 1
        fi
        echo -e "  ${GREEN}✅ Frontend packages installed${NC}"
    fi

    npx next dev -p 3000 &
    FRONTEND_PID=$!
    echo -e "  Frontend PID: $FRONTEND_PID"
    echo -e "  App:          ${CYAN}http://localhost:3000${NC}"

    cd "$SCRIPT_DIR"
}

# ── Start Docker ──────────────────────────────────────────────────────────────
start_docker() {
    echo -e "${BLUE}🐳 Starting via Docker Compose...${NC}\n"

    cd "$SCRIPT_DIR/vestra"
    docker compose up -d

    echo -e "\n${GREEN}✅ Services starting in Docker:${NC}"
    docker compose ps

    echo -e "\n  API:           ${CYAN}http://localhost:8000/docs${NC}"
    echo -e "  Frontend:      ${CYAN}http://localhost:3000${NC}"
    echo -e "  Grafana:       ${CYAN}http://localhost:3001${NC}"
    echo -e "  Prometheus:    ${CYAN}http://localhost:9090${NC}"
    echo -e "  Flower (tasks):${CYAN}http://localhost:5555${NC}"
}

# ── Stop Services ─────────────────────────────────────────────────────────────
stop_services() {
    echo -e "${YELLOW}🛑 Stopping services...${NC}"

    # Kill background processes
    if [ -n "${BACKEND_PID:-}" ]; then
        kill "$BACKEND_PID" 2>/dev/null && echo "  Stopped backend (PID $BACKEND_PID)"
    fi
    if [ -n "${FRONTEND_PID:-}" ]; then
        kill "$FRONTEND_PID" 2>/dev/null && echo "  Stopped frontend (PID $FRONTEND_PID)"
    fi

    # Kill uvicorn/gunicorn processes
    pkill -f "uvicorn app.main" 2>/dev/null || true
    pkill -f "gunicorn.*app.main" 2>/dev/null || true
    pkill -f "next dev" 2>/dev/null || true

    echo -e "${GREEN}✅ All services stopped.${NC}"
}

# ── Trap for cleanup ──────────────────────────────────────────────────────────
cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down...${NC}"
    stop_services
    exit 0
}
trap cleanup SIGINT SIGTERM

# ── Deep Research Only ────────────────────────────────────────────────────────
start_deep_research_only() {
    echo -e "${MAGENTA}🔬 Starting Deep Research API server...${NC}\n"

    cd "$BACKEND_DIR"

    if [ -f .env ]; then
        set -a; source .env; set +a
    fi

    local PYTHON_BIN="python3"
    if [ -f "$VENV_DIR/bin/activate" ]; then
        # shellcheck disable=SC1090
        source "$VENV_DIR/bin/activate"
        PYTHON_BIN="$VENV_DIR/bin/python"
    fi

    # Auto-install if deps missing
    if ! check_python_deps "$PYTHON_BIN"; then
        echo -e "  ${YELLOW}⚠️  Python dependencies not installed — installing...${NC}"
        if [ ! -d "$VENV_DIR" ]; then
            python3 -m venv "$VENV_DIR"
            source "$VENV_DIR/bin/activate"
            PYTHON_BIN="$VENV_DIR/bin/python"
        fi
        pip install --upgrade pip -q 2>/dev/null
        pip install -r requirements.txt -q 2>&1 | tail -3
    fi

    # Quick test the deep research engine
    echo -e "${BLUE}Testing deep research engine...${NC}"
    $PYTHON_BIN -c "
from app.deep_research import DeepResearchEngine
engine = DeepResearchEngine()
print(f'  ✅ Deep Research Engine initialized')
print(f'  ✅ Vector store: ready (dim={engine.embedder.DIMENSION})')
print(f'  ✅ Market benchmarks: {len(engine.aggregator.KENYA_MARKET_BENCHMARKS)} cities loaded')
print(f'  ✅ Reports dir: {engine.report_writer.output_dir}')
" 2>&1 || echo -e "  ${YELLOW}⚠️ ${NC} Engine test had warnings"

    echo ""
    echo -e "${GREEN}Starting API server with Deep Research...${NC}"
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --log-level info

    cd "$SCRIPT_DIR"
}

# ── Main ─────────────────────────────────────────────────────────────────────
main() {
    local mode="${1:-}"

    case "$mode" in
        --help|-h|help)
            show_help
            exit 0
            ;;
        --check)
            check_system
            exit 0
            ;;
        --install)
            banner
            install_deps
            setup_env
            echo -e "${GREEN}✅ Installation complete. Run ./start.sh to start.${NC}"
            exit 0
            ;;
        --stop)
            stop_services
            exit 0
            ;;
        --docker)
            banner
            check_system
            start_docker
            exit 0
            ;;
        --deep-research)
            banner
            check_system
            start_deep_research_only
            ;;
        --dev)
            banner
            check_system
            setup_env
            echo ""
            start_backend "dev"
            start_frontend
            echo ""
            echo -e "${GREEN}✅ VESTRA is running in DEVELOPMENT mode${NC}"
            echo -e "  API:      ${CYAN}http://localhost:8000/docs${NC}"
            echo -e "  Frontend: ${CYAN}http://localhost:3000${NC}"
            echo -e "\n${YELLOW}Press Ctrl+C to stop all services${NC}"
            wait
            ;;
        --prod)
            banner
            check_system
            setup_env
            setup_db
            echo ""
            start_backend "prod"
            echo ""
            echo -e "${GREEN}✅ VESTRA is running in PRODUCTION mode${NC}"
            echo -e "  API: ${CYAN}http://localhost:8000${NC}"
            echo -e "\n${YELLOW}Press Ctrl+C to stop${NC}"
            wait
            ;;
        *)
            banner
            check_system

            # Interactive menu when no flag provided
            echo -e "${BOLD}Select start mode:${NC}"
            echo "  1) Full stack (backend + frontend) — dev mode"
            echo "  2) Backend only — dev mode"
            echo "  3) Deep Research API only"
            echo "  4) Production mode (backend only)"
            echo "  5) Docker Compose (all services)"
            echo "  6) Install dependencies only"
            echo "  7) Check system only"
            echo ""
            read -rp "Enter choice [1-7] (default: 1): " choice
            choice="${choice:-1}"

            case "$choice" in
                1)
                    setup_env
                    echo ""
                    start_backend "dev"
                    start_frontend
                    echo ""
                    echo -e "${GREEN}✅ Full stack running${NC}"
                    echo -e "  API:      ${CYAN}http://localhost:8000/docs${NC}"
                    echo -e "  Frontend: ${CYAN}http://localhost:3000${NC}"
                    wait
                    ;;
                2)
                    setup_env
                    echo ""
                    start_backend "dev"
                    echo ""
                    echo -e "${GREEN}✅ Backend running${NC}"
                    echo -e "  API: ${CYAN}http://localhost:8000/docs${NC}"
                    wait
                    ;;
                3)
                    setup_env
                    start_deep_research_only
                    ;;
                4)
                    setup_env
                    setup_db
                    start_backend "prod"
                    wait
                    ;;
                5)
                    start_docker
                    ;;
                6)
                    install_deps
                    setup_env
                    echo -e "${GREEN}✅ Dependencies installed.${NC}"
                    ;;
                7)
                    check_system
                    ;;
                *)
                    echo -e "${RED}Invalid choice${NC}"
                    exit 1
                    ;;
            esac
            ;;
    esac
}

# ── Run ───────────────────────────────────────────────────────────────────────
main "${1:-}"
