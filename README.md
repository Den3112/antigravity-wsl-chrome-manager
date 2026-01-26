# Antigravity WSL Chrome Manager (Portable Edition) 🚀

Stable, zero-conflict solution for running Antigravity browser control in a dual Windows/WSL environment with **Automatic GPU Acceleration**.

## 🌟 Portable & Simple
All settings and scripts are contained within this single folder. You can move this folder to any WSL instance, run the setup, and everything will work out-of-the-box.

## 🚀 Key Features
*   **Zero-Config GPU:** Auto-detects NVIDIA or AMD GPUs.
*   **Shadow Port Isolation:** WSL uses its own \localhost:9222\ without touching Windows ports.
*   **Easy Migration:** Use the included \setup.sh\ for instant configuration on any machine.

## 🛠 Installation

1. **Move this folder** to your WSL home directory (\~/\).
2. **Run the setup script**:
   \\ash
   cd ~/antigravity-wsl-chrome-manager
   chmod +x setup.sh
   ./setup.sh
   \3. **Reload your terminal**:
   \\ash
   source ~/.bashrc
   \
## 🕹 CLI Commands
*   \chrome-status\: Check if the proxy and Chrome are healthy.
*   \chrome-restart\: Restart all browser services.
*   \chrome-logs\: Monitor browser traffic.

---
*Created and maintained by Antigravity AI*
