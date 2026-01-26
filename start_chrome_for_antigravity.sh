#!/bin/bash

# =============================================================================
# CHROME LAUNCHER with SINGLETON PROTECTION
# =============================================================================

# Prevent multiple instances of this script from running simultaneously for the SAME PORT
# We use a lock file on a specific file descriptor (200)
# Port is defined later, but we can't use it before definition.
# So we need to parse it early or just move the lock down.
# Taking a simpler approach: define default port early.
PORT="${CHROME_PORT:-9223}"
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

# Scale factor for High DPI screens (default 1.5 for 4K)
# SCALE_FACTOR="${1:-1.5}" # This variable is no longer used in the launch command

# Kill existing Chrome on this port to force a clean slate (Single Instance Policy)
# This prevents the "New Window in Old Session" behavior
# pkill -f "chrome.*$PORT" 2>/dev/null

# Clean up singleton lock for THIS profile
rm -f "$USER_DATA_DIR/SingletonLock"

# Ensure DISPLAY is set for GUI support
export DISPLAY=:0
export XDG_RUNTIME_DIR=/run/user/$(id -u)
export GALLIUM_DRIVER=d3d12
export MESA_D3D12_DEFAULT_ADAPTER_NAME=NVIDIA

echo "🚀 Starting Chrome for Antigravity..."
echo "   Profile: $USER_DATA_DIR"
echo "   Port: $PORT"

# Start Chrome in background with no initial window and specific profile
nohup "$CHROME_BIN" \
  --remote-debugging-port=$PORT \
  --user-data-dir="$USER_DATA_DIR" \
  --remote-allow-origins='*' \
  --no-sandbox \
  --disable-dev-shm-usage \
  --force-device-scale-factor=1.5 \
  --window-size=1400,900 \
  --no-first-run \
  --no-default-browser-check \
  --disable-background-networking \
  --disable-sync \
  --disable-session-crashed-bubble \
  --disable-infobars \
  --no-startup-window \
  > /tmp/antigravity_chrome_${PORT}.log 2>&1 &

PID=$!
echo "✅ Chrome PID: $PID"

# Wait for port to be ready
count=0
while ! curl -s "http://127.0.0.1:$PORT/json/version" > /dev/null 2>&1; do
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
echo "🪟 PID: $PID"
