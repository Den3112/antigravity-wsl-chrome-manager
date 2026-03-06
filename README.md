# Antigravity WSL Chrome Manager (Portable Edition) 🚀

Stable, zero-conflict solution for running Antigravity browser control in a dual Windows/WSL environment with **Automatic GPU Acceleration**.

## 🌟 Portable & Simple

All settings and scripts are contained within this single folder. You can move this folder to any WSL instance, run the setup, and everything will work out-of-the-box.

## 🚀 Key Features

* **Smart Eye Integration:** Automatically routes Antigravity's browser requests to WSL or Windows based on the project path.
* **Shadow Port Isolation:** WSL uses its own `localhost:9222` without touching Windows ports.
* **Zero-Config GPU:** Auto-detects NVIDIA or AMD GPUs.
* **Easy Migration:** Use the included `setup.sh` for instant configuration on any machine.

## 🛠 Installation

1. **Move this folder** to your WSL home directory (\~/\).
2. **Run the setup script**:
   \\ash
   cd ~/antigravity-wsl-chrome-manager
   chmod +x setup.sh
   ./setup.sh
3. **Move this folder** to your WSL home directory (\~/\).
4. **Run the setup script**:
    \\ash
    cd ~/antigravity-wsl-chrome-manager
    chmod +x setup.sh
    ./setup.sh
    \3. **Reload your terminal**:
    \\ash
    source ~/.bashrc
    \

## 🕹 CLI Commands

* `chrome-status`: Check if the proxy and Chrome are healthy.
* `chrome-restart`: Restart all browser services.
* `chrome-logs`: Monitor browser traffic.

## 👁️ Smart Eye (Cross-Environment Routing)

This project now supports **Smart Eye**, a Windows-side router that automatically switches between WSL and Windows Chrome instances.

1. **Windows Side**: The router listens on `127.0.0.1:9222`.
2. **WSL Side**: The `smart_chrome_proxy.py` (this project) listens on `0.0.0.0:9222` to accept traffic from the router.
3. **Magic**: When you work on a WSL project (`\\wsl.localhost\...`), the eye automatically sees the WSL environment. When you switch to Windows, it sees Windows.

---
*Created and maintained by Antigravity AI*
