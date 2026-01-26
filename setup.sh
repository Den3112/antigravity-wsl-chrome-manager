#!/bin/bash
INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASHRC="$HOME/.bashrc"
echo "🚀 Configuring Antigravity PRO in $INSTALL_DIR..."
# Clean old
sed -i '/Antigravity PRO/d' "$BASHRC"
sed -i '/Shadow Architecture/d' "$BASHRC"
sed -i '/antigravity-wsl-chrome-manager/d' "$BASHRC"
# Add new
cat << INNER_EOF >> "$BASHRC"

# =============================================================================
# Antigravity PRO Configuration (Shadow Architecture)
# =============================================================================
export GALLIUM_DRIVER=d3d12
if [ -z "\$MESA_D3D12_DEFAULT_ADAPTER_NAME" ]; then
    if [ -d "/proc/driver/nvidia" ]; then export MESA_D3D12_DEFAULT_ADAPTER_NAME=NVIDIA
    elif grep -iq "amd" /sys/class/drm/card*/device/vendor 2>/dev/null; then export MESA_D3D12_DEFAULT_ADAPTER_NAME=AMD
    fi
fi
alias chrome-status='$INSTALL_DIR/chrome-ctl status'
alias chrome-restart='$INSTALL_DIR/chrome-ctl restart'
alias chrome-logs='tail -f \$HOME/smart_proxy.log'
if [ -f "$INSTALL_DIR/smart_chrome_proxy.py" ]; then
    pgrep -f "smart_chrome_proxy.py" > /dev/null || nohup python3 "$INSTALL_DIR/smart_chrome_proxy.py" > "\$HOME/smart_proxy.log" 2>&1 &
fi
INNER_EOF
chmod +x "$INSTALL_DIR/chrome-ctl" "$INSTALL_DIR/start_chrome_for_antigravity.sh"
echo "✅ Done! Run: source ~/.bashrc"
