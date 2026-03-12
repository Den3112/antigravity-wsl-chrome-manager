#!/bin/bash

# =============================================================================
# CHROME LAUNCHER with SINGLETON PROTECTION
# =============================================================================

# Prevent multiple instances of this script from running simultaneously for the SAME PORT
PORT="${CHROME_PORT:-9223}"

# CRITICAL: Clean up existing listeners on THIS port if they are zombies (no chrome)
# This fixes the bug where socat stays alive but chrome is dead.
INTERNAL_PORT=$((PORT + 20000))
if ss -tuln | grep -q ":$PORT "; then
    if ! ss -tuln | grep -q ":$INTERNAL_PORT "; then
        echo "⚠️  Found zombie socat on port $PORT (no Chrome on $INTERNAL_PORT). Cleaning up..."
        fuser -k $PORT/tcp 2>/dev/null || true
        # Fallback: find PID of process listening on PORT and kill it
        LISTEN_PID=$(ss -lptn "sport = :$PORT" | grep -oP 'pid=\K\d+' | head -n 1)
        [ -n "$LISTEN_PID" ] && kill -9 $LISTEN_PID 2>/dev/null
    else
        echo "✅ Port $PORT (and Chrome on $INTERNAL_PORT) is already in use. Exiting."
        exit 0
    fi
fi

LOCK_FILE="/tmp/antigravity_chrome_launch_${PORT}.lock"
exec 200>"$LOCK_FILE"

flock -n 200 || { echo "Another instance is starting Chrome for port $PORT. Exiting."; exit 1; }

# Configuration
CHROME_BIN="/usr/bin/google-chrome-stable"
USER_DATA_DIR="${CHROME_USER_DATA_DIR:-$HOME/.gemini/antigravity_chrome_profile}"

# Verify Chrome binary exists
if ! command -v "$CHROME_BIN" >/dev/null 2>&1; then
    echo "❌ Error: Google Chrome not found at $CHROME_BIN"
    exit 1
fi

# Ensure user data dir exists
mkdir -p "$USER_DATA_DIR"

# Scale factor for High DPI screens (default 2.0 for 4K)
SCALE_FACTOR="${1:-2.0}"

# Clean up singleton lock for THIS profile
rm -f "$USER_DATA_DIR/SingletonLock"

export DISPLAY=:0
export XDG_RUNTIME_DIR="/run/user/$(id -u)"
export GALLIUM_DRIVER=d3d12

echo "🚀 Starting Chrome for Antigravity..."
echo "   Profile: $USER_DATA_DIR"
echo "   Port: $PORT"
echo "   DISPLAY: $DISPLAY"

# Force ozone platform to x11 to prevent auto-headless in WSL
OZONE_FLAG="--ozone-platform=x11"

# Internal port for Chrome to avoid conflict with socat on the same port
INTERNAL_PORT=$((PORT + 20000))

# Start Chrome in background
nohup "$CHROME_BIN" \
  --remote-debugging-port=$INTERNAL_PORT \
  --remote-debugging-address=127.0.0.1 \
  --user-data-dir="$USER_DATA_DIR" \
  --remote-allow-origins='*' \
  --no-sandbox \
  $OZONE_FLAG \
  --force-device-scale-factor=$SCALE_FACTOR \
  --window-size=1400,900 \
  --no-first-run \
  --no-default-browser-check \
  --disable-background-networking \
  --disable-sync \
  --disable-session-crashed-bubble \
  --disable-infobars \
  > /tmp/antigravity_chrome_${PORT}.log 2>&1 &

CHROME_PID=$!
echo "✅ Chrome PID: $CHROME_PID (Internal Port: $INTERNAL_PORT)"

# Start socat bridge: External $PORT -> Internal $INTERNAL_PORT
nohup socat TCP4-LISTEN:$PORT,reuseaddr,fork,bind=127.0.0.1 TCP4:127.0.0.1:$INTERNAL_PORT > /tmp/antigravity_socat_${PORT}.log 2>&1 &
SOCAT_PID=$!
echo "✅ Socat Bridge PID: $SOCAT_PID"

# Wait for port to be ready
count=0
while ! curl --max-time 1 -s "http://127.0.0.1:$PORT/json/version" > /dev/null 2>&1; do
    sleep 0.5
    count=$((count+1))
    if [ $count -ge 20 ]; then # 10 seconds timeout
        echo "❌ Launch failed (Timeout)"
        tail -10 /tmp/antigravity_chrome_${PORT}.log
        exit 1
    fi
done

echo ""
echo "✅ SUCCESS! Chrome is ready on port $PORT"
echo "🪟 Chrome PID: $CHROME_PID, Bridge PID: $SOCAT_PID"
