#!/usr/bin/env bash
# =============================================================================
#  VESTRA Mobile Shell Setup — Capacitor Init Script
#  Run from the project root (one level above frontend-build).
#  Usage: bash scripts/setup-mobile.sh
# =============================================================================

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BUILD_DIR="$ROOT_DIR/frontend-build"
MOBILE_DIR="$ROOT_DIR/mobile"

echo "============================================"
echo "  VESTRA Mobile Shell Setup"
echo "============================================"

# ── 1. Prerequisites ──────────────────────────────────────────────────────────
echo ""
echo "[1/6] Checking prerequisites..."

command -v node >/dev/null 2>&1 || { echo "ERROR: Node.js is required. Install from https://nodejs.org"; exit 1; }
command -v npm  >/dev/null 2>&1 || { echo "ERROR: npm is required."; exit 1; }

NODE_VER=$(node -v | sed 's/v//' | cut -d. -f1)
if [ "$NODE_VER" -lt 18 ]; then
  echo "ERROR: Node.js >= 18 required (found v$(node -v))"
  exit 1
fi
echo "  Node.js $(node -v) — OK"

# ── 2. Install Capacitor CLI & Core ──────────────────────────────────────────
echo ""
echo "[2/6] Installing Capacitor dependencies..."
cd "$BUILD_DIR"

npm install --save-dev @capacitor/cli @capacitor/core @capacitor/ios @capacitor/android

CAP_VER=$(npx cap --version 2>/dev/null || echo "unknown")
echo "  Capacitor v$CAP_VER installed"

# ── 3. Build the Next.js static export ───────────────────────────────────────
echo ""
echo "[3/6] Building Next.js standalone output..."
npm run build

if [ ! -d ".next/standalone" ]; then
  echo "ERROR: Next.js build did not produce .next/standalone/"
  echo "  Ensure next.config.ts has output: 'standalone'"
  exit 1
fi
echo "  Standalone build ready at .next/standalone"

# ── 4. Init Capacitor project ────────────────────────────────────────────────
echo ""
echo "[4/6] Initializing Capacitor..."
npx cap init \
  --web-dir ".next/standalone" \
  "Vestra" \
  co.ke.vestra

echo "  capacitor.config.ts created/updated"

# ── 5. Add native platforms ──────────────────────────────────────────────────
echo ""
echo "[5/6] Adding native platforms..."

if [ ! -d "ios" ]; then
  npx cap add ios
  echo "  iOS platform added"
else
  npx cap sync ios
  echo "  iOS platform synced"
fi

if [ ! -d "android" ]; then
  npx cap add android
  echo "  Android platform added"
else
  npx cap sync android
  echo "  Android platform synced"
fi

# ── 6. Copy web assets & open IDE ────────────────────────────────────────────
echo ""
echo "[6/6] Syncing web assets..."
npx cap copy

echo ""
echo "============================================"
echo "  VESTRA Mobile Shell Setup Complete!"
echo "============================================"
echo ""
echo "  Next steps:"
echo "    cd $BUILD_DIR"
echo "    npx cap open ios      # Open in Xcode"
echo "    npx cap open android  # Open in Android Studio"
echo ""
echo "  To rebuild and sync after code changes:"
echo "    npm run build && npx cap copy"
echo ""

# ── Optional: copy capacitor.config.ts to mobile/ for CI reference ──────────
if [ ! -d "$MOBILE_DIR" ]; then
  mkdir -p "$MOBILE_DIR"
fi
cp capacitor.config.ts "$MOBILE_DIR/capacitor.config.ts"
echo "  capacitor.config.ts copied to $MOBILE_DIR for CI reference"
